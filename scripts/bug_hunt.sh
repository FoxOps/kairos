#!/bin/bash

# ============================================================================
# 🎯 Leviia Schedule - Script de Chasse au Bug
# ============================================================================
#
# Ce script automatise la recherche de bugs, problèmes de sécurité,
# code dupliqué et erreurs de style dans le projet.
#
# Usage: ./scripts/bug_hunt.sh [option]
# Options:
#   --full     Exécuter tous les checks (par défaut)
#   --security  Analyser la sécurité uniquement
#   --lint     Vérifier le style de code uniquement
#   --test     Exécuter les tests uniquement
#   --duplicate Chercher le code dupliqué uniquement
#   --quick    Exécuter une analyse rapide
#   --report   Générer un rapport complet
#

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Chemins
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports"
LOGS_DIR="$PROJECT_ROOT/logs"

# Créer les répertoires si ils n'existent pas
mkdir -p "$REPORTS_DIR"
mkdir -p "$LOGS_DIR"

# Fonction pour afficher un titre
title() {
    echo -e "\n${BLUE}================================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}================================================================================${NC}\n"
}

# Fonction pour afficher une section
section() {
    echo -e "\n${CYAN}--- $1 ---${NC}\n"
}

# Fonction pour afficher un résultat
result() {
    local status=$1
    local message=$2
    
    if [ "$status" = "PASS" ] || [ "$status" = "OK" ]; then
        echo -e "${GREEN}✓ [PASS]${NC} $message"
    elif [ "$status" = "FAIL" ] || [ "$status" = "ERROR" ]; then
        echo -e "${RED}✗ [FAIL]${NC} $message"
    elif [ "$status" = "WARN" ]; then
        echo -e "${YELLOW}⚠ [WARN]${NC} $message"
    else
        echo -e "${BLUE}ℹ [INFO]${NC} $message"
    fi
}

# Fonction pour vérifier si une commande existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Fonction pour installer les dépendances manquantes
install_dependencies() {
    title "Installation des dépendances"
    
    local missing=0
    
    # Vérifier et installer pytest
    if ! command_exists pytest; then
        result "WARN" "pytest non trouvé, installation..."
        pip install pytest pytest-cov >/dev/null 2>&1
        missing=$((missing + 1))
    fi
    
    # Vérifier et installer ruff
    if ! command_exists ruff; then
        result "WARN" "ruff non trouvé, installation..."
        pip install ruff >/dev/null 2>&1
        missing=$((missing + 1))
    fi
    
    # Vérifier et installer bandit
    if ! command_exists bandit; then
        result "WARN" "bandit non trouvé, installation..."
        pip install bandit >/dev/null 2>&1
        missing=$((missing + 1))
    fi
    
    # Vérifier et installer safety
    if ! command_exists safety; then
        result "WARN" "safety non trouvé, installation..."
        pip install safety >/dev/null 2>&1
        missing=$((missing + 1))
    fi
    
    if [ $missing -gt 0 ]; then
        result "OK" "$missing dépendances installées"
    else
        result "OK" "Toutes les dépendances sont installées"
    fi
}

# Fonction pour analyser la sécurité
analyze_security() {
    title "Analyse de Sécurité"
    
    section "Bandit (Analyse statique du code)"
    echo "Analyse des problèmes de sécurité dans le code source..."
    bandit -r "$PROJECT_ROOT/app/" -f json -o "$REPORTS_DIR/bandit-results.json" 2>/dev/null
    
    # Compter les résultats
    local bandit_count=$(python3 -c "import json; data=json.load(open('$REPORTS_DIR/bandit-results.json')); print(len(data.get('results', [])))" 2>/dev/null || echo "0")
    
    if [ "$bandit_count" -eq "0" ]; then
        result "PASS" "Bandit: Aucun problème de sécurité détecté"
    else
        result "FAIL" "Bandit: $bandit_count problèmes de sécurité détectés"
        python3 -c "
import json
data = json.load(open('$REPORTS_DIR/bandit-results.json'))
for r in data.get('results', []):
    print(f'  {r[\"issue_severity\"]}:{r[\"issue_confidence\"]} - {r[\"issue_text\"]} ({r[\"filename\"]}:{r[\"line_number\"]})')
" 2>/dev/null
    fi
    
    section "Safety (Vulnérabilités des dépendances)"
    echo "Analyse des vulnérabilités dans les dépendances..."
    safety check --json --output "$REPORTS_DIR/safety-results.json" 2>/dev/null || true
    
    # Compter les vulnérabilités
    local safety_count=$(python3 -c "import json; data=json.load(open('$REPORTS_DIR/safety-results.json')); print(len(data))" 2>/dev/null || echo "0")
    
    if [ "$safety_count" -eq "0" ]; then
        result "PASS" "Safety: Aucune vulnérabilité détectée"
    else
        result "WARN" "Safety: $safety_count vulnérabilités détectées"
        python3 -c "
import json
data = json.load(open('$REPORTS_DIR/safety-results.json'))
for v in data:
    print(f'  {v.get(\"vulnerability_id\", \"N/A\")}: {v.get(\"package\", \"N/A\")} {v.get(\"vulnerable_version\", \"\")} -> {v.get(\"fixed_version\", \"N/A\")}')
" 2>/dev/null
    fi
}

