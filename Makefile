# COMMANDES DOCKER
# ============================================================================

docker-build: ## Construit l'image Docker
	@echo "$(YELLOW)Construction de l'image Docker...$(NC)"
	docker build -t leviia-schedule .
	@echo "$(GREEN)✓ Image Docker construite$(NC)"

docker-up: ## Démarre les services avec Docker Compose
	@echo "$(YELLOW)Démarrage des services Docker...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services démarrés$(NC)"

docker-down: ## Arrête les services Docker
	@echo "$(YELLOW)Arrêt des services Docker...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services arrêtés$(NC)"

docker-logs: ## Affiche les logs des services Docker
	@echo "$(YELLOW)Affichage des logs...$(NC)"
	docker-compose logs -f app

docker-shell: ## Ouvre un shell dans le conteneur de l'application
	@echo "$(YELLOW)Ouverture d'un shell dans le conteneur...$(NC)"
	docker-compose exec app bash
	@echo "$(GREEN)✓ Shell ouvert$(NC)"

docker-clean: ## Nettoie les conteneurs, images et volumes Docker
	@echo "$(YELLOW)Nettoyage des ressources Docker...$(NC)"
	docker-compose down -v --rmi local
	@echo "$(GREEN)✓ Nettoyage Docker terminé$(NC)"

docker-rebuild: ## Reconstruit et redémarre les services
	@echo "$(YELLOW)Reconstruction et redémarrage...$(NC)"
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
	@echo "$(GREEN)✓ Services reconstruits et redémarrés$(NC)"

docker-ps: ## Affiche l'état des services Docker
	@echo "$(YELLOW)État des services Docker:$(NC)"
	docker-compose ps

docker-test: ## Démarre les services pour les tests (SQLite)
	@echo "$(YELLOW)Démarrage pour les tests avec SQLite...$(NC)"
	DATABASE_URL=sqlite:////app/data/app.db docker-compose up -d app
	@echo "$(GREEN)✓ Services démarrés pour les tests$(NC)"
=======
# ============================================================================
# COMMANDES DOCKER
# ============================================================================

docker-build: ## Construit l'image Docker
	@echo "$(YELLOW)Construction de l'image Docker...$(NC)"
	cd docker && docker build -t leviia-schedule .
	@echo "$(GREEN)✓ Image Docker construite$(NC)"

docker-up: ## Démarre les services avec Docker Compose
	@echo "$(YELLOW)Démarrage des services Docker...$(NC)"
	cd docker && docker-compose up -d
	@echo "$(GREEN)✓ Services démarrés$(NC)"

docker-down: ## Arrête les services Docker
	@echo "$(YELLOW)Arrêt des services Docker...$(NC)"
	cd docker && docker-compose down
	@echo "$(GREEN)✓ Services arrêtés$(NC)"

docker-logs: ## Affiche les logs des services Docker
	@echo "$(YELLOW)Affichage des logs...$(NC)"
	cd docker && docker-compose logs -f app

docker-shell: ## Ouvre un shell dans le conteneur de l'application
	@echo "$(YELLOW)Ouverture d'un shell dans le conteneur...$(NC)"
	cd docker && docker-compose exec app bash
	@echo "$(GREEN)✓ Shell ouvert$(NC)"

docker-clean: ## Nettoie les conteneurs, images et volumes Docker
	@echo "$(YELLOW)Nettoyage des ressources Docker...$(NC)"
	cd docker && docker-compose down -v --rmi local
	@echo "$(GREEN)✓ Nettoyage Docker terminé$(NC)"

docker-rebuild: ## Reconstruit et redémarre les services
	@echo "$(YELLOW)Reconstruction et redémarrage...$(NC)"
	cd docker && docker-compose down
	cd docker && docker-compose build --no-cache
	cd docker && docker-compose up -d
	@echo "$(GREEN)✓ Services reconstruits et redémarrés$(NC)"

docker-ps: ## Affiche l'état des services Docker
	@echo "$(YELLOW)État des services Docker:$(NC)"
	cd docker && docker-compose ps

docker-test: ## Démarre les services pour les tests (SQLite)
	@echo "$(YELLOW)Démarrage pour les tests avec SQLite...$(NC)"
	cd docker && DATABASE_URL=sqlite:////app/data/app.db docker-compose up -d app
	@echo "$(GREEN)✓ Services démarrés pour les tests$(NC)"Makefile pour Leviia Schedule
# Exécutez `make help` pour voir les commandes disponibles

.PHONY: help install test lint format security all clean backup backup-local backup-s3 backup-list backup-restore docker-build docker-up docker-down docker-logs docker-shell docker-clean

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
	@echo "$(GREEN)✓ Dépendances installées$(NC)"

install-boto3: ## Installe boto3 pour les sauvegardes S3
	@echo "$(YELLOW)Installation de boto3 pour les sauvegardes S3...$(NC)"
	pip install boto3
	@echo "$(GREEN)✓ boto3 installé$(NC)"

# Tests
test: ## Exécute les tests avec pytest
	@echo "$(YELLOW)Exécution des tests...$(NC)"
	python -m pytest tests/ -v --tb=short

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
# COMMANDES DOCKER
# ============================================================================

docker-build: ## Construit l'image Docker
	@echo "$(YELLOW)Construction de l'image Docker...$(NC)"
	docker build -t leviia-schedule .
	@echo "$(GREEN)✓ Image Docker construite$(NC)"

docker-up: ## Démarre les services avec Docker Compose
	@echo "$(YELLOW)Démarrage des services Docker...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services démarrés$(NC)"

docker-down: ## Arrête les services Docker
	@echo "$(YELLOW)Arrêt des services Docker...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services arrêtés$(NC)"

docker-logs: ## Affiche les logs des services Docker
	@echo "$(YELLOW)Affichage des logs...$(NC)"
	docker-compose logs -f app

docker-shell: ## Ouvre un shell dans le conteneur de l'application
	@echo "$(YELLOW)Ouverture d'un shell dans le conteneur...$(NC)"
	docker-compose exec app bash
	@echo "$(GREEN)✓ Shell ouvert$(NC)"

docker-clean: ## Nettoie les conteneurs, images et volumes Docker
	@echo "$(YELLOW)Nettoyage des ressources Docker...$(NC)"
	docker-compose down -v --rmi local
	@echo "$(GREEN)✓ Nettoyage Docker terminé$(NC)"

docker-rebuild: ## Reconstruit et redémarre les services
	@echo "$(YELLOW)Reconstruction et redémarrage...$(NC)"
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
	@echo "$(GREEN)✓ Services reconstruits et redémarrés$(NC)"

docker-ps: ## Affiche l'état des services Docker
	@echo "$(YELLOW)État des services Docker:$(NC)"
	docker-compose ps

docker-test: ## Démarre les services pour les tests (SQLite)
	@echo "$(YELLOW)Démarrage pour les tests avec SQLite...$(NC)"
	DATABASE_URL=sqlite:////app/data/app.db docker-compose up -d app
	@echo "$(GREEN)✓ Services démarrés pour les tests$(NC)"
