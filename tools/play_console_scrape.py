#!/usr/bin/env python3
"""Play Console 홈의 앱별 수치(기기 획득 수·수익·월간 활성 기기)와 주문 관리의 인앱 결제를 Playwright 로 읽어 Cloudflare KV 에 올린다.

공개 페이지에 싣는 자료이므로 주문은 날짜·앱·상품 ID·금액만 남기고 주문 번호·구매자 정보는 저장하지 않는다.

읽기 전용. 구글 계정 비밀번호는 다루지 않는다 — 최초 1회 `login` 으로 전용 크롬 프로필에 사람이 직접 로그인하고,
이후엔 그 프로필(쿠키)만 재사용한다. 프로필 폴더는 로그인 세션이므로 비밀값처럼 취급(복사·커밋 금지).

  python3 tools/play_console_scrape.py login    # 창이 열리면 구글 로그인 → 홈이 보이면 창이 자동으로 닫힘
  python3 tools/play_console_scrape.py run      # 헤드리스로 읽어 KV(play-stats) 갱신
  python3 tools/play_console_scrape.py run --dry   # 읽기만, 올리지 않고 출력
"""
import json
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

DEV = "5334321905021374763"
HOME = f"https://play.google.com/console/u/0/developers/{DEV}/home"
PROFILE = Path.home() / ".onepixel-playwright-profile"
ORDERS = f"https://play.google.com/console/u/0/developers/{DEV}/orders"
PUBLIC_STATS = "https://onepixel.yhchad.com/api/play-stats"
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
                vals[line] = "-" if lines[k + 1] in LABELS else lines[k + 1]  # 값이 비면 다음 항목 이름이 온다
        if vals:
            apps.append({"package": pkg, "name": name, "values": vals})
    return apps


def parse_order(cells, app):
    """주문 표 한 줄(날짜·앱·제품·주문 ID·상태·합계)을 익명 항목으로 바꾼다. 주문 ID 는 버린다."""
    d = re.search(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(오전|오후)\s*(\d{1,2}):(\d{2})\(UTC\)", cells[0])
    amt = re.search(r"([A-Z]{3})\s*([\d,]+(?:\.\d+)?)", cells[5])
    if not d or not amt:
        raise ValueError("주문 줄 형식이 바뀜")
    y, mo, day, ampm, h, mi = d.groups()
    utc = datetime(int(y), int(mo), int(day), int(h) % 12 + (12 if ampm == "오후" else 0), int(mi), tzinfo=timezone.utc)
    lines = [l.strip() for l in cells[2].split("\n") if l.strip()]
    status = cells[4].strip().split("\n")[-1].strip()
    return {"date": (utc + timedelta(hours=9)).strftime("%Y%m%d"), "app": app,
            "product": lines[1] if len(lines) > 1 else "", "status": status,
            "currency": amt.group(1), "amount": float(amt.group(2).replace(",", ""))}


def scrape_orders(page):
    page.goto(ORDERS, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("[role=columnheader]", timeout=40000)
    page.wait_for_timeout(5000)
    orders = []
    for _ in range(50):
        rows = page.eval_on_selector_all("[role=row]", """rs => rs.map(r => {
            const c = [...r.querySelectorAll('[role=gridcell]')];
            return {cells: c.map(x => x.innerText), app: r.querySelector('img')?.alt || ''};
        }).filter(r => r.cells.length >= 6)""")
        orders += [parse_order(r["cells"], r["app"]) for r in rows]
        nxt = page.locator('[aria-label="다음 페이지로 이동"]')
        if not nxt.count() or nxt.first.get_attribute("aria-disabled") == "true" or "is-disabled" in (nxt.first.get_attribute("class") or ""):
            return orders
        nxt.first.click()
        page.wait_for_timeout(4000)
    return orders


def previous_orders():
    """주문 화면을 못 읽었을 때 직전에 올린 값을 그대로 이어 쓴다. 그것도 못 읽으면 업로드를 멈춘다."""
    req = urllib.request.Request(PUBLIC_STATS, headers={"User-Agent": "onepixel-sync"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    return d.get("orders", []), d.get("ordersUpdated")


def scrape(headless=True):
    with sync_playwright() as p:
        ctx = launch(p, headless)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(HOME, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(7000)
            if "accounts.google.com" in page.url or "/console" not in page.url:
                raise SystemExit("로그인이 필요합니다: python3 tools/play_console_scrape.py login")
            apps = parse(page.inner_text("body"))
            try:
                orders = scrape_orders(page)
            except Exception as e:  # 주문 화면 실패가 홈 수치 갱신까지 막지 않게
                print("주문 읽기 실패:", str(e)[:200])
                orders = None
            return apps, orders
        finally:
            ctx.close()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "login":
        with sync_playwright() as p:
            ctx = launch(p, False)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(HOME)
            print("열린 창에서 구글 로그인을 해 주세요. Play Console 홈이 보이면 창이 자동으로 닫힙니다(최대 15분).", flush=True)
            deadline = time.time() + 900
            while True:  # 구글 로그인 화면은 CSP 로 wait_for_function 을 막아 파이썬에서 주기적으로 확인한다
                try:
                    if page.url.startswith("https://play.google.com/console") and "정렬 기준" in page.inner_text("body"):
                        break
                except Exception:
                    pass  # 화면 이동 중
                if time.time() > deadline:
                    raise SystemExit("15분 안에 로그인이 끝나지 않았습니다.")
                page.wait_for_timeout(2000)
            page.wait_for_timeout(3000)
            ctx.close()
        print("프로필 저장됨:", PROFILE)
        return
    apps, orders = scrape(headless=True)
    # 공개 대시보드에는 출시(live)된 앱만 싣는다. 폐기·테스트 중인 앱은 뺀다.
    live = {a.get("package") for a in json.loads((ROOT / "apps.json").read_text())["apps"] if a.get("status") == "live"}
    apps = [a for a in apps if a["package"] in live]
    if not apps:
        raise SystemExit("앱 수치를 읽지 못했습니다(화면 구조 변경 가능).")
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    if orders is None:
        orders, orders_updated = previous_orders()
    else:
        names = {a["name"] for a in apps}
        orders, orders_updated = [o for o in orders if o["app"] in names], now
    payload = {"updated": now, "apps": apps, "orders": orders, "ordersUpdated": orders_updated}
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
    print(f"업로드 완료: 앱 {len(apps)}개, 인앱 주문 {len(orders)}건")


if __name__ == "__main__":
    main()