# Fonction pour vérifier le linter
check_linter() {
    title "Vérification du Style de Code (Ruff)"
    
    echo "Exécution de Ruff sur le code source..."
    ruff check "$PROJECT_ROOT/app/" --output-file="$REPORTS_DIR/ruff-results.json" 2>/dev/null || true
    
    # Compter les erreurs
    local ruff_count=$(python3 -c "
import json
try:
    with open('$REPORTS_DIR/ruff-results.json') as f:
        data = json.load(f)
    print(len(data.get('violations', [])))
except:
    print('0')
" 2>/dev/null || echo "0")
    
    if [ "$ruff_count" -eq "0" ]; then
        result "PASS" "Ruff: Aucun problème de style détecté"
    else
        result "FAIL" "Ruff: $ruff_count problèmes de style détectés"
        echo "  Voir $REPORTS_DIR/ruff-results.json pour les détails"
    fi
}

# Fonction pour exécuter les tests
run_tests() {
    title "Exécution des Tests"
    
    echo "Exécution des tests avec pytest..."
    cd "$PROJECT_ROOT"
    
    # Exécuter les tests avec couverture
    pytest tests/ -v --tb=short --cov=app --cov=config --cov-report=term-missing --cov-report=json:"$REPORTS_DIR/coverage-results.json" 2>&1 | tee "$REPORTS_DIR/test-results.log" || true
    
    # Extraire les statistiques
    local passed=$(grep -oP '\d+(?= passed)' "$REPORTS_DIR/test-results.log" | head -1 || echo "0")
    local failed=$(grep -oP '\d+(?= failed)' "$REPORTS_DIR/test-results.log" | head -1 || echo "0")
    local errors=$(grep -oP '\d+(?= error)' "$REPORTS_DIR/test-results.log" | head -1 || echo "0")
    local skipped=$(grep -oP '\d+(?= skipped)' "$REPORTS_DIR/test-results.log" | head -1 || echo "0")
    local coverage=$(grep -oP '\d+%' "$REPORTS_DIR/test-results.log" | head -1 || echo "0%")
    
    result "INFO" "Tests: $passed passés, $failed échoués, $errors erreurs, $skipped ignorés"
    result "INFO" "Couverture: $coverage"
    
    if [ "$failed" -eq "0" ] && [ "$errors" -eq "0" ]; then
        result "PASS" "Tous les tests ont réussi"
    else
        result "FAIL" "$((failed + errors)) tests ont échoué"
    fi
}

# Fonction pour chercher le code dupliqué
find_duplicates() {
    title "Recherche de Code Dupliqué"
    
    echo "Recherche de fonctions et classes dupliquées..."
    
    # Utiliser un script Python pour trouver les doublons
    python3 "$PROJECT_ROOT/scripts/find_duplicates.py" > "$REPORTS_DIR/duplicates-results.txt" 2>&1 || true
    
    local duplicate_count=$(wc -l < "$REPORTS_DIR/duplicates-results.txt" | tr -d ' ')
    
    if [ "$duplicate_count" -gt 0 ]; then
        result "WARN" "Code dupliqué: $duplicate_count instances détectées"
        cat "$REPORTS_DIR/duplicates-results.txt"
    else
        result "PASS" "Aucun code dupliqué détecté"
    fi
}

# Fonction pour générer un rapport complet
generate_report() {
    title "Génération du Rapport Complet"
    
    echo "Génération du rapport de chasse au bug..."
    
    # Créer le rapport
    cat > "$REPORTS_DIR/bug-hunt-report-$(date +%Y%m%d-%H%M%S).md" << 'EOF'
# 🎯 Rapport de Chasse au Bug - Leviia Schedule

**Date :** $(date +"%d %B %Y")  
**Heure :** $(date +"%H:%M:%S")  

## 📊 Sommaire

### Statistiques
EOF
    
    # Ajouter les statistiques
    echo "" >> "$REPORTS_DIR/bug-hunt-report-$(date +%Y%m%d-%H%M%S).md"
    echo "| Catégorie | Statut | Détails |" >> "$REPORTS_DIR/bug-hunt-report-$(date +%Y%m%d-%H%M%S).md"
    echo "|-----------|--------|---------|" >> "$REPORTS_DIR/bug-hunt-report-$(date +%Y%m%d-%H%M%S).md"
    
    # Ajouter les résultats
    echo "| Sécurité (Bandit) | $(if [ "$bandit_count" -eq "0" ]; then echo "✅ PASS"; else echo "❌ FAIL"; fi) | $bandit_count problèmes |" >> "$REPORTS_DIR/bug-hunt-report-$(date +%Y%m%d-%H%M%S).md"
    echo "| Sécurité (Safety) | $(if [ "$safety_count" -eq "0" ]; then echo "✅ PASS"; else echo "⚠️ WARN"; fi) | $safety_count vulnérabilités |" >> "$REPORTS_DIR/bug-hunt-report-$(date +%Y%m%d-%H%M%S).md"
    echo "| Style de Code | $(if [ "$ruff_count" -eq "0" ]; then echo "✅ PASS"; else echo "❌ FAIL"; fi) | $ruff_count problèmes |" >> "$REPORTS_DIR/bug-hunt-report-$(date +%Y%m%d-%H%M%S).md"
    echo "| Tests | $(if [ "$failed" -eq "0" ] && [ "$errors" -eq "0" ]; then echo "✅ PASS"; else echo "❌ FAIL"; fi) | $passed passés, $failed échoués |" >> "$REPORTS_DIR/bug-hunt-report-$(date +%Y%m%d-%H%M%S).md"
    echo "| Code Dupliqué | ⚠️ WARN | $duplicate_count instances |" >> "$REPORTS_DIR/bug-hunt-report-$(date +%Y%m%d-%H%M%S).md"
    echo "| Couverture | ℹ️ INFO | $coverage |" >> "$REPORTS_DIR/bug-hunt-report-$(date +%Y%m%d-%H%M%S).md"
    
    result "OK" "Rapport généré: $REPORTS_DIR/bug-hunt-report-$(date +%Y%m%d-%H%M%S).md"
}

# Fonction pour afficher l'aide
show_help() {
    echo "Usage: $0 [option]"
    echo ""
    echo "Options:"
    echo "  --full     Exécuter tous les checks (par défaut)"
    echo "  --security  Analyser la sécurité uniquement"
    echo "  --lint     Vérifier le style de code uniquement"
    echo "  --test     Exécuter les tests uniquement"
    echo "  --duplicate Chercher le code dupliqué uniquement"
    echo "  --quick    Exécuter une analyse rapide (sécurité + linter)"
    echo "  --report   Générer un rapport complet"
    echo "  --help     Afficher cette aide"
    echo ""
    echo "Exemples:"
    echo "  $0 --full"
    echo "  $0 --security --lint"
    echo "  $0 --quick --report"
}

# Script Python pour trouver les doublons
cat > "$PROJECT_ROOT/scripts/find_duplicates.py" << 'PYEOF'
import os
import hashlib
from collections import defaultdict

def find_duplicates(directory, min_lines=5):
    """Trouve les fonctions et classes dupliquées."""
    files = []
    for root, dirs, filenames in os.walk(directory):
        # Ignorer les répertoires .git et __pycache__
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'venv', 'instance']]
        for filename in filenames:
            if filename.endswith('.py'):
                filepath = os.path.join(root, filename)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    files.append((filepath, content))
    
    # Trouver les fonctions/classes dupliquées
    funcs = defaultdict(list)
    for filepath, content in files:
        lines = content.split('\n')
        in_func = False
        func_start = 0
        func_name = ''
        indent_level = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Détecter le début d'une fonction ou classe
            if stripped.startswith('def ') or stripped.startswith('class '):
                in_func = True
                func_start = i
                func_name = stripped
                indent_level = len(line) - len(line.lstrip())
            
            # Détecter la fin d'une fonction ou classe
            elif in_func:
                current_indent = len(line) - len(line.lstrip())
                # Si on revient à un niveau d'indentation inférieur ou égal
                if line.strip() and current_indent <= indent_level:
                    in_func = False
                    func_code = '\n'.join(lines[func_start:i])
                    if len(func_code.split('\n')) >= min_lines:
                        func_hash = hashlib.md5(func_code.encode()).hexdigest()
                        funcs[func_hash].append((filepath, func_name, func_start + 1))
    
    # Filtrer les doublons
    duplicates = {k: v for k, v in funcs.items() if len(v) > 1}
    return duplicates

