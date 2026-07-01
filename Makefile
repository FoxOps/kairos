# Makefile pour Leviia Schedule
# Exécutez `make help` pour voir les commandes disponibles

.PHONY: help install test lint format security all clean backup backup-local backup-s3 backup-list backup-restore

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

install: ## Installe les dépendances du projet
	@echo "$(YELLOW)Installation des dépendances...$(NC)"
	pip install -r requirements.txt
	@echo "$(YELLOW)Téléchargement des assets vendor...$(NC)"
	python scripts/download_vendor_assets.py
	@echo "$(GREEN)✓ Dépendances et assets installés$(NC)"

install-boto3: ## Installe boto3 pour les sauvegardes S3
	@echo "$(YELLOW)Installation de boto3 pour les sauvegardes S3...$(NC)"
	pip install boto3
	@echo "$(GREEN)✓ boto3 installé$(NC)"

# Tests
test: ## Exécute les tests avec pytest
	@echo "$(YELLOW)Exécution des tests...$(NC)"
	python -m pytest tests/ -v --tb=short

test-quick: ## Exécute les tests rapidement (sans sortie détaillée)
	@echo "$(YELLOW)Exécution rapide des tests...$(NC)"
	python -m pytest tests/ --tb=no -q

test-coverage: ## Exécute les tests avec couverture de code
	@echo "$(YELLOW)Exécution des tests avec couverture...$(NC)"
	python -m pytest tests/ --cov=app --cov=config --cov-report=term-missing

test-coverage-html: ## Exécute les tests avec couverture et génère un rapport HTML
	@echo "$(YELLOW)Exécution des tests avec couverture (rapport HTML)...$(NC)"
	python -m pytest tests/ --cov=app --cov=config --cov-report=html
	@echo "$(GREEN)✓ Rapport de couverture généré dans htmlcov/$(NC)"

test-coverage-json: ## Exécute les tests avec couverture et génère un rapport JSON
	@echo "$(YELLOW)Exécution des tests avec couverture (rapport JSON)...$(NC)"
	python -m pytest tests/ --cov=app --cov=config --cov-report=json
	@echo "$(GREEN)✓ Rapport de couverture généré$(NC)"

# Tests spécifiques
test-main: ## Exécute les tests pour les routes principales
	@echo "$(YELLOW)Exécution des tests pour main.py...$(NC)"
	python -m pytest tests/test_main_coverage.py -v

test-dark-theme: ## Exécute les tests pour le thème sombre
	@echo "$(YELLOW)Exécution des tests pour le thème sombre...$(NC)"
	python -m pytest tests/test_dark_theme.py -v

# Linting
lint: ## Exécute Ruff et mypy pour vérifier la qualité du code
	@echo "$(YELLOW)Vérification avec Ruff...$(NC)"
	ruff check . --config=.ruff.toml
	@echo "$(YELLOW)Vérification avec mypy...$(NC)"
	mypy app/ tests/ --ignore-missing-imports --allow-untyped-decorators
	@echo "$(GREEN)✓ Linting terminé$(NC)"

# Formatage
format: ## Vérifie le formatage du code avec Black
	@echo "$(YELLOW)Vérification du formatage avec Black...$(NC)"
	black --check . --exclude=".git|__pycache__|instance|venv"
	@echo "$(GREEN)✓ Formatage vérifié$(NC)"

format-fix: ## Applique le formatage avec Black
	@echo "$(YELLOW)Application du formatage avec Black...$(NC)"
	black . --exclude=".git|__pycache__|instance|venv"
	@echo "$(GREEN)✓ Formatage appliqué$(NC)"

# Sécurité
security: ## Exécute Bandit et Safety pour vérifier les vulnérabilités
	@echo "$(YELLOW)Analyse de sécurité avec Bandit...$(NC)"
	bandit -r app/ tests/ -f json -o bandit-results.json || true
	@echo "$(YELLOW)Analyse de sécurité avec Safety...$(NC)"
	safety scan --full-report || true
	@echo "$(GREEN)✓ Analyse de sécurité terminée$(NC)"

# Tout exécuter
all: test lint format security ## Exécute tous les tests, linting, formatage et analyses de sécurité

