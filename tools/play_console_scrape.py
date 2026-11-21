#!/usr/bin/env python3
"""Play Console 홈의 앱별 수치(기기 획득 수·수익·월간 활성 기기)를 Playwright 로 읽어 Cloudflare KV 에 올린다.

읽기 전용. 구글 계정 비밀번호는 다루지 않는다 — 최초 1회 `login` 으로 전용 크롬 프로필에 사람이 직접 로그인하고,
이후엔 그 프로필(쿠키)만 재사용한다. 프로필 폴더는 로그인 세션이므로 비밀값처럼 취급(복사·커밋 금지).

  python3 tools/play_console_scrape.py login    # 창이 열리면 구글 로그인 → 홈이 보이면 터미널에서 Enter
  python3 tools/play_console_scrape.py run      # 헤드리스로 읽어 KV(play-stats) 갱신
  python3 tools/play_console_scrape.py run --dry   # 읽기만, 올리지 않고 출력
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

DEV = "5334321905021374763"
HOME = f"https://play.google.com/console/u/0/developers/{DEV}/home"
PROFILE = Path.home() / ".onepixel-playwright-profile"
ROOT = Path(__file__).resolve().parent.parent
KV_KEY = "play-stats"
LABELS = ["기기 획득 수", "처음 실행한 기기 수", "수익(KRW)", "월간 활성 기기"]


def launch(p, headless):
    return p.chromium.launch_persistent_context(
        str(PROFILE), channel="chrome", headless=headless,
        ignore_default_args=["--enable-automation"],
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1400, "height": 900},
    )


def parse(text):
    """홈 본문 텍스트를 패키지명 기준으로 잘라 앱별 수치를 뽑는다."""
    i = text.find("정렬 기준")
    body = text[i:] if i >= 0 else text
    apps = []
    for m in re.finditer(r"com\.[a-z0-9_.]+", body):
        pkg = m.group(0)
        start = m.end()
        nxt = re.search(r"com\.[a-z0-9_.]+", body[start:])
        chunk = body[start: start + nxt.start()] if nxt else body[start:]
        # 이름은 패키지 바로 앞 1~3줄 중 상태 문구를 뺀 첫 줄
        before = body[:m.start()].rstrip("\n").split("\n")
        name = next((l for l in reversed(before[-3:]) if l.strip() and "검토" not in l and "전송되지" not in l), pkg)
        vals = {}
        lines = [l.strip() for l in chunk.split("\n") if l.strip()]
        for k, line in enumerate(lines):
            if line in LABELS and k + 1 < len(lines):
                vals[line] = lines[k + 1]
        if vals:
            apps.append({"package": pkg, "name": name, "values": vals})
    return apps


def scrape(headless=True):
    with sync_playwright() as p:
        ctx = launch(p, headless)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(HOME, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(7000)
            if "accounts.google.com" in page.url or "/console" not in page.url:
                raise SystemExit("로그인이 필요합니다: python3 tools/play_console_scrape.py login")
            return parse(page.inner_text("body"))
        finally:
            ctx.close()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "login":
        with sync_playwright() as p:
            ctx = launch(p, False)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(HOME)
            input("구글 로그인을 마치고 Play Console 홈이 보이면 Enter 를 누르세요... ")
            ctx.close()
        print("프로필 저장됨:", PROFILE)
        return
    apps = scrape(headless=True)
    # 공개 대시보드에는 출시(live)된 앱만 싣는다. 폐기·테스트 중인 앱은 뺀다.
    live = {a.get("package") for a in json.loads((ROOT / "apps.json").read_text())["apps"] if a.get("status") == "live"}
    apps = [a for a in apps if a["package"] in live]
    if not apps:
        raise SystemExit("앱 수치를 읽지 못했습니다(화면 구조 변경 가능).")
    payload = {"updated": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "apps": apps}
    out = json.dumps(payload, ensure_ascii=False)
    if "--dry" in sys.argv:
        print(out)
        return
    tmp = ROOT / "tools" / ".play-stats.json"
    tmp.write_text(out)
    try:
        r = subprocess.run(
            ["npx", "wrangler", "kv", "key", "put", KV_KEY, "--path", str(tmp), "--binding", "SUGGESTIONS", "--remote"],
            cwd=ROOT, capture_output=True, text=True, timeout=120)
        print(r.stdout[-300:], r.stderr[-300:])
        if r.returncode != 0:
            raise SystemExit(f"KV 업로드 실패 (code {r.returncode})")
    finally:
        tmp.unlink(missing_ok=True)
    print(f"업로드 완료: 앱 {len(apps)}개")


if __name__ == "__main__":
    main()
