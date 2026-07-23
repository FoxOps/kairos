# Makefile for Kairos
# Run `make help` to see the available commands
#
# Goal: keep only the essentials. Any one-off variant (a specific test
# subdirectory, an HTML/JSON coverage report, an S3/cleanup/list-backups
# combination...) stays a direct invocation of the underlying tool rather
# than a dedicated target - see the commented examples under
# test/test-coverage/backup below, and Docs/deployment/BACKUP_GUIDE.md
# for backups.

.PHONY: help install test test-coverage lint format format-fix security all clean find-duplicates backup backup-restore babel-update babel-compile bump-version check-version

# Colors for messages
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

help: ## Show this help
	@echo "Commandes disponibles :"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

install: ## Install project dependencies (+ boto3: pip install boto3, for S3 backups)
	@echo "$(YELLOW)Installation des dépendances...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)✓ Dépendances installées$(NC)"

test: ## Run the full test suite
	@echo "$(YELLOW)Exécution des tests...$(NC)"
	python -m pytest tests/ -v --tb=short
	# A targeted subset: pytest tests/unit/ -v (or tests/integration/, tests/e2e/, a specific file)

test-coverage: ## Run the tests with code coverage (terminal)
	@echo "$(YELLOW)Exécution des tests avec couverture...$(NC)"
	python -m pytest tests/ --cov=app --cov-report=term-missing
	# HTML report: add --cov-report=html (opens htmlcov/index.html)
	# JSON report: add --cov-report=json

lint: ## Run Ruff, mypy and djlint (Jinja templates) to check code quality
	@echo "$(YELLOW)Vérification avec Ruff...$(NC)"
	ruff check . --config=.ruff.toml
	@echo "$(YELLOW)Vérification avec mypy...$(NC)"
	mypy app/ tests/ --ignore-missing-imports --allow-untyped-decorators
	@echo "$(YELLOW)Vérification des templates avec djlint...$(NC)"
	djlint app/templates
	@echo "$(GREEN)✓ Linting terminé$(NC)"

format: ## Check code formatting with Black
	@echo "$(YELLOW)Vérification du formatage avec Black...$(NC)"
	black --check . --exclude=".git|__pycache__|instance|venv"
	@echo "$(GREEN)✓ Formatage vérifié$(NC)"

format-fix: ## Apply formatting with Black
	@echo "$(YELLOW)Application du formatage avec Black...$(NC)"
	black . --exclude=".git|__pycache__|instance|venv"
	@echo "$(GREEN)✓ Formatage appliqué$(NC)"

security: ## Run Bandit and pip-audit to check for vulnerabilities
	@echo "$(YELLOW)Analyse de sécurité avec Bandit...$(NC)"
	bandit -r app/ tests/ -f json -o bandit-results.json || true
	@echo "$(YELLOW)Analyse des dépendances avec pip-audit...$(NC)"
	pip-audit -r requirements.txt || true
	@echo "$(GREEN)✓ Analyse de sécurité terminée$(NC)"

all: test lint format security ## Run all tests, linting, formatting and security scans

clean: ## Clean up temporary files and artifacts
	@echo "$(YELLOW)Nettoyage des fichiers temporaires...$(NC)"
	rm -f bandit-results.json
	rm -rf __pycache__/
	rm -rf *.pyc
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Nettoyage terminé$(NC)"

find-duplicates: ## Find duplicated code (functions/classes/imports)
	@echo "Recherche de code dupliqué..."
	python scripts/find_duplicates.py --check-imports

# ============================================================================
# VERSIONING (see Docs/reference/VERSIONING.md)
# ============================================================================

bump-version: ## Update the version in health.py/.env.example (VERSION=1.0.0-rc4)
	@if [ -z "$(VERSION)" ]; then \
		echo "$(RED)Erreur: précisez VERSION=1.0.0-rc4 (ou 1.0.0)$(NC)"; \
		exit 1; \
	fi
	python scripts/bump_version.py $(VERSION)

check-version: ## Check that the current git tag matches APP_VERSION_DEFAULT
	python scripts/check_version.py

# ============================================================================
# DATABASE BACKUP
# ============================================================================
# S3 / cleanup / list combinations: see Docs/deployment/BACKUP_GUIDE.md
# for direct invocations of scripts/backup_database.py
# (--s3, --cleanup, --list...).

backup: ## Create a local database backup
	@echo "$(YELLOW)Création d'une sauvegarde locale...$(NC)"
	python scripts/backup_database.py --local --verify
	@echo "$(GREEN)✓ Sauvegarde locale terminée$(NC)"

backup-restore: ## Restore a backup (specify BACKUP=path/to/file)
	@if [ -z "$(BACKUP)" ]; then \
		echo "$(RED)Erreur: Veuillez spécifier le fichier de sauvegarde avec BACKUP=chemin/vers/fichier$(NC)"; \
		echo "Exemple: make backup-restore BACKUP=backups/kairos_backup_20240101.db.gz"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Restauration de la sauvegarde: $(BACKUP)$(NC)"
	python scripts/backup_database.py --restore $(BACKUP)
	@echo "$(GREEN)✓ Restauration terminée$(NC)"

# ============================================================================
# TRANSLATIONS (i18n, Flask-Babel)
# ============================================================================

babel-extract:
	@echo "$(YELLOW)Extraction des chaînes traduisibles...$(NC)"
	pybabel extract -F babel.cfg -o app/translations/messages.pot .

babel-update: babel-extract ## Extract and update the .po catalogs (fr/en)
	@echo "$(YELLOW)Mise à jour des catalogues de traduction...$(NC)"
	pybabel update -i app/translations/messages.pot -d app/translations -l fr
	pybabel update -i app/translations/messages.pot -d app/translations -l en
	python scripts/fill_fr_catalog.py
	@echo "$(GREEN)✓ Catalogues fr/en mis à jour$(NC)"
	@echo "$(YELLOW)⚠ Vérifiez app/translations/en/LC_MESSAGES/messages.po : les nouvelles chaînes ont un msgstr vide/fuzzy à traduire à la main.$(NC)"

babel-compile: ## Compile the .po catalogs into .mo (required before running the app)
	@echo "$(YELLOW)Compilation des catalogues de traduction...$(NC)"
	pybabel compile -d app/translations
	@echo "$(GREEN)✓ Catalogues compilés (.mo)$(NC)"
