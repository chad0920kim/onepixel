#!/usr/bin/env python3
"""Play Developer API 로 앱별 트랙(내부/비공개/프로덕션) 상태를 읽는다. 읽기 전용.

키: fastlane/google-play-key.json (6개 프로젝트에 같은 서비스 계정 키). 키 내용은 출력하지 않는다.
조회를 위해 임시 edit 를 열고 읽은 뒤 반드시 삭제한다(앱 설정은 바뀌지 않는다).
google-auth 가 없거나 키가 없으면 None 을 돌려주고 호출 쪽이 조용히 건너뛴다.
"""
import sys
from pathlib import Path

SCOPE = ["https://www.googleapis.com/auth/androidpublisher"]
BASE = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications"
KEY_CANDIDATES = [Path.home() / "Projects" / d / "fastlane" / "google-play-key.json"
                  for d in ("slidepuzzle", "zendoku", "autoplay", "dusty-wipe")]


def _session():
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import AuthorizedSession
    except Exception:
        return None
    for k in KEY_CANDIDATES:
        if k.exists():
            creds = service_account.Credentials.from_service_account_file(str(k), scopes=SCOPE)
            return AuthorizedSession(creds)
    return None


def get_tracks(pkg, session=None):
    """{'production': [{'status': 'completed', 'versionCodes': [...]}], ...} 또는 오류 문자열 dict {'error': ...}."""
    s = session or _session()
    if s is None:
        return None
    r = s.post(f"{BASE}/{pkg}/edits", json={}, timeout=30)
    if r.status_code != 200:
        return {"error": f"edits.insert {r.status_code}: {r.json().get('error', {}).get('message', '')[:120]}"}
    eid = r.json()["id"]
    try:
        t = s.get(f"{BASE}/{pkg}/edits/{eid}/tracks", timeout=30)
        if t.status_code != 200:
            return {"error": f"tracks.list {t.status_code}: {t.json().get('error', {}).get('message', '')[:120]}"}
        out = {}
        for tr in t.json().get("tracks", []):
            rel = [{"status": x.get("status"), "versionCodes": x.get("versionCodes", []), "name": x.get("name")}
                   for x in tr.get("releases", [])]
            out[tr["track"]] = rel
        return out
    finally:
        s.delete(f"{BASE}/{pkg}/edits/{eid}", timeout=30)  # 임시 edit 정리


def highest_stage(tracks):
    """트랙 결과에서 가장 높은 '공개 단계'. production > closed(alpha·beta·custom) > internal. 없으면 None.
    status 가 completed(또는 inProgress 일부 배포)인 릴리스만 센다. draft·halted 는 제외."""
    if not tracks or "error" in tracks:
        return None
    def active(rels):
        return any(r["status"] in ("completed", "inProgress") and r["versionCodes"] for r in rels)
    if active(tracks.get("production", [])):
        return "live"
    if any(active(v) for k, v in tracks.items() if k not in ("production", "internal")):
        return "closed"
    if active(tracks.get("internal", [])):
        return "internal"
    return None


if __name__ == "__main__":
    pkgs = sys.argv[1:] or ["com.zendoku.sudoku"]
    s = _session()
    if s is None:
        sys.exit("키 또는 google-auth 가 없습니다")
    for p in pkgs:
        tr = get_tracks(p, s)
        if tr is None or "error" in tr:
            print(f"{p}: {tr}")
            continue
        summary = {k: [f"{r['status']}:{','.join(map(str, r['versionCodes']))}" for r in v] for k, v in tr.items()}
        print(f"{p}: 최고단계={highest_stage(tr)} 트랙={summary}")
