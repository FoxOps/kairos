# Makefile ultra-simple pour Leviia Schedule
.PHONY: help build up down logs shell

help: ## Affiche l'aide
	@echo "Commandes Docker pour Leviia Schedule:"
	@echo ""
	@echo "  make -f docker/Makefile build    # Construire l'image"
	@echo "  make -f docker/Makefile up      # Démarrer"
	@echo "  make -f docker/Makefile down    # Arrêter"
	@echo "  make -f docker/Makefile logs    # Voir les logs"
	@echo "  make -f docker/Makefile shell   # Shell dans le conteneur"
	@echo ""

build: ## Construire l'image Docker
	docker compose -f docker/docker-compose.yml build

up: ## Démarrer le conteneur
	docker compose -f docker/docker-compose.yml up -d

down: ## Arrêter le conteneur
	docker compose -f docker/docker-compose.yml down

logs: ## Voir les logs
	docker compose -f docker/docker-compose.yml logs -f

shell: ## Ouvrir un shell dans le conteneur
	docker compose -f docker/docker-compose.yml exec leviia-schedule sh

# Production (avec Gunicorn)
up-prod: ## Démarrer en production
	FLASK_ENV=production docker compose -f docker/docker-compose.yml up -d

down-prod: ## Arrêter la production
	docker compose -f docker/docker-compose.yml down
