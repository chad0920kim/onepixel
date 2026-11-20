#!/usr/bin/env python3
"""Onepixel 앱 상태 동기화.

  python3 tools/sync_apps.py sync            # 스토어 공개 여부 확인 → apps.json 갱신 → index.html 카드 생성
  python3 tools/sync_apps.py build           # apps.json 으로 index.html 카드만 다시 생성
  python3 tools/sync_apps.py status          # 현재 상태 표 출력
  python3 tools/sync_apps.py set <id> <status>   # 상태 변경 후 build
  python3 tools/sync_apps.py add <id> <이름> <패키지> [status]   # 신규 앱 추가(카드 문구는 apps.json 에서 채운다)

자동으로 알 수 있는 것: 공개 스토어 페이지가 열리면 live. 내부/비공개/심사 중은 공개된 신호가 없으니
`set` 으로 바꾸거나 apps.json 을 직접 고친다(허브 세션이 출시·심사·폐기 때마다 갱신).
"""
import html
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
APPS = ROOT / "apps.json"
INDEX = ROOT / "index.html"
START, END = "<!-- APPS:START -->", "<!-- APPS:END -->"

BADGE = {
    "planned": ("plan", "⬜ 기획"),
    "internal": ("proto", "🔵 프로토타입 (내부테스트)"),
    "closed": ("closed", "🟠 비공개테스트 진행중"),
    "review": ("review", "🟡 출시 심사 중"),
    "live": ("live", "🟢 출시됨 (Google Play)"),
}
STAGE = {
    "planned": "",
    "internal": "지금 내부 테스트 단계입니다.",
    "closed": "지금 비공개 테스트가 진행 중입니다.",
    "review": "지금 Google Play 출시 심사 중입니다.",
    "live": "Google Play에서 설치할 수 있습니다.",
}
STORE = "https://play.google.com/store/apps/details?id={}"


def load():
    return json.loads(APPS.read_text(encoding="utf-8"))


