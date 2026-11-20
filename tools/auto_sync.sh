#!/bin/bash
# 앱 상태 자동 동기화: 스토어 공개 확인 → 카드 생성 → (변경 시) 배포.
# 안전장치: worker.js·_worker.js·wrangler.toml 이 마지막 배포 때와 다르면(다른 세션 작업 중) 배포하지 않는다.
set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
cd "$(dirname "$0")/.."
# google-auth 가 설치된 파이썬을 쓴다(없으면 기본 python3 — 그땐 스토어 공개 확인만 동작)
PY=/Library/Frameworks/Python.framework/Versions/3.14/bin/python3
[ -x "$PY" ] || PY=python3
LOG="$HOME/Library/Logs/onepixel-sync.log"
mkdir -p "$(dirname "$LOG")"
{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S')"
  OUT=$("$PY" tools/sync_apps.py sync 2>&1); echo "$OUT"
  if ! echo "$OUT" | grep -q "index.html 갱신"; then echo "변경 없음 — 배포 안 함"; exit 0; fi
  NOW=$(shasum worker.js _worker.js wrangler.toml | shasum | cut -d' ' -f1)
  if [ "$NOW" != "$(cat tools/.deployed_hash 2>/dev/null)" ]; then
    echo "[중단] worker/설정이 마지막 배포 이후 바뀌었습니다. 사이트 코드는 갱신됐지만 배포는 하지 않았습니다 — 수동 확인 필요"
    exit 2
  fi
  if npx wrangler deploy 2>&1 | grep -q "Success"; then
    echo "배포 완료"
    curl -s -m 15 -o /dev/null -w "라이브 확인 HTTP %{http_code}\n" https://onepixel.yhchad.com/
  else
    echo "[실패] 배포 중 오류"; exit 3
  fi
} >> "$LOG" 2>&1
