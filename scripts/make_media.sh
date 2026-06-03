#!/usr/bin/env bash
# Generate the README media from a running stack:
#   - docs/assets/demo.gif   — terminal recording via VHS (scripts/demo.tape)
#   - docs/assets/report.png — annotation report screenshot via headless Chrome
#
# Usage:
#   make up-d          # bring the stack up first (api + worker + infra)
#   scripts/make_media.sh [--demo|--report]   # default: both
#
# The C4 architecture diagram (docs/assets/architecture-c4.svg) is authored by
# hand and committed directly — it is not regenerated here.
set -euo pipefail

cd "$(dirname "$0")/.."
BASE_URL="${BASE_URL:-http://localhost:8000}"
WHAT="${1:-all}"

log() { printf '\033[36m▸ %s\033[0m\n' "$*"; }
die() { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

require_stack() {
  curl -fsS -o /dev/null --max-time 5 "$BASE_URL/openapi.json" \
    || die "stack not reachable at $BASE_URL — run 'make up-d' first"
}

find_chrome() {
  for c in google-chrome google-chrome-stable chromium chromium-browser; do
    command -v "$c" >/dev/null 2>&1 && { echo "$c"; return; }
  done
  for p in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/Applications/Chromium.app/Contents/MacOS/Chromium"; do
    [ -x "$p" ] && { echo "$p"; return; }
  done
  return 1
}

gen_demo() {
  command -v vhs >/dev/null 2>&1 || die "vhs not installed — see https://github.com/charmbracelet/vhs"
  require_stack
  log "recording terminal demo → docs/assets/demo.gif"
  vhs scripts/demo.tape
}

gen_report() {
  require_stack
  local chrome; chrome="$(find_chrome)" || die "Chrome/Chromium not found"
  log "rendering annotation report HTML"
  uv run python scripts/render_report.py
  log "screenshotting report → docs/assets/report.png  (via $(basename "$chrome"))"
  "$chrome" --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
    --default-background-color=FFFFFFFF --window-size=1180,560 \
    --screenshot="docs/assets/report.png" "file://$PWD/docs/assets/report.html"
  rm -f docs/assets/report.html  # the PNG is the committed artifact
}

case "$WHAT" in
  --demo)   gen_demo ;;
  --report) gen_report ;;
  all|"")   gen_demo; gen_report ;;
  *)        die "unknown option '$WHAT' (use --demo, --report, or no argument)" ;;
esac
log "done."
