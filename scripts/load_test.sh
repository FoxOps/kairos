#!/bin/bash
# ============================================================================
# Kairos - Load test
# ============================================================================
#
# Wrapper around wrk (preferred) or hey - no extra Python dependency,
# both tools are standalone binaries.
#
# Prerequisites: an already-running app instance (python run.py, or
# docker compose up) reachable at the target URL, with a test account
# already created (the /login endpoint requires authentication for every
# page except /health, /ready, /version).
#
# Install:
#   wrk  : https://github.com/wg/wrk ("wrk" package on Arch/chaotic-aur,
#          "wrk" on Debian/Ubuntu via apt if available, otherwise build
#          from source - a single C binary, no runtime required)
#   hey  : https://github.com/rakyll/hey (static Go binary, or
#          `go install github.com/rakyll/hey@latest`)
#
# Usage:
#   scripts/load_test.sh [BASE_URL] [DURATION] [CONNECTIONS] [THREADS]
#
# Examples:
#   scripts/load_test.sh
#   scripts/load_test.sh http://localhost:5000 30s 50 4
#
# ============================================================================

set -e

BASE_URL="${1:-http://localhost:5000}"
DURATION="${2:-30s}"
CONNECTIONS="${3:-50}"
THREADS="${4:-4}"

# Public endpoints (no authentication required) - the ones that make the
# most sense to load-test in a loop without having to manage a login
# session/cookie in this script (see report/LOAD_TEST_v1.0.md for a
# methodology that also covers authenticated pages, via a tool that
# handles cookies).
ENDPOINTS=(
    "/health"
    "/ready"
    "/version"
    "/login"
)

echo "=== Test de charge Kairos ==="
echo "Cible       : $BASE_URL"
echo "Durée/endpoint : $DURATION"
echo "Connexions  : $CONNECTIONS"
echo "Threads     : $THREADS"
echo ""

run_with_wrk() {
    local url="$1"
    wrk -t"$THREADS" -c"$CONNECTIONS" -d"$DURATION" --latency "$url"
}

run_with_hey() {
    local url="$1"
    # hey uses -z for a duration (instead of -n for a fixed request
    # count) - equivalent of wrk -d.
    hey -z "$DURATION" -c "$CONNECTIONS" "$url"
}

if command -v wrk >/dev/null 2>&1; then
    TOOL="wrk"
elif command -v hey >/dev/null 2>&1; then
    TOOL="hey"
else
    echo "Erreur : ni wrk ni hey ne sont installés." >&2
    echo "" >&2
    echo "Installer l'un des deux :" >&2
    echo "  Arch/chaotic-aur : sudo pacman -S wrk" >&2
    echo "  Debian/Ubuntu    : sudo apt install wrk  (ou compiler depuis les sources)" >&2
    echo "  hey (Go)         : go install github.com/rakyll/hey@latest" >&2
    exit 1
fi

echo "Outil utilisé : $TOOL"
echo ""

for endpoint in "${ENDPOINTS[@]}"; do
    url="${BASE_URL}${endpoint}"
    echo "--- $endpoint ---"
    if [ "$TOOL" = "wrk" ]; then
        run_with_wrk "$url"
    else
        run_with_hey "$url"
    fi
    echo ""
done

echo "=== Terminé ==="
echo "Voir report/LOAD_TEST_v1.0.md pour la méthodologie complète"
echo "(y compris les pages authentifiées) et les résultats de référence."
