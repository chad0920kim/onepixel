#!/usr/bin/env python3
"""출시 전(비공개 테스트) 앱 소개 페이지 생성: /slidepuzzle/(+en), /dustywipe/, /petnote/. 실행: python3 tools/gen_other_pages.py
출시되면 CTA 를 Play 스토어 링크로 바꾸고 status 문구를 고친다."""
import os, json, re
ROOT = os.path.join(os.path.dirname(__file__), "..")
BASE = "https://onepixel.yhchad.com"
STYLE = """
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f0f0f;color:#e8e8e8;padding:48px 20px;line-height:1.7}
    .wrap{max-width:720px;margin:0 auto}
    a.back{color:#888;font-size:.9rem;text-decoration:none}
    h1{font-size:2rem;margin:18px 0 6px;letter-spacing:-.5px}
    .sub{color:#aaa;margin-bottom:18px;font-size:1.05rem}
    .status{display:inline-block;background:#1f2a44;color:#9fb7ff;border-radius:999px;padding:3px 12px;font-size:.85rem;margin-bottom:22px}
    .cta{display:block;text-align:center;background:linear-gradient(135deg,#7c5cff,#ff5c9e);color:#fff;font-weight:700;padding:14px;border-radius:12px;text-decoration:none;font-size:1rem;margin:0 0 12px}
    .cta.alt{background:#222;border:1px solid #333;font-weight:600}
    h2{font-size:1.1rem;margin:28px 0 8px;color:#f0f0f0}
    p,li{color:#cfcfcf}
    ul{padding-left:1.3rem}li{margin-bottom:6px}
    .shots{display:flex;gap:12px;overflow-x:auto;margin:20px 0 8px;padding-bottom:8px}
    .shots img{height:420px;width:auto;border-radius:12px;border:1px solid #2a2a2a;flex:none}
    .note{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:14px 16px;color:#bbb;font-size:.92rem;margin-top:28px}
    .langs{margin:6px 0 0;font-size:.9rem}.langs a{color:#9a8cff;text-decoration:none;margin-right:12px}.langs b{color:#e8e8e8;margin-right:12px}
    footer{margin-top:40px;color:#666;font-size:.85rem}
"""
ko_status = "현재 Google Play 비공개 테스트 진행 중"
APPS = {
 "slidepuzzle": {
  "ko": dict(path="/slidepuzzle/", name="한국어", lang="ko", og="ko_KR", imgs=4, alts=["슬라이드 100 홈 화면","스테이지 선택","슬라이딩 퍼즐 플레이","스테이지 클리어"],
   title="슬라이드 100 – 100개 스테이지 슬라이딩 퍼즐 게임 (15퍼즐)",
   desc="슬라이드 100은 빈 칸으로 타일을 밀어 순서대로 맞추는 클래식 슬라이딩 퍼즐(15퍼즐) 게임입니다. 3x3부터 7x8까지 20가지 크기, 100개 스테이지, 별점 기록과 다크 모드를 지원합니다.",
   h1="슬라이드 100", sub="100개 스테이지로 즐기는 슬라이딩 퍼즐 게임. 빈 칸으로 타일을 밀어 순서대로 맞춰 보세요.", status=ko_status,
   ctas=[("① 테스터 그룹 가입하기","https://groups.google.com/g/slide100",False),("② Play 스토어에서 설치","https://play.google.com/apps/testing/com.tide.slidepuzzle",True)],
   secs=[("클래식 슬라이딩 퍼즐","<p>빈 칸으로 타일을 밀어서 순서대로 맞추는 퍼즐입니다. 어릴 때 한 번쯤 만져본 15퍼즐을 스테이지형 게임으로 만들었습니다.</p>"),
         ("주요 기능","<ul><li>3x3부터 7x8까지 20가지 크기, 총 100개 스테이지</li><li>클리어할 때 이동 횟수와 시간에 따라 별점 획득</li><li>스테이지를 순서대로 클리어하며 다음 단계 잠금 해제</li><li>최고 기록 자동 저장</li><li>다크 모드, 효과음과 음소거 설정</li><li>한국어·영어·중국어·스페인어·프랑스어·일본어 지원(앱 안에서 언어 선택)</li></ul>")],
   note="비공개 테스트 참여 방법: ① 테스터 그룹에 가입한 뒤 ② 설치 링크에서 '테스터 되기'를 누르면 Play 스토어에서 설치할 수 있습니다(안드로이드 폰)."),
  "en": dict(path="/slidepuzzle/en/", name="English", lang="en", og="en_US", imgs=4, alts=["Slide 100 home screen","Stage select","Sliding puzzle gameplay","Stage cleared"],
   title="Slide 100 – Sliding Puzzle Game with 100 Stages (15 Puzzle)",
   desc="Slide 100 is a classic sliding puzzle game: push tiles into the empty space to put them in order. 100 stages across 20 grid sizes from 3x3 to 7x8, star ratings and dark mode.",
   h1="Slide 100", sub="A sliding puzzle game with 100 stages. Push tiles into the empty space to put them back in order.", status="Currently in closed testing on Google Play",
   ctas=[("1. Join the tester group","https://groups.google.com/g/slide100",False),("2. Install from Google Play","https://play.google.com/apps/testing/com.tide.slidepuzzle",True)],
   secs=[("A classic sliding puzzle","<p>Push tiles into the empty space to put them back in order. The old 15 puzzle, rebuilt as a stage-based mobile game.</p>"),
         ("Features","<ul><li>100 stages across 20 grid sizes, from 3x3 to 7x8</li><li>Star ratings based on your move count and time</li><li>Stages unlock in order as you clear them</li><li>Best records saved automatically</li><li>Dark mode, sound effects with a mute toggle</li><li>Korean, English, Chinese, Spanish, French and Japanese, switchable in the app</li></ul>")],
   note="How to join the closed test: join the tester group, then tap “Become a tester” on the install link to install from Google Play (Android phone)."),
 },
 "dustywipe": {
  "ko": dict(path="/dustywipe/", name="한국어", lang="ko", og="ko_KR", imgs=0, alts=[],
   title="한눈에 미세먼지 – 내 위치 실시간 미세먼지·초미세먼지·대기질 앱",
   desc="한눈에 미세먼지는 내 위치를 기준으로 실시간 미세먼지(PM10)·초미세먼지(PM2.5)와 대기질 정보를 보여 주는 안드로이드 앱입니다. 잠금화면과 알림으로 앱을 열지 않고도 오늘의 대기질을 확인합니다.",
   h1="한눈에 미세먼지", sub="내 위치 기준 실시간 미세먼지·초미세먼지·대기질 정보를 한눈에.", status=ko_status,
   ctas=[("① 테스터 그룹 가입하기","https://groups.google.com/g/dustywipe-test",False),("② Play 스토어에서 설치","https://play.google.com/apps/testing/com.anonymous.dustywipe",True)],
   secs=[("내 위치 기준 실시간 대기질","<p>현재 위치를 기준으로 미세먼지(PM10)와 초미세먼지(PM2.5), 대기질 정보를 확인할 수 있습니다.</p>"),
         ("앱을 열지 않아도","<p>잠금화면과 알림을 통해 앱을 열지 않고도 오늘의 대기질을 바로 볼 수 있습니다.</p>")],
   note="비공개 테스트 참여자를 모집하고 있습니다. ① 테스터 그룹에 가입한 뒤 ② 설치 링크에서 '테스터 되기'를 누르면 Play 스토어에서 설치할 수 있습니다(안드로이드 폰, 14일간 사용해 주실 분)."),
 },
 "petnote": {
  "ko": dict(path="/petnote/", name="한국어", lang="ko", og="ko_KR", imgs=4, alts=["챙겨줄개 홈: 아이별 사료 남은 일수와 다음 접종일","사료 소진일 계산","예방접종 기록","병원 기록과 영수증"],
   title="챙겨줄개 – 반려동물 사료 소진일·접종·병원 기록 앱",
   desc="챙겨줄개는 반려동물 사료 소진일, 예방접종, 병원 영수증을 알림과 달력으로 챙겨 주는 기록 앱입니다. 회원가입 없이 쓰고, 입력한 기록은 폰 안에만 저장됩니다.",
   h1="챙겨줄개", sub="사료 소진일·접종·병원 영수증을 알림과 달력으로 챙겨 주는 반려동물 기록 앱.", status=ko_status,
   ctas=[("① 테스터 그룹 가입하기","https://groups.google.com/g/chad-testers-a",False),("② Play 스토어에서 설치","https://play.google.com/apps/testing/com.yhchad.pet_note",True)],
   secs=[("사료 소진일 계산","<p>포장 용량과 하루 급여량, 개봉일을 넣으면 남은 양과 소진 예정일을 보여 주고, 떨어지기 3일 전에 알림을 보냅니다.</p>"),
         ("예방접종 기록과 알림","<p>접종 이름, 접종일, 다음 접종일을 기록하면 접종 하루 전과 당일에 알려 줍니다.</p>"),
         ("병원 기록과 영수증 보관","<p>병원, 진료비, 메모를 남기고 영수증은 사진으로 보관합니다. 올해 쓴 진료비 합계도 볼 수 있습니다.</p>"),
         ("한눈에 보는 달력과 여러 마리 관리","<p>접종, 병원 방문, 사료 소진 예정을 달력 하나에서 확인하고, 강아지·고양이 등 여러 아이를 따로 관리할 수 있습니다.</p>"),
         ("내 기록은 내 폰에만","<p>회원가입 없이 쓸 수 있고, 입력한 기록은 폰 안에만 저장됩니다. 백업 파일로 내보내고 복원할 수 있습니다.</p>")],
   note="무료 앱이며 홈 화면에 광고가 표시될 수 있습니다. 이 앱은 기록과 알림을 돕는 도구이며 수의학적 진단이나 조언을 제공하지 않습니다. 사료 소진일은 하루 급여량이 일정하다는 가정의 추정치입니다. 비공개 테스트: ① 테스터 그룹 가입 → ② '테스터 되기'(안드로이드 폰, 14일간 사용해 주실 분)."),
 },
}
def render(app, code, p, pages):
    canon = BASE + p["path"]
    alts = "\n".join(f'  <link rel="alternate" hreflang="{q["lang"]}" href="{BASE}{q["path"]}">' for q in pages.values())
    if len(pages) > 1: alts += f'\n  <link rel="alternate" hreflang="x-default" href="{BASE}{pages["ko"]["path"]}">'
    else: alts = ""
    shots = ""
    if p["imgs"]:
        shots = '    <div class="shots">\n' + "\n".join(f'      <img src="/{app}/img/{i}.jpg" alt="{a}" loading="lazy">' for i, a in zip(range(1, p["imgs"]+1), p["alts"])) + "\n    </div>\n"
    secs = "\n".join(f"    <h2>{h}</h2>\n    {b}" for h, b in p["secs"])
    cta = "\n".join(f'    <a class="cta{"" if main else " alt"}" href="{h}">{l}</a>' for l, h, main in p["ctas"])
    langs = ""
    if len(pages) > 1:
        langs = '    <div class="langs">' + " ".join((f"<b>{q['name']}</b>" if c == code else f'<a href="{q["path"]}" hreflang="{q["lang"]}">{q["name"]}</a>') for c, q in pages.items()) + "</div>\n"
    ld = json.dumps({"@context":"https://schema.org","@type":"MobileApplication","name":p["h1"],"operatingSystem":"Android","description":p["desc"],"url":canon,"inLanguage":p["lang"],"author":{"@type":"Organization","name":"Onepixel","url":BASE+"/"}}, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="{p['lang']}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{p['title']}</title>
  <meta name="description" content="{p['desc']}">
  <link rel="canonical" href="{canon}">
{alts}
  <meta property="og:title" content="{p['title']}">
  <meta property="og:description" content="{p['desc']}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{canon}">
  <meta property="og:locale" content="{p['og']}">
  <meta name="twitter:card" content="summary">
  <script type="application/ld+json">{ld}</script>
  <style>{STYLE}  </style>
</head>
<body>
  <div class="wrap">
    <a class="back" href="/">← Onepixel</a>
{langs}    <h1>{p['h1']}</h1>
    <p class="sub">{p['sub']}</p>
    <span class="status">{p['status']}</span>
{cta}
{shots}{secs}
    <div class="note">{p['note']}</div>
    <footer>© Onepixel</footer>
  </div>
</body>
</html>
"""
paths = []
for app, pages in APPS.items():
    for code, p in pages.items():
        d = os.path.join(ROOT, p["path"].strip("/")); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w").write(render(app, code, p, pages)); paths.append(p["path"]); print("생성", p["path"])
sm = os.path.join(ROOT, "sitemap.xml"); s = open(sm).read()
for pth in paths:
    s = re.sub(r"\s*<url><loc>" + re.escape(BASE + pth) + r"</loc>.*?</url>", "", s)
add = "".join(f'  <url><loc>{BASE}{pth}</loc><lastmod>2026-11-23</lastmod><changefreq>monthly</changefreq><priority>0.6</priority></url>\n' for pth in paths)
open(sm, "w").write(s.replace("</urlset>", add + "</urlset>")); print("sitemap 갱신")
