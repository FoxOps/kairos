#!/bin/bash
# ============================================================================
# Kairos - Test de charge
# ============================================================================
#
# Wrapper autour de wrk (préféré) ou hey - pas de dépendance Python
# supplémentaire, ces deux outils sont des binaires autonomes.
#
# Prérequis : une instance de l'app déjà lancée (python run.py, ou
# docker compose up) et accessible à l'URL cible, avec un compte de test
# déjà créé (l'endpoint /login exige une authentification pour toutes les
# pages sauf /health, /ready, /version).
#
# Installation :
#   wrk  : https://github.com/wg/wrk (paquet "wrk" sous Arch/chaotic-aur,
#          "wrk" sous Debian/Ubuntu via apt si disponible, sinon compiler
#          depuis les sources - un seul binaire C, pas de runtime requis)
#   hey  : https://github.com/rakyll/hey (binaire Go statique, ou
#          `go install github.com/rakyll/hey@latest`)
#
# Utilisation :
#   scripts/load_test.sh [URL_BASE] [DUREE] [CONNEXIONS] [THREADS]
#
# Exemples :
#   scripts/load_test.sh
#   scripts/load_test.sh http://localhost:5000 30s 50 4
#
# ============================================================================

set -e

BASE_URL="${1:-http://localhost:5000}"
DURATION="${2:-30s}"
CONNECTIONS="${3:-50}"
THREADS="${4:-4}"

# Endpoints publics (pas d'authentification requise) - ceux qui ont le
# plus de sens à charger en boucle sans avoir à gérer une session/cookie
# de connexion dans ce script (voir report/LOAD_TEST_v1.0.md pour une
# méthodologie couvrant aussi les pages authentifiées, via un outil qui
# gère les cookies).
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
    # hey utilise -z pour une durée (au lieu de -n pour un nombre de
    # requêtes fixe) - équivalent de wrk -d.
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