if __name__ == '__main__':
    duplicates = find_duplicates('$PROJECT_ROOT/app')
    
    if not duplicates:
        print("Aucun code dupliqué détecté.")
    else:
        print(f"Trouvé {len(duplicates)} groupes de code dupliqué:\n")
        for i, (hash_val, funcs) in enumerate(duplicates.items(), 1):
            print(f"{i}. {funcs[0][1]}")
            for filepath, func_name, line in funcs:
                print(f"   - {filepath}:{line}")
            print()
PYEOF

# Vérifier les arguments
if [ $# -eq 0 ]; then
    MODE="full"
else
    MODE=""
    for arg in "$@"; do
        case "$arg" in
            --full) MODE="full" ;;
            --security) MODE="$MODE security" ;;
            --lint) MODE="$MODE lint" ;;
            --test) MODE="$MODE test" ;;
            --duplicate) MODE="$MODE duplicate" ;;
            --quick) MODE="security lint" ;;
            --report) REPORT="yes" ;;
            --help) show_help; exit 0 ;;
            *) echo "Option inconnue: $arg"; show_help; exit 1 ;;
        esac
    done
fi

# Installer les dépendances
install_dependencies

# Variables pour stocker les résultats
bandit_count=0
safety_count=0
ruff_count=0
passed=0
failed=0
errors=0
skipped=0
coverage="0%"
duplicate_count=0

