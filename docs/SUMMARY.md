# 📚 Documentation Complète - Leviia Schedule

> **Version** : 1.0.0 - Documentation Technique, API et Architecture
> **Dernière mise à jour** : Juin 2026
> **Statut** : Développement actif

---

## 📋 Table des Matières

- [📖 Introduction](#-introduction)
- [🏗️ Architecture Technique](#-architecture-technique)
- [📡 API REST](#-api-rest)
- [🛡️ Gestion des Erreurs](#-gestion-des-erreurs)
- [📁 Structure de la Documentation](#-structure-de-la-documentation)
- [🚀 Comment Utiliser cette Documentation](#-comment-utiliser-cette-documentation)
- [📊 Résumé des Composants](#-résumé-des-composants)
- [🔧 Configuration Rapide](#-configuration-rapide)
- [📝 Historique des Changements](#-historique-des-changements)

---

## 📖 Introduction

Bienvenue dans la **documentation complète** de **Leviia Schedule**, une application web de gestion des plannings et des astreintes conçue pour les équipes et organisations.

### À propos de Leviia Schedule

**Leviia Schedule** est une solution complète pour :
- ✅ Gérer les horaires de travail (shifts)
- ✅ Planifier les rotations d'astreinte (On-Call)
- ✅ Suivre les congés et absences
- ✅ Exporter les données vers les calendriers externes (ICS)
- ✅ Gérer les utilisateurs et les permissions

### Public Cible

Cette documentation s'adresse à :
- **Développeurs** : Pour comprendre l'architecture, l'API et contribuer au projet
- **Administrateurs** : Pour configurer, déployer et maintenir l'application
- **Utilisateurs techniques** : Pour comprendre les fonctionnalités avancées

---

## 🏗️ Architecture Technique

### Vue d'ensemble

L'architecture de Leviia Schedule suit une approche **modulaire et en couches** :

```
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE PRÉSENTATION                        │
│  (Templates Jinja2, CSS, JavaScript)                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE APPLICATION                         │
│  (Flask, Routes, Services, Middleware)                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE DONNÉES                             │
│  (SQLAlchemy, Modèles, ORM)                                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE PERSISTANCE                         │
│  (SQLite/PostgreSQL/MySQL)                                   │
└─────────────────────────────────────────────────────────────┘
```

### Technologies Utilisées

| Composant | Technologie | Version | Rôle |
|-----------|-------------|---------|------|
| **Framework Web** | Flask | 3.1.1 | Framework principal |
| **ORM** | SQLAlchemy | 2.0.36 | Mapping Objet-Relationnel |
| **Base de données** | SQLite | - | Base de données par défaut |
| **Authentification** | Flask-Login | 0.6.3 | Gestion des sessions |
| **Export ICS** | icalendar | 5.0.14 | Génération de fichiers ICS |
| **Tests** | pytest | 8.3.5 | Exécution des tests |
| **Linting** | Ruff | 0.6.4 | Vérification du style |
| **Typage** | mypy | 1.12.0 | Vérification des types |
| **Formatage** | Black | 24.10.0 | Formatage du code |

### Principes de Conception

1. **Simplicité** : Architecture claire et maintenable
2. **Modularité** : Composants indépendants et réutilisables
3. **Extensibilité** : Facilité d'ajout de nouvelles fonctionnalités
4. **Sécurité** : Protection des données et prévention des vulnérabilités
5. **Performance** : Optimisation des requêtes et du temps de réponse

### Documentation Détaillée

Pour une documentation complète de l'architecture, voir :
📄 **[ARCHITECTURE.md](./ARCHITECTURE.md)**

Ce document contient :
- Diagrammes d'architecture détaillés
- Description des composants techniques
- Modèles de données complets
- Flux de données
- Configuration et déploiement
- Bonnes pratiques

---

## 📡 API REST

### Vue d'ensemble

L'API REST de Leviia Schedule permet d'interagir avec toutes les fonctionnalités de l'application :

- **Format** : JSON (sauf export ICS : `text/calendar`)
- **Authentification** : Sessions (Flask-Login) ou Tokens ICS
- **Base URL** : `http://localhost:5000` (dev) / `https://votre-domaine.com` (prod)

### Catégories d'Endpoints

| Catégorie | Préfixe | Description | Accès |
|----------|---------|-------------|-------|
| **Authentification** | `/login`, `/logout`, `/profile` | Gestion des utilisateurs | Public/Privé |
| **Utilisateurs** | `/admin/users` | Gestion des utilisateurs | Admin |
| **Groupes** | `/admin/groups` | Gestion des groupes | Admin |
| **Types de Shifts** | `/admin/shift-types` | Gestion des types | Admin |
| **Shifts** | `/schedule` | Gestion des shifts | Utilisateur |
| **Astreintes** | `/oncall` | Gestion des astreintes | Utilisateur |
| **Congés** | `/leaves` | Gestion des congés | Utilisateur |
| **Export** | `/export` | Export ICS | Utilisateur |
| **Administration** | `/admin` | Dashboard et outils | Admin |

### Endpoints Principaux

#### Authentification
- `POST /login` - Connexion
- `GET /logout` - Déconnexion
- `GET /profile` - Récupérer le profil
- `POST /profile/update` - Mettre à jour le profil

#### Utilisateurs (Admin)
- `GET /admin/users` - Lister les utilisateurs
- `POST /admin/users/add` - Ajouter un utilisateur
- `POST /admin/users/edit/<id>` - Modifier un utilisateur
- `POST /admin/users/delete/<id>` - Supprimer un utilisateur
- `POST /admin/users/generate-token/<id>` - Générer un token ICS

#### Groupes (Admin)
- `GET /admin/groups` - Lister les groupes
- `POST /admin/groups/add` - Ajouter un groupe
- `POST /admin/groups/edit/<id>` - Modifier un groupe
- `POST /admin/groups/delete/<id>` - Supprimer un groupe

#### Types de Shifts (Admin)
- `GET /admin/shift-types` - Lister les types
- `POST /admin/shift-types/add` - Ajouter un type
- `POST /admin/shift-types/edit/<id>` - Modifier un type
- `POST /admin/shift-types/delete/<id>` - Supprimer un type

#### Shifts
- `GET /schedule` - Afficher le planning
- `POST /schedule/shift` - Ajouter un shift
- `POST /schedule/shift/<id>/delete` - Supprimer un shift
- `GET /schedule/my-shifts` - Mes shifts

#### Astreintes
- `GET /oncall` - Afficher les astreintes
- `POST /oncall` - Ajouter une astreinte
- `POST /oncall/<id>/delete` - Supprimer une astreinte
- `GET /oncall/my-oncalls` - Mes astreintes

#### Congés
- `GET /leaves` - Afficher les congés
- `POST /leaves` - Ajouter un congé
- `POST /leaves/<id>/delete` - Supprimer un congé
- `GET /leaves/my-leaves` - Mes congés

#### Export ICS
- `GET /export/shifts` - Exporter les shifts
- `GET /export/oncall` - Exporter les astreintes
- `GET /export/leaves` - Exporter les congés

#### Administration
- `GET /admin` - Dashboard
- `GET /admin/automation` - Statut de l'automatisation
- `POST /admin/automation/run` - Exécuter l'automatisation
- `GET /admin/cleanup` - Nettoyer les données

### Documentation Détaillée

Pour une documentation complète de l'API, voir :
📄 **[API.md](./API.md)**

Ce document contient :
- Description détaillée de tous les endpoints
- Schémas de données
- Exemples de requêtes (cURL)
- Codes de réponse
- Bonnes pratiques

---

## 🛡️ Gestion des Erreurs

### Vue d'ensemble

Leviia Schedule implémente une **gestion des erreurs avancée** avec :

- **Pages d'erreur personnalisées** pour tous les codes HTTP principaux
- **Gestionnaires d'exceptions** pour les erreurs Python
- **Système de logging complet** avec rotation des fichiers
- **Audit logging** pour tracer les actions utilisateur
- **Filtrage des données sensibles** dans les logs

### Codes HTTP Gérés

| Code | Nom | Page Personnalisée | Description |
|------|-----|-------------------|-------------|
| 400 | Bad Request | ✅ `400.html` | Requête mal formée |
| 401 | Unauthorized | ✅ `401.html` | Authentification requise |
| 403 | Forbidden | ✅ `403.html` | Accès interdit |
| 404 | Not Found | ✅ `404.html` | Page non trouvée |
| 405 | Method Not Allowed | ✅ `405.html` | Méthode non autorisée |
| 500 | Internal Server Error | ✅ `500.html` | Erreur serveur |
| 502 | Bad Gateway | ✅ `502.html` | Mauvaise passerelle |
| 503 | Service Unavailable | ✅ `503.html` | Service indisponible |
| 504 | Gateway Timeout | ✅ `504.html` | Délai dépassé |

### Système de Logging

#### Fichiers de Log

| Fichier | Niveau | Description |
|--------|--------|-------------|
| `leviia-app.log` | INFO | Logs généraux de l'application |
| `leviia-errors.log` | ERROR | Toutes les erreurs |
| `leviia-http-errors.log` | WARNING | Erreurs HTTP avec contexte |
| `leviia-debug.log` | DEBUG | Logs de débogage |
| `leviia-audit.log` | INFO | Actions utilisateur |
| `leviia-sql.log` | DEBUG | Requêtes SQL |
| `leviia-auth.log` | INFO | Événements d'authentification |

#### Configuration

```bash
# Niveau de log principal
export LOG_LEVEL=INFO

# Taille des fichiers (5 Mo par défaut)
export LOG_FILE_SIZE=5242880

# Nombre de backups (10 par défaut)
export LOG_BACKUP_COUNT=10

# Dossier des logs
export LOG_DIR=/var/log/leviia

# Activer syslog
export SYSLOG_ENABLED=true
export SYSLOG_ADDRESS=/dev/log

# Filtrer les données sensibles
export LOG_FILTER_SENSITIVE=true
```

### Documentation Détaillée

Pour une documentation complète de la gestion des erreurs, voir :
📄 **[ERROR_HANDLING.md](./ERROR_HANDLING.md)**

Ce document contient :
- Architecture de la gestion des erreurs
- Implémentation des pages d'erreur personnalisées
- Configuration du logging
- Gestionnaires d'exceptions
- Exemples de code
- Tests

---

## 📁 Structure de la Documentation

```
docs/
├── 📄 ARCHITECTURE.md          # Architecture technique complète
│   ├── Vue d'ensemble
│   ├── Composants techniques
│   ├── Modèles de données
│   ├── Flux de données
│   ├── Sécurité
│   ├── Environnements
│   ├── Performances
│   └── Configuration
│
├── 📄 API.md                   # Documentation API REST
│   ├── Authentification
│   ├── Endpoints (par catégorie)
│   ├── Schémas de données
│   ├── Exemples de requêtes
│   ├── Codes de réponse
│   └── Bonnes pratiques
│
├── 📄 ERROR_HANDLING.md       # Gestion des erreurs et logging
│   ├── Architecture de la gestion des erreurs
│   ├── Pages d'erreur personnalisées
│   ├── Gestionnaires d'erreurs HTTP
│   ├── Gestion des exceptions
│   ├── Système de logging
│   └── Configuration
│
└── 📄 SUMMARY.md              # Ce fichier - Résumé complet
```

---

## 🚀 Comment Utiliser cette Documentation

### Pour les Développeurs

1. **Comprendre l'architecture** : Commencez par [ARCHITECTURE.md](./ARCHITECTURE.md)
2. **Explorer l'API** : Consultez [API.md](./API.md) pour les endpoints
3. **Gérer les erreurs** : Voir [ERROR_HANDLING.md](./ERROR_HANDLING.md)
4. **Contribuer** : Suivez les bonnes pratiques dans chaque document

### Pour les Administrateurs

1. **Configurer l'application** : Voir la section Configuration dans [ARCHITECTURE.md](./ARCHITECTURE.md)
2. **Configurer le logging** : Voir [ERROR_HANDLING.md](./ERROR_HANDLING.md)
3. **Surveiller les erreurs** : Consulter les fichiers de log
4. **Déployer** : Voir les sections Déploiement dans [ARCHITECTURE.md](./ARCHITECTURE.md)

### Pour les Utilisateurs Techniques

1. **Comprendre les fonctionnalités** : Voir [ARCHITECTURE.md](./ARCHITECTURE.md)
2. **Utiliser l'API** : Voir [API.md](./API.md)
3. **Exporter les données** : Voir les endpoints d'export dans [API.md](./API.md)

---

## 📊 Résumé des Composants

### Backend (Flask)

| Composant | Fichier | Description |
|-----------|--------|-------------|
| **Application** | `app/__init__.py` | Initialisation Flask, logging, gestion des erreurs |
| **Modèles** | `app/models.py` | Modèles de la base de données (SQLAlchemy) |
| **Routes** | `app/routes/` | Routes Flask (auth, main, admin, export) |
| **Utils** | `app/utils/` | Fonctions utilitaires et services |
| **Templates** | `app/templates/` | Templates Jinja2 |

### Modèles de Données

| Modèle | Table | Description |
|--------|-------|-------------|
| **User** | `user` | Utilisateurs de l'application |
| **Group** | `groups` | Groupes d'utilisateurs |
| **ShiftType** | `shift_types` | Types de shifts |
| **Shift** | `shift` | Shifts planifiés |
| **OnCall** | `on_call` | Astreintes planifiées |
| **Leave** | `leave` | Congés et absences |

### Services et Utilitaires

| Service | Fichier | Description |
|---------|--------|-------------|
| **Authentification** | `app/routes/auth.py` | Connexion, déconnexion, profil |
| **Administration** | `app/routes/admin.py` | Gestion des utilisateurs, groupes, types |
| **Planning** | `app/routes/main.py` | Gestion des shifts, astreintes, congés |
| **Export ICS** | `app/routes/export.py` | Export au format iCalendar |
| **Automatisation** | `app/utils/automation.py` | Tâches automatisées |
| **Export ICS** | `app/utils/ics_exporter.py` | Génération de fichiers ICS |
| **Décorateurs** | `app/utils/decorators.py` | Décorateurs personnalisés |
| **Helpers** | `app/utils/helpers.py` | Fonctions utilitaires |

---

## 🔧 Configuration Rapide

### Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)
- Git (optionnel)

### Installation

```bash
# Cloner le dépôt
git clone https://github.com/FoxOps/leviia-schedule.git
cd leviia-schedule

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt

# Configurer l'application (optionnel)
cp config.py config.local.py
# Modifier config.local.py selon vos besoins

# Initialiser la base de données
python run.py

# Démarrer l'application
python run.py
```

### Configuration de Base

```bash
# Clé secrète (générer une nouvelle pour la production)
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Environnement
export FLASK_ENV=development  # ou production

# Niveau de logging
export LOG_LEVEL=INFO

# Base de données (optionnel)
export DATABASE_URL=postgresql://user:password@localhost/leviia
```

### Accès à l'Application

- **URL** : `http://localhost:5000`
- **Identifiants par défaut** :
  - Email : `admin@leviia.local`
  - Mot de passe : `admin123`

---

## 📝 Historique des Changements

### Documentation

| Version | Date | Auteur | Changements |
|---------|------|--------|-------------|
| 1.0.0 | Juin 2026 | Vibe Code | Création initiale de la documentation complète |

### Application

Voir [ROADMAP.md](../ROADMAP.md) pour la feuille de route complète.

---

## 📞 Contact et Support

Pour toute question ou suggestion :

- **Issues** : Ouvrir une Issue sur [GitHub](https://github.com/FoxOps/leviia-schedule)
- **Discussions** : Ouvrir une Discussion sur [GitHub](https://github.com/FoxOps/leviia-schedule)
- **Documentation** : Consulter les documents dans le dossier `docs/`

---

## 🎯 Prochaines Étapes

1. **Lire la documentation** : Commencez par ce fichier et explorez les autres
2. **Configurer l'application** : Suivez les instructions d'installation
3. **Tester les fonctionnalités** : Connectez-vous et explorez l'interface
4. **Contribuer** : Forker le dépôt et soumettre des Pull Requests
5. **Signaler des bugs** : Ouvrir une Issue pour les problèmes rencontrés

---

> **⚠️ Note importante** : Cette documentation est évolutive et peut être mise à jour en fonction des changements dans l'application. Vérifiez régulièrement les mises à jour.

---

*Documentation générée pour Leviia Schedule - Résumé Complet*