def save(data):
    APPS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def store_is_public(pkg):
    """공개 스토어 페이지가 200 이면 출시된 것. 404 면 아직 비공개. 네트워크 오류는 None(판단 보류)."""
    req = urllib.request.Request(STORE.format(pkg) + "&hl=ko", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        return False if e.code == 404 else None
    except Exception:
        return None


def promote_to_live(app):
    app["status"] = "live"
    app.pop("stage", None)
    keep = [c for c in app.get("ctas", []) if c.get("keep")]
    app["ctas"] = [{"label": "Play 스토어에서 받기 →", "href": STORE.format(app["package"])}] + keep
    app.pop("note", None)


def derive_status(app, session):
    """Play API 트랙 + 공개 스토어 확인으로 상태를 정한다. (상태, 근거) 또는 (None, 사유).
    프로덕션 completed 는 '심사 제출됨'과 '공개됨'을 구분하지 못하므로 스토어 페이지로 가른다."""
    pub = store_is_public(app["package"])
    tracks = None
    if session is not None:
        import play_tracks
        tracks = play_tracks.get_tracks(app["package"], session)
        if tracks and "error" in tracks:
            print(f"[경고] {app['name']}: Play API 오류 — {tracks['error']}")
            tracks = None
    if tracks is None:  # API 불가 → 스토어 공개 여부만으로 판단
        return ("live", "공개 스토어 페이지 확인") if pub is True else (None, "API 불가·스토어 미공개")
    import play_tracks
    stage = play_tracks.highest_stage(tracks)
    if stage == "live":
        if pub is True:
            return "live", "프로덕션 completed + 스토어 공개"
        if pub is False:
            return "review", "프로덕션 completed 이지만 스토어 미공개 → 심사 중"
        return None, "스토어 확인 실패(네트워크)"
    if stage is None:
        return None, "릴리스 없음"
    return stage, f"Play API 최고 트랙: {stage}"


def sync():
    data = load()
    changes = []
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import play_tracks
        session = play_tracks._session()
    except Exception as e:
        print(f"[경고] Play API 사용 불가({e}) — 스토어 공개 여부만 확인")
        session = None
    if session is None:
        print("[안내] Play API 키/라이브러리 없음 — 스토어 공개 여부만 확인")
    for app in data["apps"]:
        if app["status"] in ("discarded", "live") or not app.get("package"):
            continue
        new, why = derive_status(app, session)
        if new is None or new == app["status"]:
            continue
        old = app["status"]
        if new == "live":
            promote_to_live(app)
        elif new == "closed":
            app["status"] = "closed"
            app.pop("stage", None)
            keep = [c for c in app.get("ctas", []) if c.get("keep")]
            app["ctas"] = [{"label": "테스트 참여 →", "href": f"https://play.google.com/apps/testing/{app['package']}"}] + keep
        else:  # internal, review — 공개 링크가 없어 기존 버튼 유지
            app["status"] = new
            if new == "internal" and not app.get("ctas"):
                print(f"[주의] {app['name']}: 내부 테스트 참여 링크가 없습니다 — apps.json 의 ctas 를 채워 주세요")
        changes.append(f"{app['name']}: {old} → {new} ({why})")
    if changes:
        save(data)
    return changes


def render_card(app):
    cls, label = BADGE[app["status"]]
    stage = app["stage"] if "stage" in app else STAGE[app["status"]]
    story = (app.get("desc", "") + (" " + stage if stage else "")).strip()
    e = html.escape
    out = ['    <section class="featured">',
           f'      <span class="badge {cls}">{label}</span>',
           f'      <h2>{e(app["name"])}</h2>',
           f'      <div class="sub">{e(app.get("sub", ""))}</div>',
           '      <p class="story">', f'        {e(story)}', '      </p>']
    ctas = app.get("ctas", [])
    if ctas:
        out.append('      <div class="cta-row">')
        for c in ctas:
            ext = "" if c.get("internal") else ' target="_blank" rel="noopener"'
            out.append(f'        <a class="cta ready" href="{e(c["href"])}"{ext}>{e(c["label"])}</a>')
        out.append('      </div>')
    if app.get("note"):
        out.append(f'      <p class="note">{e(app["note"])}</p>')
    out.append('    </section>')
    return "\n".join(out)


def build():
    data = load()
    cards = [render_card(a) for a in data["apps"] if a["status"] != "discarded"]
    text = INDEX.read_text(encoding="utf-8")
    if START not in text or END not in text:
        sys.exit("index.html 에 APPS 마커가 없습니다")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    new = head + START + "\n" + "\n\n".join(cards) + "\n    " + END + tail
    if new != text:
        INDEX.write_text(new, encoding="utf-8")
        return True
    return False


def status():
    for a in load()["apps"]:
        print(f"{a['status']:<10} {a['name']:<14} {a.get('package', '')}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sync"
    if cmd == "sync":
        for c in sync():
            print("변경:", c)
        print("index.html 갱신" if build() else "index.html 변경 없음")
    elif cmd == "build":
        print("index.html 갱신" if build() else "index.html 변경 없음")
    elif cmd == "status":
        status()
    elif cmd == "set" and len(sys.argv) == 4:
        data = load()
        app = next((a for a in data["apps"] if a["id"] == sys.argv[2]), None)
        if not app or sys.argv[3] not in list(BADGE) + ["discarded"]:
            sys.exit("id 또는 status 가 올바르지 않습니다")
        app["status"] = sys.argv[3]
        save(data)
        print("index.html 갱신" if build() else "index.html 변경 없음")
    elif cmd == "add" and len(sys.argv) >= 5:
        data = load()
        if any(a["id"] == sys.argv[2] for a in data["apps"]):
            sys.exit("이미 있는 id 입니다")
        st = sys.argv[5] if len(sys.argv) > 5 else "planned"
        data["apps"].append({"id": sys.argv[2], "name": sys.argv[3], "package": sys.argv[4], "status": st,
                             "sub": "(한 줄 소개)", "desc": "(소개 문구)", "ctas": []})
        save(data)
        print("추가됨. apps.json 에서 sub·desc·ctas 를 채운 뒤 build 하세요.")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
