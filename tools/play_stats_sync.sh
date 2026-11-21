#!/bin/bash
# Play Console 홈 수치를 읽어 대시보드(KV play-stats)를 갱신한다.
# 실패(로그인 만료 등)하면 맥 알림을 띄운다. 이전 값은 그대로 남고, 대시보드의 '갱신' 시각이 멈춰 보인다.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd "$(dirname "$0")/.."
PY=/Library/Frameworks/Python.framework/Versions/3.14/bin/python3
LOG="$HOME/Library/Logs/onepixel-playstats.log"
mkdir -p "$(dirname "$LOG")"
echo "=== $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG"
OUT=$("$PY" tools/play_console_scrape.py run 2>&1); RC=$?
echo "$OUT" | tail -5 >> "$LOG"
if [ $RC -ne 0 ]; then
  MSG="Play Console 수치 갱신 실패"
  echo "$OUT" | grep -q "로그인이 필요" && MSG="Play Console 로그인 만료 — tools/play_console_scrape.py login 다시 실행"
  osascript -e "display notification \"$MSG\" with title \"원픽셀 대시보드\"" >/dev/null 2>&1
  echo "[실패] $MSG" >> "$LOG"
  exit $RC
fi
