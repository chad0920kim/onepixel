#!/usr/bin/env python3
"""ZenDoku 다국어 소개 페이지(/zendoku/, /zendoku/<lang>/) 생성. 실행: python3 tools/gen_zendoku_pages.py"""
import os, json
ROOT = os.path.join(os.path.dirname(__file__), "..")
BASE = "https://onepixel.yhchad.com"
PLAY = "https://play.google.com/store/apps/details?id=com.zendoku.sudoku"
STYLE = """
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f0f0f;color:#e8e8e8;padding:48px 20px;line-height:1.7}
    .wrap{max-width:720px;margin:0 auto}
    a.back{color:#888;font-size:.9rem;text-decoration:none}
    h1{font-size:2rem;margin:18px 0 6px;letter-spacing:-.5px}
    .sub{color:#aaa;margin-bottom:24px;font-size:1.05rem}
    .cta{display:block;text-align:center;background:linear-gradient(135deg,#7c5cff,#ff5c9e);color:#fff;font-weight:700;padding:16px;border-radius:12px;text-decoration:none;font-size:1.05rem;margin:0 0 30px}
    h2{font-size:1.1rem;margin:28px 0 8px;color:#f0f0f0}
    p,li{color:#cfcfcf}
    ul{padding-left:1.3rem}li{margin-bottom:6px}
    .shots{display:flex;gap:12px;overflow-x:auto;margin:20px 0 8px;padding-bottom:8px}
    .shots img{height:420px;width:auto;border-radius:12px;border:1px solid #2a2a2a;flex:none}
    .note{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:14px 16px;color:#bbb;font-size:.92rem;margin-top:28px}
    .langs{margin:6px 0 0;font-size:.9rem}.langs a{color:#9a8cff;text-decoration:none;margin-right:12px}.langs b{color:#e8e8e8;margin-right:12px}
    footer{margin-top:40px;color:#666;font-size:.85rem}
"""
SHOT_FILES = ["1-home", "2-select", "3-play", "4-hint"]
# lang: (경로, 표시이름, hreflang, 내용)
PAGES = {
 "en": dict(path="/zendoku/", name="English", og="en_US",
  title="ZenDoku: Sudoku Puzzle Coach for Android – No Timer, Hints That Explain",
  desc="ZenDoku is a free sudoku puzzle game for Android. Hints explain why a number fits, a zen mode hides the timer and mistake counter, and a daily sudoku challenge keeps you playing.",
  h1="ZenDoku: Sudoku Puzzle Coach", sub="A sudoku app for Android that explains the “why” instead of the answer. No clock, no pressure.",
  cta="Get it on Google Play →", back="← Onepixel",
  secs=[("Sudoku hints that explain the logic","<p>Stuck? Tap the light bulb. ZenDoku shows which cell to look at and explains why that number fits, step by step, so you start spotting the patterns on your own.</p>"),
        ("Zen mode: no timer, no mistake counter","<p>Play at your own pace with just you and the grid. No clock and no pressure.</p>"),
        ("What's inside","<ul><li>Easy, Medium and Hard sudoku puzzles</li><li>Pencil notes, undo and redo, optional note auto-fill</li><li>Daily sudoku challenge: everyone gets the same puzzle each day</li><li>Streaks, resume unfinished puzzles, review completed ones</li><li>Korean, English, Japanese, Spanish and Simplified Chinese</li></ul>")],
  note="Free to play. Ads are shown on some screens, and “Find mistakes” can be used after watching an ad.",
  alts=["ZenDoku sudoku home screen","Choose a sudoku difficulty","Sudoku board with pencil notes","Hint that explains why a number fits"]),
 "ko": dict(path="/zendoku/ko/", name="한국어", og="ko_KR",
  title="ZenDoku 젠도쿠 – 타이머 없이 편안하게, 이유를 알려주는 스도쿠 앱",
  desc="ZenDoku는 안드로이드용 무료 스도쿠 앱입니다. 정답 대신 왜 그 숫자가 들어가는지 알려주는 힌트와, 타이머·실수 횟수를 숨기는 젠 모드, 데일리 챌린지가 있습니다.",
  h1="ZenDoku 젠도쿠", sub="정답 대신 ‘왜’를 알려주는 안드로이드 스도쿠 앱. 타이머 없이 편안하게 풀어 보세요.",
  cta="Google Play에서 받기 →", back="← Onepixel",
  secs=[("이유를 알려주는 스도쿠 힌트","<p>막히면 전구 버튼을 누르세요. 어느 칸을 봐야 하는지, 왜 그 숫자가 들어가는지 단계별로 알려줘서 스스로 패턴을 찾게 됩니다.</p>"),
        ("젠 모드: 타이머와 실수 횟수 숨김","<p>시간에 쫓기지 않고 나만의 속도로 한 판씩 풀 수 있습니다.</p>"),
        ("주요 기능","<ul><li>쉬움·보통·어려움 3단계 난이도</li><li>메모(연필), 되돌리기·다시 실행, 메모 자동 채우기</li><li>매일 같은 퍼즐을 푸는 데일리 챌린지</li><li>연속 기록, 풀던 퍼즐 이어하기, 완료한 퍼즐 다시 보기</li><li>한국어·영어·일본어·스페인어·중국어 간체 지원</li></ul>")],
  note="무료로 즐길 수 있습니다. 일부 화면에 광고가 표시되며, ‘틀린 칸 찾기’는 광고를 본 뒤 사용할 수 있습니다.",
  alts=["ZenDoku 스도쿠 홈 화면","스도쿠 난이도 선택","메모가 있는 스도쿠 판","왜 그 숫자인지 알려주는 힌트"]),
 "ja": dict(path="/zendoku/ja/", name="日本語", og="ja_JP",
  title="ZenDoku ナンプレ・数独パズル – タイマーなし、解き方を教えるヒント付き",
  desc="ZenDokuはAndroid向けの無料ナンプレ（数独）アプリ。答えではなく「なぜ」を教えるヒント、タイマーとミス回数を隠すゼンモード、毎日のデイリーチャレンジが楽しめます。",
  h1="ZenDoku ナンプレ・数独パズル", sub="答えではなく「なぜ」を教えるAndroid向けナンプレ。タイマーなしで気楽に解けます。",
  cta="Google Playで入手 →", back="← Onepixel",
  secs=[("考え方を教えてくれるナンプレのヒント","<p>行き詰まったら電球ボタンをタップ。どのマスに注目すればよいか、なぜその数字が入るのかをステップごとに説明します。</p>"),
        ("ゼンモード：タイマーなし","<p>プレイ中はタイマーもミスの回数も表示されません。盤面だけに集中できます。</p>"),
        ("主な機能","<ul><li>やさしい・ふつう・むずかしいの3段階</li><li>メモ、元に戻す、やり直し、メモの自動入力</li><li>毎日同じ問題に挑戦するデイリーチャレンジ</li><li>連続記録、続きから再開、完成したパズルの見返し</li><li>韓国語・英語・日本語・スペイン語・中国語（簡体字）に対応</li></ul>")],
  note="無料で遊べます。一部の画面に広告が表示され、「間違い探し」は広告を見たあとに使えます。",
  alts=["ZenDokuナンプレのホーム画面","ナンプレの難易度選択","メモ付きのナンプレ盤面","なぜその数字かを教えるヒント"]),
 "es": dict(path="/zendoku/es/", name="Español", og="es_419",
  title="ZenDoku: Sudoku gratis sin cronómetro – Pistas que explican el porqué",
  desc="ZenDoku es un juego de sudoku gratis para Android. Pistas que explican por qué encaja cada número, modo zen sin cronómetro ni contador de errores y reto diario de sudoku.",
  h1="ZenDoku: Sudoku sin cronómetro", sub="Un sudoku para Android que explica el «porqué» en lugar de darte la respuesta. Sin reloj, sin presión.",
  cta="Descargar en Google Play →", back="← Onepixel",
  secs=[("Pistas de sudoku que explican la lógica","<p>¿Atascado? Toca la bombilla. ZenDoku te muestra qué casilla mirar y explica paso a paso por qué ese número encaja.</p>"),
        ("Modo zen: sin cronómetro","<p>Sin cronómetro y sin contador de errores mientras juegas. Solo tú y la cuadrícula.</p>"),
        ("Qué incluye","<ul><li>Sudoku fácil, medio y difícil</li><li>Notas a lápiz, deshacer, rehacer y autocompletado de notas</li><li>Reto diario de sudoku: el mismo puzzle para todos cada día</li><li>Rachas, continuar puzzles sin terminar y revisar los completados</li><li>Coreano, inglés, japonés, español y chino simplificado</li></ul>")],
  note="Gratis. Se muestran anuncios en algunas pantallas y «Buscar errores» se puede usar después de ver un anuncio.",
  alts=["Pantalla de inicio de ZenDoku sudoku","Elegir la dificultad del sudoku","Tablero de sudoku con notas a lápiz","Pista que explica por qué encaja un número"]),
 "zh": dict(path="/zendoku/zh/", name="简体中文", og="zh_CN",
  title="ZenDoku 数独 – 免费数独游戏，无计时，提示讲解解题思路",
  desc="ZenDoku 是一款安卓免费数独游戏。提示会解释为什么这个数字可以填，禅模式不显示计时和错误次数，还有每日数独挑战。",
  h1="ZenDoku 数独", sub="不直接给答案，而是告诉你“为什么”的安卓数独。没有计时，轻松解题。",
  cta="在 Google Play 下载 →", back="← Onepixel",
  secs=[("讲解思路的数独提示","<p>卡住了？点一下灯泡按钮。ZenDoku 会告诉你该看哪个格子，并一步步解释为什么这个数字可以填在这里。</p>"),
        ("禅模式：无计时","<p>游戏过程中不显示计时，也不统计错误次数，让你专注于棋盘本身。</p>"),
        ("主要功能","<ul><li>简单、中等、困难 3 个难度</li><li>笔记、撤销、重做、笔记自动填入</li><li>每日数独挑战：每天所有人玩同一道题</li><li>连续记录、继续未完成的题目、回看已完成的题目</li><li>支持韩语、英语、日语、西班牙语、简体中文</li></ul>")],
  note="免费游玩。部分界面会显示广告，“查找错误”功能需要观看广告后使用。",
  alts=["ZenDoku 数独主页","选择数独难度","带笔记的数独棋盘","解释为什么填这个数字的提示"]),
}
HREFLANG = {"en":"en","ko":"ko","ja":"ja","es":"es-419","zh":"zh-Hans"}
def render(code, p):
    canon = BASE + p["path"]
    alts = "\n".join(f'  <link rel="alternate" hreflang="{HREFLANG[c]}" href="{BASE}{q["path"]}">' for c, q in PAGES.items())
    alts += f'\n  <link rel="alternate" hreflang="x-default" href="{BASE}/zendoku/">'
    shots = "\n".join(f'      <img src="/zendoku/img/{n}.png" alt="{a}" loading="lazy">' for n, a in zip(SHOT_FILES, p["alts"]))
    secs = "\n".join(f"    <h2>{h}</h2>\n    {b}" for h, b in p["secs"])
    langs = " ".join((f"<b>{q['name']}</b>" if c == code else f'<a href="{q["path"]}" hreflang="{HREFLANG[c]}">{q["name"]}</a>') for c, q in PAGES.items())
    ld = json.dumps({"@context":"https://schema.org","@type":"MobileApplication","name":"ZenDoku","applicationCategory":"GameApplication","operatingSystem":"Android","description":p["desc"],"url":canon,"downloadUrl":PLAY,"inLanguage":HREFLANG[code],"offers":{"@type":"Offer","price":"0","priceCurrency":"USD"},"author":{"@type":"Organization","name":"Onepixel","url":BASE+"/"}}, ensure_ascii=False)
    lang_attr = HREFLANG[code]
    return f"""<!DOCTYPE html>
<html lang="{lang_attr}">
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
  <meta property="og:image" content="{BASE}/zendoku/img/1-home.png">
  <meta name="twitter:card" content="summary">
  <script type="application/ld+json">{ld}</script>
  <style>{STYLE}  </style>
</head>
<body>
  <div class="wrap">
    <a class="back" href="/">{p['back']}</a>
    <div class="langs">{langs}</div>
    <h1>{p['h1']}</h1>
    <p class="sub">{p['sub']}</p>
    <a class="cta" href="{PLAY}">{p['cta']}</a>
    <div class="shots">
{shots}
    </div>
{secs}
    <div class="note">{p['note']}</div>
    <footer>© Onepixel · <a href="https://yhchad.com/privacy/zendoku.html" style="color:#888">Privacy Policy</a></footer>
  </div>
</body>
</html>
"""
for code, p in PAGES.items():
    d = os.path.join(ROOT, p["path"].strip("/")); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w").write(render(code, p)); print("생성", p["path"])
# 사이트맵
sm = os.path.join(ROOT, "sitemap.xml"); s = open(sm).read()
import re
s = re.sub(r"\s*<url><loc>https://onepixel\.yhchad\.com/zendoku/[^<]*</loc>.*?</url>", "", s)
add = "".join(f'  <url><loc>{BASE}{q["path"]}</loc><lastmod>2026-11-23</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>\n' for q in PAGES.values())
s = s.replace("</urlset>", add + "</urlset>"); open(sm, "w").write(s); print("sitemap 갱신")