# Exécuter les checks selon le mode
if [[ "$MODE" == *"security"* ]] || [[ "$MODE" == "full" ]]; then
    analyze_security
fi

if [[ "$MODE" == *"lint"* ]] || [[ "$MODE" == "full" ]]; then
    check_linter
fi

if [[ "$MODE" == *"test"* ]] || [[ "$MODE" == "full" ]]; then
    run_tests
fi

if [[ "$MODE" == *"duplicate"* ]] || [[ "$MODE" == "full" ]]; then
    find_duplicates
fi

# Générer le rapport si demandé
if [ "$REPORT" = "yes" ]; then
    generate_report
fi

# Afficher un résumé
title "Résumé de la Chasse au Bug"

echo ""
echo "📊 Statistiques:"
echo "  Sécurité (Bandit):  $bandit_count problèmes"
echo "  Sécurité (Safety):  $safety_count vulnérabilités"
echo "  Style de Code:      $ruff_count problèmes"
echo "  Tests:              $passed passés, $failed échoués"
echo "  Code Dupliqué:     $duplicate_count instances"
echo "  Couverture:        $coverage"
echo ""

# Calculer un score global
score=100
if [ "$bandit_count" -gt 0 ]; then
    score=$((score - 10))
fi
if [ "$safety_count" -gt 0 ]; then
    score=$((score - 10))
fi
if [ "$ruff_count" -gt 0 ]; then
    score=$((score - 15))
fi
if [ "$failed" -gt 0 ]; then
    score=$((score - 20))
fi
if [ "$duplicate_count" -gt 0 ]; then
    score=$((score - 10))
fi

if [ $score -ge 90 ]; then
    grade="A ✅"
elif [ $score -ge 80 ]; then
    grade="B ✅"
elif [ $score -ge 70 ]; then
    grade="C ⚠️"
elif [ $score -ge 60 ]; then
    grade="D ⚠️"
else
    grade="F ❌"
fi

echo "🎯 Score Global: $score/100 ($grade)"
echo ""

if [ $score -ge 80 ]; then
    result "PASS" "Le code est en bonne santé !"
elif [ $score -ge 60 ]; then
    result "WARN" "Des améliorations sont nécessaires."
else
    result "FAIL" "Des corrections urgentes sont nécessaires."
fi

echo ""
echo "📁 Rapports générés dans: $REPORTS_DIR/"
ls -la "$REPORTS_DIR/" 2>/dev/null || echo "Aucun rapport généré."

echo ""
echo "💡 Pour plus de détails, consultez les rapports dans $REPORTS_DIR/"