# Tests complets avec couverture
all-tests: test lint test-coverage ## Exécute tous les tests + linting + couverture

# Nettoyage
clean: ## Nettoie les fichiers temporaires et artifacts
	@echo "$(YELLOW)Nettoyage des fichiers temporaires...$(NC)"
	rm -f bandit-results.json
	rm -rf __pycache__/
	rm -rf *.pyc
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Nettoyage terminé$(NC)"

# ============================================================================
# SAUVEGARDE DE LA BASE DE DONNÉES
# ============================================================================

# Sauvegarde locale par défaut
backup: backup-local ## Crée une sauvegarde locale de la base de données

backup-local: ## Crée une sauvegarde locale de la base de données
	@echo "$(YELLOW)Création d'une sauvegarde locale...$(NC)"
	python scripts/backup_database.py --local --verify
	@echo "$(GREEN)✓ Sauvegarde locale terminée$(NC)"

backup-s3: ## Crée une sauvegarde locale + S3 de la base de données
	@echo "$(YELLOW)Création d'une sauvegarde locale + S3...$(NC)"
	python scripts/backup_database.py --local --s3 --verify
	@echo "$(GREEN)✓ Sauvegarde S3 terminée$(NC)"

backup-full: ## Crée une sauvegarde complète (local + S3 + nettoyage)
	@echo "$(YELLOW)Création d'une sauvegarde complète...$(NC)"
	python scripts/backup_database.py --local --s3 --verify --cleanup
	@echo "$(GREEN)✓ Sauvegarde complète terminée$(NC)"

backup-list: ## Liste toutes les sauvegardes disponibles
	@echo "$(YELLOW)Liste des sauvegardes...$(NC)"
	python scripts/backup_database.py --list

backup-cleanup: ## Nettoie les anciennes sauvegardes
	@echo "$(YELLOW)Nettoyage des anciennes sauvegardes...$(NC)"
	python scripts/backup_database.py --cleanup
	@echo "$(GREEN)✓ Nettoyage terminé$(NC)"

# Restauration (utilisation: make backup-restore BACKUP=chemin/vers/sauvegarde.db)
backup-restore: ## Restaure une sauvegarde (spécifiez BACKUP=chemin/vers/fichier)
	@if [ -z "$(BACKUP)" ]; then \
		echo "$(RED)Erreur: Veuillez spécifier le fichier de sauvegarde avec BACKUP=chemin/vers/fichier$(NC)"; \
		echo "Exemple: make backup-restore BACKUP=backups/leviia_backup_20240101.db.gz"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Restauration de la sauvegarde: $(BACKUP)$(NC)"
	python scripts/backup_database.py --restore $(BACKUP)
	@echo "$(GREEN)✓ Restauration terminée$(NC)"

# ============================================================================
# CHASSE AU BUG
# ============================================================================

bug-hunt: bug-hunt-full ## Exécute une chasse au bug complète

bug-hunt-full: ## Exécute tous les checks de chasse au bug
	@echo "Exécution de la chasse au bug complète..."
	./scripts/bug_hunt.sh --full --report

bug-hunt-security: ## Analyse de sécurité uniquement
	@echo "Analyse de sécurité..."
	./scripts/bug_hunt.sh --security

bug-hunt-lint: ## Vérification du linter uniquement
	@echo "Vérification du linter..."
	./scripts/bug_hunt.sh --lint

bug-hunt-tests: ## Exécution des tests uniquement
	@echo "Exécution des tests..."
	./scripts/bug_hunt.sh --test

bug-hunt-duplicates: ## Recherche de code dupliqué uniquement
	@echo "Recherche de code dupliqué..."
	./scripts/bug_hunt.sh --duplicate

bug-hunt-quick: ## Analyse rapide (sécurité + linter)
	@echo "Analyse rapide..."
	./scripts/bug_hunt.sh --quick

bug-hunt-report: ## Génère un rapport complet
	@echo "Génération du rapport de chasse au bug..."
	./scripts/bug_hunt.sh --full --report

find-duplicates: ## Trouve le code dupliqué
	@echo "Recherche de code dupliqué..."
	python scripts/find_duplicates.py --check-imports
