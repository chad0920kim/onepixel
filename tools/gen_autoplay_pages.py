#!/usr/bin/env python3
"""Autoplay 소개 페이지(/autoplay/, /autoplay/ko/) 생성. 실행: python3 tools/gen_autoplay_pages.py"""
import os, json
ROOT = os.path.join(os.path.dirname(__file__), "..")
BASE = "https://onepixel.yhchad.com"
PLAY = "https://play.google.com/store/apps/details?id=com.chadkim.autoplay"
STYLE = """
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f0f0f;color:#e8e8e8;padding:48px 20px;line-height:1.7}
    .wrap{max-width:720px;margin:0 auto}
    a.back{color:#888;font-size:.9rem;text-decoration:none}
    h1{font-size:2rem;margin:18px 0 6px;letter-spacing:-.5px}
    .sub{color:#aaa;margin-bottom:24px;font-size:1.05rem}
    .cta{display:block;text-align:center;background:linear-gradient(135deg,#7c5cff,#ff5c9e);color:#fff;font-weight:700;padding:16px;border-radius:12px;text-decoration:none;font-size:1.05rem;margin:0 0 30px}
    .icon{width:72px;height:72px;border-radius:16px;display:block;margin-top:14px}
    h2{font-size:1.1rem;margin:28px 0 8px;color:#f0f0f0}
    p,li{color:#cfcfcf}
    ul{padding-left:1.3rem}li{margin-bottom:6px}
    .shots{display:flex;gap:12px;overflow-x:auto;margin:20px 0 8px;padding-bottom:8px}
    .shots img{height:420px;width:auto;border-radius:12px;border:1px solid #2a2a2a;flex:none}
    .note{background:#1a1a1a;border:1px solid #2a2a2a;border-radius:10px;padding:14px 16px;color:#bbb;font-size:.92rem;margin-top:28px}
    .langs{margin:6px 0 0;font-size:.9rem}.langs a{color:#9a8cff;text-decoration:none;margin-right:12px}.langs b{color:#e8e8e8;margin-right:12px}
    footer{margin-top:40px;color:#666;font-size:.85rem}
"""
SHOT_FILES = ["1", "2", "3", "4"]
# lang: (경로, 표시이름, hreflang, 내용)
PAGES = {
 "en": dict(path="/autoplay/", name="English", og="en_US",
  title="AutoPlay: Auto Play Music When Bluetooth Connects – Car and Speaker",
  desc="AutoPlay starts your music app automatically when your phone connects to car Bluetooth, a Bluetooth speaker or earbuds, and pauses when it disconnects. For Android.",
  h1="AutoPlay: Bluetooth Auto Music", sub="Get in the car or turn on your Bluetooth speaker and your music starts by itself. For Android.",
  cta="Get it on Google Play →", back="← Onepixel",
  secs=[("Auto play music when Bluetooth connects","<p>Pick the Bluetooth devices you want, such as your car stereo, a Bluetooth speaker or earbuds, and the music app to use. When a chosen device connects, AutoPlay opens that app and starts playback.</p>"),
        ("Pauses when it disconnects","<p>When Bluetooth drops, the music stops. If a call or notification interrupted playback, AutoPlay can resume it for you (this needs notification access).</p>"),
        ("What's inside","<ul><li>Choose which paired devices trigger playback, or react to all of them</li><li>Works with the music app you pick</li><li>Set the volume used when playback starts</li><li>Adjust the start delay and retry interval to suit your music app</li><li>Korean and English interface</li></ul>"),
        ("Good to know","<ul><li>Music apps handle outside play commands differently, so on some apps or phones auto play may be slow or not work. Increasing the start delay usually helps.</li><li>To detect connections while the app is closed, battery optimization may need to be turned off for AutoPlay.</li></ul>")],
  note="7-day free trial with all features, then a one-time purchase. While you use it for free, ads are shown on the home screen; buying removes them.",
  alts=["AutoPlay home screen showing the connected Bluetooth device","Choose which Bluetooth devices trigger playback","Trial and basic settings","Volume and start delay settings"]),
 "ko": dict(path="/autoplay/ko/", name="한국어", og="ko_KR",
  title="음악자동재생 AutoPlay – 차량·블루투스 스피커 연결하면 음악 자동 재생",
  desc="음악자동재생(AutoPlay)은 차량, 블루투스 스피커, 이어폰이 연결되면 고른 음악 앱을 자동으로 재생하고 끊기면 멈춰 주는 안드로이드 앱입니다.",
  h1="음악자동재생 AutoPlay", sub="차에 타거나 블루투스 스피커를 켜면 음악이 알아서 나옵니다. 안드로이드용.",
  cta="Google Play에서 받기 →", back="← Onepixel",
  secs=[("블루투스 연결되면 음악 자동 재생","<p>차량 오디오, 블루투스 스피커, 이어폰 중 원하는 기기와 사용할 음악 앱을 고르세요. 선택한 기기가 연결되면 그 앱을 열고 재생합니다.</p>"),
        ("연결이 끊기면 자동 일시정지","<p>블루투스가 끊기면 음악을 멈춥니다. 전화나 알림 때문에 멈춘 재생은 다시 이어서 재생해 줍니다(알림 접근 권한 필요).</p>"),
        ("주요 기능","<ul><li>페어링된 기기 중 반응할 기기 선택(선택하지 않으면 모든 기기에 반응)</li><li>사용할 음악 앱 선택</li><li>재생이 시작될 때의 볼륨 설정</li><li>음악 앱에 맞춘 재생 대기 시간·재시도 간격 조절</li><li>한국어·영어 지원</li></ul>"),
        ("알아 두세요","<ul><li>음악 앱마다 외부 재생 명령을 받는 방식이 달라, 일부 앱이나 기기에서는 자동 재생이 늦거나 동작하지 않을 수 있습니다. 재생 대기 시간을 늘려 보세요.</li><li>앱이 꺼져 있어도 연결을 감지하려면 배터리 최적화 해제가 필요할 수 있습니다.</li></ul>")],
  note="설치 후 7일간 모든 기능을 무료로 써 볼 수 있고, 이후에는 1회 구매로 계속 이용합니다. 무료로 쓰는 동안 홈 화면에 광고가 표시되며 구매하면 사라집니다.",
  alts=["연결된 블루투스 기기가 보이는 홈 화면","재생을 시작할 블루투스 기기 선택","무료 체험과 기본 설정","볼륨과 재생 대기 시간 설정"]),
 "ja": dict(path="/autoplay/ja/", name="日本語", og="ja_JP",
  title="AutoPlay: Bluetooth接続で音楽を自動再生 – 車・スピーカー対応",
  desc="AutoPlayは、車のBluetooth、Bluetoothスピーカー、イヤホンに接続すると選んだ音楽アプリを自動で再生し、切断すると一時停止するAndroidアプリです。",
  h1="AutoPlay: Bluetooth自動再生", sub="車に乗る、Bluetoothスピーカーをつなぐ。それだけで音楽が自動で流れます。Android対応。",
  cta="Google Playで入手 →", back="← Onepixel",
  secs=[("Bluetooth接続で音楽を自動再生","<p>車のオーディオ、Bluetoothスピーカー、イヤホンなど、反応させたい機器と使う音楽アプリを選びます。選んだ機器が接続されると、そのアプリを開いて再生します。</p>"),
        ("切断すると自動で一時停止","<p>Bluetoothが切れると音楽を止めます。通話や通知で中断された再生は、再開させることもできます（通知へのアクセス権限が必要です）。</p>"),
        ("主な機能","<ul><li>ペアリング済みの機器から反応させる機器を選択（未選択なら全機器に反応）</li><li>使う音楽アプリを選択</li><li>再生開始時の音量を設定</li><li>音楽アプリに合わせて再生までの待ち時間と再試行間隔を調整</li><li>アプリの表示言語は韓国語と英語</li></ul>"),
        ("ご注意","<ul><li>音楽アプリによって外部からの再生命令の扱いが異なるため、アプリや機種によっては自動再生が遅れたり動作しないことがあります。再生までの待ち時間を長くすると改善する場合があります。</li><li>アプリを終了した状態でも接続を検知するには、バッテリーの最適化を解除する必要がある場合があります。</li></ul>")],
  note="インストール後7日間は全機能を無料でお試しいただけ、その後は1回の購入でご利用いただけます。無料の間はホーム画面に広告が表示され、購入すると表示されなくなります。",
  alts=["接続中のBluetooth機器が表示されたホーム画面","再生を開始するBluetooth機器を選択","無料体験と基本設定","音量と再生待ち時間の設定"]),
 "es": dict(path="/autoplay/es/", name="Español", og="es_419",
  title="AutoPlay: reproduce música al conectar Bluetooth – coche y altavoz",
  desc="AutoPlay inicia tu app de música automáticamente cuando el teléfono se conecta al Bluetooth del coche, a un altavoz Bluetooth o a unos auriculares, y la pausa al desconectarse. Para Android.",
  h1="AutoPlay: música automática por Bluetooth", sub="Sube al coche o enciende tu altavoz Bluetooth y la música empieza sola. Para Android.",
  cta="Descargar en Google Play →", back="← Onepixel",
  secs=[("Reproduce música al conectar Bluetooth","<p>Elige los dispositivos que quieres, como el equipo del coche, un altavoz Bluetooth o auriculares, y la app de música que usas. Cuando se conecta uno de ellos, AutoPlay abre esa app y empieza la reproducción.</p>"),
        ("Se pausa al desconectarse","<p>Si el Bluetooth se corta, la música se detiene. Si una llamada o una notificación interrumpió la reproducción, AutoPlay puede reanudarla (requiere acceso a las notificaciones).</p>"),
        ("Qué incluye","<ul><li>Elige qué dispositivos emparejados activan la reproducción, o deja que respondan todos</li><li>Funciona con la app de música que elijas</li><li>Ajusta el volumen al iniciar la reproducción</li><li>Regula la espera inicial y el intervalo de reintento según tu app de música</li><li>Interfaz en coreano e inglés</li></ul>"),
        ("Conviene saber","<ul><li>Cada app de música gestiona de forma distinta las órdenes de reproducción externas, así que en algunas apps o teléfonos la reproducción automática puede tardar o no funcionar. Aumentar la espera suele ayudar.</li><li>Para detectar conexiones con la app cerrada, puede ser necesario desactivar la optimización de batería.</li></ul>")],
  note="Prueba gratuita de 7 días con todas las funciones y después una compra única. Durante la prueba se muestran anuncios en la pantalla de inicio; al comprar desaparecen.",
  alts=["Pantalla de inicio con el dispositivo Bluetooth conectado","Elegir qué dispositivos Bluetooth inician la reproducción","Prueba gratuita y ajustes básicos","Ajustes de volumen y espera de reproducción"]),
 "zh": dict(path="/autoplay/zh/", name="简体中文", og="zh_CN",
  title="AutoPlay：蓝牙连接后自动播放音乐 – 车载与蓝牙音箱",
  desc="AutoPlay 是一款安卓应用：手机连上车载蓝牙、蓝牙音箱或耳机时自动打开你选的音乐应用并开始播放，断开连接时自动暂停。",
  h1="AutoPlay：蓝牙自动播放音乐", sub="上车或打开蓝牙音箱，音乐就自动响起。适用于安卓。",
  cta="在 Google Play 下载 →", back="← Onepixel",
  secs=[("蓝牙连接后自动播放音乐","<p>选择要触发播放的设备（如车载音响、蓝牙音箱、耳机）和你使用的音乐应用。所选设备连接后，AutoPlay 会打开该应用并开始播放。</p>"),
        ("断开连接时自动暂停","<p>蓝牙断开时音乐会停止。若通话或通知打断了播放，AutoPlay 可以帮你恢复（需要通知访问权限）。</p>"),
        ("主要功能","<ul><li>从已配对设备中选择触发播放的设备（不选则对所有设备生效）</li><li>选择要使用的音乐应用</li><li>设置开始播放时的音量</li><li>根据音乐应用调整播放等待时间和重试间隔</li><li>应用界面语言为韩语和英语</li></ul>"),
        ("须知","<ul><li>不同音乐应用处理外部播放指令的方式不同，因此在某些应用或手机上，自动播放可能延迟或无法工作。适当延长播放等待时间通常有帮助。</li><li>若要在应用关闭时也能检测连接，可能需要关闭电池优化。</li></ul>")],
  note="安装后 7 天内可免费体验全部功能，之后一次性购买即可继续使用。免费使用期间主屏幕会显示广告，购买后广告消失。",
  alts=["显示已连接蓝牙设备的主屏幕","选择触发播放的蓝牙设备","免费试用与基本设置","音量与播放等待时间设置"]),
}
HREFLANG = {"en":"en","ko":"ko","ja":"ja","es":"es-419","zh":"zh-Hans"}
def render(code, p):
    canon = BASE + p["path"]
    alts = "\n".join(f'  <link rel="alternate" hreflang="{HREFLANG[c]}" href="{BASE}{q["path"]}">' for c, q in PAGES.items())
    alts += f'\n  <link rel="alternate" hreflang="x-default" href="{BASE}/autoplay/">'
    shots = "\n".join(f'      <img src="/autoplay/img/{n}.jpg" alt="{a}" loading="lazy">' for n, a in zip(SHOT_FILES, p["alts"]))
    secs = "\n".join(f"    <h2>{h}</h2>\n    {b}" for h, b in p["secs"])
    langs = " ".join((f"<b>{q['name']}</b>" if c == code else f'<a href="{q["path"]}" hreflang="{HREFLANG[c]}">{q["name"]}</a>') for c, q in PAGES.items())
    ld = json.dumps({"@context":"https://schema.org","@type":"MobileApplication","name":"AutoPlay","applicationCategory":"MusicApplication","operatingSystem":"Android","description":p["desc"],"url":canon,"downloadUrl":PLAY,"inLanguage":HREFLANG[code],"offers":{"@type":"Offer","price":"0","priceCurrency":"USD"},"author":{"@type":"Organization","name":"Onepixel","url":BASE+"/"}}, ensure_ascii=False)
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
  <meta property="og:image" content="{BASE}/autoplay/img/1-home.png">
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
    <footer>© Onepixel · <a href="https://yhchad.com/privacy/autoplay.html" style="color:#888">Privacy Policy</a></footer>
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
s = re.sub(r"\s*<url><loc>https://onepixel\.yhchad\.com/autoplay/[^<]*</loc>.*?</url>", "", s)
add = "".join(f'  <url><loc>{BASE}{q["path"]}</loc><lastmod>2026-11-23</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>\n' for q in PAGES.values())
s = s.replace("</urlset>", add + "</urlset>"); open(sm, "w").write(s); print("sitemap 갱신")
