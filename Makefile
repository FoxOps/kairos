# Makefile pour Kairos
# Exécutez `make help` pour voir les commandes disponibles
#
# Objectif : ne garder que l'essentiel. Toute variante ponctuelle (un
# sous-dossier de tests précis, un rapport de couverture HTML/JSON, une
# combinaison S3/nettoyage/liste de sauvegardes...) reste une invocation
# directe des outils sous-jacents plutôt qu'une cible dédiée - voir les
# exemples en commentaire sous test/test-coverage/backup ci-dessous et
# Docs/deployment/BACKUP_GUIDE.md pour les sauvegardes.

.PHONY: help install test test-coverage lint format format-fix security all clean find-duplicates backup backup-restore babel-update babel-compile

# Couleurs pour les messages
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

help: ## Affiche cette aide
	@echo "Commandes disponibles :"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

install: ## Installe les dépendances du projet (+ boto3 : pip install boto3, pour les sauvegardes S3)
	@echo "$(YELLOW)Installation des dépendances...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)✓ Dépendances installées$(NC)"

test: ## Exécute la suite de tests complète
	@echo "$(YELLOW)Exécution des tests...$(NC)"
	python -m pytest tests/ -v --tb=short
	# Un sous-ensemble ciblé : pytest tests/unit/ -v (ou tests/integration/, tests/e2e/, un fichier précis)

test-coverage: ## Exécute les tests avec couverture de code (terminal)
	@echo "$(YELLOW)Exécution des tests avec couverture...$(NC)"
	python -m pytest tests/ --cov=app --cov-report=term-missing
	# Rapport HTML : ajouter --cov-report=html (ouvre htmlcov/index.html)
	# Rapport JSON : ajouter --cov-report=json

lint: ## Exécute Ruff et mypy pour vérifier la qualité du code
	@echo "$(YELLOW)Vérification avec Ruff...$(NC)"
	ruff check . --config=.ruff.toml
	@echo "$(YELLOW)Vérification avec mypy...$(NC)"
	mypy app/ tests/ --ignore-missing-imports --allow-untyped-decorators
	@echo "$(GREEN)✓ Linting terminé$(NC)"

format: ## Vérifie le formatage du code avec Black
	@echo "$(YELLOW)Vérification du formatage avec Black...$(NC)"
	black --check . --exclude=".git|__pycache__|instance|venv"
	@echo "$(GREEN)✓ Formatage vérifié$(NC)"

format-fix: ## Applique le formatage avec Black
	@echo "$(YELLOW)Application du formatage avec Black...$(NC)"
	black . --exclude=".git|__pycache__|instance|venv"
	@echo "$(GREEN)✓ Formatage appliqué$(NC)"

security: ## Exécute Bandit et pip-audit pour vérifier les vulnérabilités
	@echo "$(YELLOW)Analyse de sécurité avec Bandit...$(NC)"
	bandit -r app/ tests/ -f json -o bandit-results.json || true
	@echo "$(YELLOW)Analyse des dépendances avec pip-audit...$(NC)"
	pip-audit -r requirements.txt || true
	@echo "$(GREEN)✓ Analyse de sécurité terminée$(NC)"

all: test lint format security ## Exécute tous les tests, linting, formatage et analyses de sécurité

clean: ## Nettoie les fichiers temporaires et artifacts
	@echo "$(YELLOW)Nettoyage des fichiers temporaires...$(NC)"
	rm -f bandit-results.json
	rm -rf __pycache__/
	rm -rf *.pyc
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Nettoyage terminé$(NC)"

find-duplicates: ## Trouve le code dupliqué (fonctions/classes/imports)
	@echo "Recherche de code dupliqué..."
	python scripts/find_duplicates.py --check-imports

# ============================================================================
# SAUVEGARDE DE LA BASE DE DONNÉES
# ============================================================================
# Combinaisons S3 / nettoyage / liste : voir Docs/deployment/BACKUP_GUIDE.md
# pour les invocations directes de scripts/backup_database.py
# (--s3, --cleanup, --list...).

backup: ## Crée une sauvegarde locale de la base de données
	@echo "$(YELLOW)Création d'une sauvegarde locale...$(NC)"
	python scripts/backup_database.py --local --verify
	@echo "$(GREEN)✓ Sauvegarde locale terminée$(NC)"

backup-restore: ## Restaure une sauvegarde (spécifiez BACKUP=chemin/vers/fichier)
	@if [ -z "$(BACKUP)" ]; then \
		echo "$(RED)Erreur: Veuillez spécifier le fichier de sauvegarde avec BACKUP=chemin/vers/fichier$(NC)"; \
		echo "Exemple: make backup-restore BACKUP=backups/kairos_backup_20240101.db.gz"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Restauration de la sauvegarde: $(BACKUP)$(NC)"
	python scripts/backup_database.py --restore $(BACKUP)
	@echo "$(GREEN)✓ Restauration terminée$(NC)"

# ============================================================================
# TRADUCTIONS (i18n, Flask-Babel)
# ============================================================================

babel-extract:
	@echo "$(YELLOW)Extraction des chaînes traduisibles...$(NC)"
	pybabel extract -F babel.cfg -o app/translations/messages.pot .

babel-update: babel-extract ## Extrait et met à jour les catalogues .po (fr/en)
	@echo "$(YELLOW)Mise à jour des catalogues de traduction...$(NC)"
	pybabel update -i app/translations/messages.pot -d app/translations -l fr
	pybabel update -i app/translations/messages.pot -d app/translations -l en
	python scripts/fill_fr_catalog.py
	@echo "$(GREEN)✓ Catalogues fr/en mis à jour$(NC)"
	@echo "$(YELLOW)⚠ Vérifiez app/translations/en/LC_MESSAGES/messages.po : les nouvelles chaînes ont un msgstr vide/fuzzy à traduire à la main.$(NC)"

babel-compile: ## Compile les catalogues .po en .mo (requis avant de lancer l'app)
	@echo "$(YELLOW)Compilation des catalogues de traduction...$(NC)"
	pybabel compile -d app/translations
	@echo "$(GREEN)✓ Catalogues compilés (.mo)$(NC)"
