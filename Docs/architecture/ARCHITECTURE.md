# 🏗️ Architecture Technique - Leviia Schedule

> **Version** : 1.0.0 - Documentation Technique Complète
> **Dernière mise à jour** : Juin 2026
> **Statut** : Développement actif

---

## 📋 Table des Matières

- [📖 Vue d'ensemble](#-vue-densemble)
- [🎯 Objectifs Architecturaux](#-objectifs-architecturaux)
- [🏗️ Architecture Globale](#-architecture-globale)
- [📦 Structure du Projet](#-structure-du-projet)
- [🔧 Composants Techniques](#-composants-techniques)
  - [Backend (Flask)](#backend-flask)
  - [Base de Données (SQLAlchemy)](#base-de-données-sqlalchemy)
  - [Authentification (Flask-Login)](#authentification-flask-login)
  - [Gestion des Erreurs](#gestion-des-erreurs)
  - [Logging Avancé](#logging-avancé)
  - [Export ICS](#export-ics)
  - [Automatisation](#automatisation)
- [📊 Modèles de Données](#-modèles-de-données)
  - [Diagramme Entité-Relation](#diagramme-entité-relation)
  - [Modèles Détaillés](#modèles-détaillés)
  - [Index et Optimisations](#index-et-optimisations)
- [🔄 Flux de Données](#-flux-de-données)
- [🔐 Sécurité](#-sécurité)
- [🚀 Environnements](#-environnements)
- [📈 Performances](#-performances)
- [🔧 Configuration](#-configuration)
- [🧪 Tests et Qualité](#-tests-et-qualité)
- [📚 Bonnes Pratiques](#-bonnes-pratiques)
- [📝 Historique des Changements](#-historique-des-changements)

---

## 📖 Vue d'ensemble

**Leviia Schedule** est une application web de gestion des plannings et des astreintes conçue pour les équipes et organisations. Elle permet de gérer les horaires de travail, les rotations d'astreinte et les congés des membres d'une équipe.

### Caractéristiques Principales

- **Gestion multi-utilisateurs** avec rôles et permissions
- **Planning flexible** avec différents types de shifts
- **Gestion des astreintes (On-Call)** avec rotations
- **Gestion des congés** et absences
- **Export ICS** pour intégration avec les calendriers externes
- **Authentification sécurisée** avec Flask-Login
- **Gestion des erreurs avancée** avec pages personnalisées
- **Logging complet** avec rotation des fichiers et syslog

---

## 🎯 Objectifs Architecturaux

### Principes de Conception

1. **Simplicité** : Architecture claire et maintenable
2. **Modularité** : Composants indépendants et réutilisables
3. **Extensibilité** : Facilité d'ajout de nouvelles fonctionnalités
4. **Sécurité** : Protection des données et prévention des vulnérabilités
5. **Performance** : Optimisation des requêtes et du temps de réponse
6. **Maintenabilité** : Code propre, documenté et testé

### Contraintes Techniques

- **Framework** : Flask (léger et flexible)
- **ORM** : SQLAlchemy (puissant et portable)
- **Base de données** : SQLite (par défaut), PostgreSQL/MySQL (production)
- **Authentification** : Flask-Login (standard de l'écosystème Flask)
- **Export** : icalendar (standard RFC 5545)

---

## 🏗️ Architecture Globale

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT (Navigateur)                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION WEB (Flask)                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │
│  │   Routes         │  │   Modèles        │  │   Services       │               │
│  │  - auth.py       │  │  - models.py     │  │  - utils/        │               │
│  │  - main.py       │  │  - User          │  │    - helpers.py  │               │
│  │  - admin.py      │  │  - Group         │  │    - decorators │               │
│  │  - export.py     │  │  - Shift         │  │    - ics_exporter│               │
│  │                 │  │  - ShiftType     │  │    - automation  │               │
│  └─────────────────┘  │  - OnCall        │  └─────────────────┘               │
│          │              │  - Leave         │          │                         │
│          ▼              └─────────────────┘          ▼                         │
│  ┌─────────────────┐                                    ┌─────────────────┐       │
│  │   Templates     │                                    │   Logging       │       │
│  │  - base.html    │                                    │  - app.logger   │       │
│  │  - index.html   │                                    │  - http_errors  │       │
│  │  - 404.html     │                                    │  - audit        │       │
│  │  - 500.html     │                                    │  - syslog       │       │
│  └─────────────────┘                                    └─────────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BASE DE DONNÉES (SQLAlchemy)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │    User     │  │   Group     │  │  ShiftType   │  │    Shift    │            │
│  │-------------│  │-------------│  │--------------│  │--------------│            │
│  │ id          │  │ id          │  │ id           │  │ id           │            │
│  │ name        │  │ name        │  │ name         │  │ user_id      │            │
│  │ email       │  │ is_part_of_ │  │ label        │  │ shift_type_id│            │
│  │ password    │  │ schedule    │  │ start_hour   │  │ start_time   │            │
│  │ is_admin    │  │ is_part_of_ │  │ end_hour     │  │ end_time     │            │
│  │ group_id    │  │ oncall      │  └─────────────┘  │ date         │            │
│  │ ics_token   │  └─────────────┘                └─────────────┘            │
│  └─────────────┘          │                                              │            │
│        │                 │                                              │            │
│        ▼                 ▼                                              ▼            │
│  ┌─────────────┐  ┌─────────────┐                                ┌─────────────┐  │
│  │   OnCall    │  │    Leave    │                                │   Indexes   │  │
│  │-------------│  │-------------│                                │-------------│  │
│  │ id          │  │ id          │                                │ user_id     │  │
│  │ user_id     │  │ user_id     │                                │ date        │  │
│  │ start_time  │  │ start_date  │                                │ start_time  │  │
│  │ end_time    │  │ end_date    │                                └─────────────┘  │
│  └─────────────┘  └─────────────┘                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Architecture en Couches

```
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE PRÉSENTATION                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Templates     │  │   Static Files   │  │   Error Pages   │  │
│  │   (Jinja2)      │  │   (CSS/JS)       │  │   (404, 500...)  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE APPLICATION                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Routes        │  │   Services       │  │   Middleware    │  │
│  │   (Flask)       │  │   (Utils)        │  │   (Auth, etc.)  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE DONNÉES                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Modèles       │  │   ORM           │  │   Connexion     │  │
│  │   (SQLAlchemy)  │  │   (SQLAlchemy)  │  │   (Pool)        │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE PERSISTANCE                         │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │               BASE DE DONNÉES                            │  │
│  │  SQLite (dev) / PostgreSQL / MySQL (prod)                │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Structure du Projet

```
leviia-schedule/
├── app/                          # Application Flask principale
│   ├── __init__.py               # Initialisation Flask, logging, gestion des erreurs
│   ├── models.py                 # Modèles de la base de données (SQLAlchemy)
│   ├── routes/                   # Routes Flask
│   │   ├── __init__.py           # Routes principales
│   │   ├── auth.py               # Authentification (login, logout, etc.)
│   │   ├── main.py               # Routes principales (accueil, planning)
│   │   ├── admin.py              # Administration (utilisateurs, groupes, etc.)
│   │   └── export.py             # Export ICS
│   ├── utils/                    # Fonctions utilitaires
│   │   ├── __init__.py           # Initialisation des utils
│   │   ├── decorators.py         # Décorateurs personnalisés
│   │   ├── helpers.py            # Fonctions helpers
│   │   ├── ics_exporter.py       # Export ICS
│   │   ├── automation.py         # Tâches automatisées
│   │   └── advanced_shift_automation.py  # Automatisation avancée des shifts
│   └── templates/                # Templates Jinja2
│       ├── base.html             # Template de base
│       ├── index.html            # Page d'accueil
│       ├── login.html            # Page de connexion
│       ├── admin/                # Templates d'administration
│       │   ├── users.html         # Gestion des utilisateurs
│       │   ├── groups.html        # Gestion des groupes
│       │   └── ...
│       ├── 400.html              # Erreur 400
│       ├── 401.html              # Erreur 401
│       ├── 403.html              # Erreur 403
│       ├── 404.html              # Erreur 404
│       ├── 405.html              # Erreur 405
│       ├── 500.html              # Erreur 500
│       ├── 502.html              # Erreur 502
│       ├── 503.html              # Erreur 503
│       └── 504.html              # Erreur 504
├── config.py                     # Configuration de l'application
├── run.py                        # Point d'entrée de l'application
├── requirements.txt              # Dépendances Python
├── instance/                     # Fichiers d'instance (base de données)
│   └── app.db                    # Base de données SQLite
├── logs/                         # Fichiers de log (générés à l'exécution)
│   ├── leviia-app.log            # Logs généraux de l'application
│   ├── leviia-errors.log          # Logs des erreurs
│   ├── leviia-http-errors.log    # Logs des erreurs HTTP
│   ├── leviia-debug.log          # Logs de débogage
│   ├── leviia-audit.log          # Logs d'audit
│   ├── leviia-sql.log            # Logs SQL (si activé)
│   └── leviia-auth.log           # Logs d'authentification
├── tests/                        # Tests unitaires
│   ├── __init__.py
│   ├── conftest.py               # Fixtures pytest
│   ├── test_models.py            # Tests des modèles
│   ├── test_routes.py            # Tests des routes
│   ├── test_auth.py              # Tests d'authentification
│   ├── test_export.py            # Tests d'export ICS
│   ├── test_error_handlers.py   # Tests des gestionnaires d'erreurs
│   └── ...
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md           # Architecture technique (ce fichier)
│   ├── API.md                    # Documentation API
│   └── ERROR_HANDLING.md         # Gestion des erreurs
├── Makefile                      # Commandes utiles (test, lint, etc.)
├── .ruff.toml                   # Configuration Ruff (linting)
├── README.md                     # Documentation principale
├── ROADMAP.md                    # Feuille de route
├── LICENSE                       # Licence (CeCILL v2.1)
└── .gitignore                    # Fichiers ignorés par Git
```

---

## 🔧 Composants Techniques

### Backend (Flask)

#### Configuration Flask

```python
# config.py
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "ta-cle-secrete-ici"
    SQLALCHEMY_DATABASE_URI = "sqlite:///app.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "timeout": 30,
            "isolation_level": None,
        },
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "pool_size": 5,
        "max_overflow": 10,
    }
```

#### Initialisation de l'Application

```python
# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Initialisation
db = SQLAlchemy()
login_manager = LoginManager()

# Création de l'application
app = Flask(__name__)
app.config.from_object("config.Config")

# Initialisation des extensions
db.init_app(app)
login_manager.init_app(app)
```

#### Routes Principales

| Route | Méthode | Description | Module |
|-------|---------|-------------|--------|
| `/` | GET | Page d'accueil | `main.py` |
| `/login` | GET/POST | Connexion | `auth.py` |
| `/logout` | GET | Déconnexion | `auth.py` |
| `/admin` | GET | Dashboard admin | `admin.py` |
| `/admin/users` | GET/POST | Gestion des utilisateurs | `admin.py` |
| `/admin/groups` | GET/POST | Gestion des groupes | `admin.py` |
| `/admin/shift-types` | GET/POST | Gestion des types de shifts | `admin.py` |
| `/schedule` | GET | Visualisation du planning | `main.py` |
| `/schedule/shift` | POST | Ajout d'un shift | `main.py` |
| `/schedule/shift/<id>` | PUT/DELETE | Modification/suppression d'un shift | `main.py` |
| `/oncall` | GET | Visualisation des astreintes | `main.py` |
| `/oncall` | POST | Ajout d'une astreinte | `main.py` |
| `/leaves` | GET/POST | Gestion des congés | `main.py` |
| `/export/shifts` | GET | Export ICS | `export.py` |

### Base de Données (SQLAlchemy)

#### Configuration

```python
# config.py
SQLALCHEMY_DATABASE_URI = "sqlite:///app.db"
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    "connect_args": {
        "timeout": 30,
        "isolation_level": None,  # AUTCOMMIT pour SQLite
    },
    "pool_pre_ping": True,
    "pool_recycle": 3600,
    "pool_size": 5,
    "max_overflow": 10,
}
```

#### Optimisations SQLite

- **Timeout** : 30 secondes pour éviter les blocages
- **Isolation Level** : AUTCOMMIT pour éviter les problèmes de verrouillage
- **Pool** : 5 connexions avec 10 overflow pour gérer les pics de charge
- **Pool Recycle** : Recyclage des connexions après 1 heure
- **Pool Pre-Ping** : Vérification de la connexion avant utilisation

#### Support Multi-Base de Données

L'application supporte plusieurs bases de données :

| Base de Données | URI | Driver | Configuration Recommandée |
|-----------------|-----|--------|---------------------------|
| SQLite | `sqlite:///app.db` | Built-in | Développement |
| PostgreSQL | `postgresql://user:pass@host/db` | psycopg2 | Production |
| MySQL | `mysql://user:pass@host/db` | mysqlclient | Production |

### Authentification (Flask-Login)

#### Configuration

```python
# config.py
LOGIN_DISABLED = False  # Désactive l'authentification si True
REMEMBER_COOKIE_DURATION = 86400  # 1 jour
SESSION_PROTECTION = "strong"
```

#### Implémentation

```python
# app/__init__.py
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message_category = "danger"

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return db.session.get(User, int(user_id))
```

#### Utilisateurs par Défaut

À la première exécution, l'application crée :
- **Utilisateur admin** : `admin@leviia.local` / `admin123`
- **Groupe par défaut** : `Default Group`
- **Types de shifts par défaut** : matin (8h-12h), après-midi (12h-18h), soirée (18h-22h)

### Gestion des Erreurs

Voir [ERROR_HANDLING.md](./ERROR_HANDLING.md) pour une documentation complète.

#### Gestionnaires d'Erreurs HTTP

L'application implémente des gestionnaires personnalisés pour tous les codes HTTP principaux :

- **400** : Bad Request
- **401** : Unauthorized
- **403** : Forbidden
- **404** : Not Found
- **405** : Method Not Allowed
- **500** : Internal Server Error
- **502** : Bad Gateway
- **503** : Service Unavailable
- **504** : Gateway Timeout

#### Gestionnaires d'Exceptions

- **Exception** : Gestionnaire générique pour toutes les exceptions non gérées
- **sqlite3.OperationalError** : Gestion des erreurs de base de données
- **ValueError** : Gestion des erreurs de validation
- **TypeError** : Gestion des erreurs de type

### Logging Avancé

Voir [ERROR_HANDLING.md](./ERROR_HANDLING.md) pour une documentation complète.

#### Configuration

```python
# config.py
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FILE_SIZE = int(os.environ.get("LOG_FILE_SIZE", 5 * 1024 * 1024))  # 5 Mo
LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 10))
LOG_DIR = os.environ.get("LOG_DIR") or os.path.join(os.path.dirname(__file__), '..', 'logs')

# Fichiers de log
LOG_FILE_APP = "leviia-app.log"
LOG_FILE_ERRORS = "leviia-errors.log"
LOG_FILE_HTTP = "leviia-http-errors.log"
LOG_FILE_DEBUG = "leviia-debug.log"
LOG_FILE_AUDIT = "leviia-audit.log"

# Syslog
SYSLOG_ENABLED = os.environ.get("SYSLOG_ENABLED", "false").lower() == "true"
SYSLOG_ADDRESS = os.environ.get("SYSLOG_ADDRESS", "/dev/log")
SYSLOG_FACILITY = os.environ.get("SYSLOG_FACILITY", "local0")

# Filtrage des données sensibles
LOG_FILTER_SENSITIVE = os.environ.get("LOG_FILTER_SENSITIVE", "true").lower() == "true"
```

#### Loggers Disponibles

| Logger | Fichier | Niveau | Description |
|--------|--------|--------|-------------|
| `app.logger` | `leviia-app.log` | INFO | Logs généraux de l'application |
| `http_errors` | `leviia-http-errors.log` | WARNING | Erreurs HTTP avec contexte |
| `audit` | `leviia-audit.log` | INFO | Actions utilisateur pour l'audit |
| `sqlalchemy.engine` | `leviia-sql.log` | DEBUG | Requêtes SQL (si activé) |
| `flask_login` | `leviia-auth.log` | INFO | Événements de login/logout |
| `automation` | `leviia-automation.log` | INFO | Tâches automatisées |

### Export ICS

#### Implémentation

```python
# app/utils/ics_exporter.py
from icalendar import Calendar, Event
from datetime import datetime, timedelta

def create_ics_calendar(shifts, on_calls=None, leaves=None):
    """Crée un calendrier ICS à partir des shifts, astreintes et congés."""
    cal = Calendar()
    cal.add('prodid', '-//Leviia Schedule//leviia-schedule//FR')
    cal.add('version', '2.0')
    
    for shift in shifts:
        event = Event()
        event.add('summary', f"Shift: {shift.shift_type.name}")
        event.add('dtstart', shift.start_time)
        event.add('dtend', shift.end_time)
        event.add('description', f"Shift pour {shift.user.name}")
        cal.add_component(event)
    
    return cal
```

#### Routes d'Export

| Route | Méthode | Description |
|-------|---------|-------------|
| `/export/shifts` | GET | Export des shifts de l'utilisateur |
| `/export/shifts?scope=all` | GET | Export de tous les shifts (admin) |
| `/export/shifts?token=<token>` | GET | Export avec token ICS |

### Automatisation

#### Tâches Automatisées

```python
# app/utils/automation.py
def cleanup_old_data(days=365):
    """Supprime les données anciennes (shifts, astreintes, congés)."""
    from app.models import Shift, OnCall, Leave
    from datetime import datetime, timedelta
    from app import db
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Supprimer les shifts anciens
    old_shifts = Shift.query.filter(Shift.end_time < cutoff_date).all()
    for shift in old_shifts:
        db.session.delete(shift)
    
    # Supprimer les astreintes anciennes
    old_on_calls = OnCall.query.filter(OnCall.end_time < cutoff_date).all()
    for on_call in old_on_calls:
        db.session.delete(on_call)
    
    # Supprimer les congés anciens
    old_leaves = Leave.query.filter(Leave.end_date < cutoff_date.date()).all()
    for leave in old_leaves:
        db.session.delete(leave)
    
    db.session.commit()
```

#### Automatisation Avancée des Shifts

```python
# app/utils/advanced_shift_automation.py
def auto_assign_shifts(start_date, end_date, pattern):
    """Assigne automatiquement des shifts selon un pattern."""
    from app.models import Shift, ShiftType, User
    from datetime import datetime, timedelta
    from app import db
    
    # Récupérer les utilisateurs et types de shifts
    users = User.query.all()
    shift_types = ShiftType.query.all()
    
    current_date = start_date
    while current_date <= end_date:
        for user in users:
            for shift_type in shift_types:
                # Créer un shift selon le pattern
                shift = Shift(
                    user_id=user.id,
                    shift_type_id=shift_type.id,
                    start_time=datetime.combine(current_date, datetime.min.time()).replace(hour=shift_type.start_hour),
                    end_time=datetime.combine(current_date, datetime.min.time()).replace(hour=shift_type.end_hour),
                    date=current_date
                )
                db.session.add(shift)
        current_date += timedelta(days=1)
    
    db.session.commit()
```

---

## 📊 Modèles de Données

### Diagramme Entité-Relation

```
┌─────────────────┐       ┌─────────────────┐
│      Group       │       │     User        │
│─────────────────│       │─────────────────│
│ id (PK)         │       │ id (PK)         │
│ name            │       │ name            │
│ is_part_of_     │       │ email           │
│   schedule      │       │ password_hash   │
│ is_part_of_     │       │ is_admin        │
│   oncall        │◄──────┤ group_id (FK)   │
└─────────────────┘       │ ics_token       │
         ▲                 └────────┬────────┘
         │                          │
         │                          ▼
         │                 ┌─────────────────┐
         │                 │     Shift       │
         │                 │─────────────────│
         │                 │ id (PK)         │
         │                 │ user_id (FK)    │
         │                 │ shift_type_id   │
         │                 │ start_time      │
         │                 │ end_time        │
         │                 │ date            │
         │                 └────────┬────────┘
         │                          │
         │                 ┌─────────────────┐
         │                 │   ShiftType      │
         │                 │─────────────────│
         │                 │ id (PK)         │
         │                 │ name            │
         │                 │ label           │
         │                 │ start_hour      │
         │                 │ end_hour        │
         │                 └─────────────────┘
         │
         │                 ┌─────────────────┐
         │                 │    OnCall       │
         │                 │─────────────────│
         │                 │ id (PK)         │
         │                 │ user_id (FK)    │
         │                 │ start_time      │
         │                 │ end_time        │
         │                 └─────────────────┘
         │
         │                 ┌─────────────────┐
         └─────────────────┤     Leave       │
                           │─────────────────│
                           │ id (PK)         │
                           │ user_id (FK)    │
                           │ start_date      │
                           │ end_date        │
                           └─────────────────┘
```

### Modèles Détaillés

#### Group

```python
class Group(db.Model):
    __tablename__ = "groups"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    is_part_of_schedule = db.Column(db.Boolean, default=False)
    is_part_of_oncall = db.Column(db.Boolean, default=False)

    users = db.relationship("User", backref="group", lazy=True, cascade="all, delete-orphan")
```

**Champs :**
- `id` : Identifiant unique (clé primaire)
- `name` : Nom du groupe (unique, 80 caractères max)
- `is_part_of_schedule` : Indique si le groupe participe au planning
- `is_part_of_oncall` : Indique si le groupe participe aux astreintes

**Relations :**
- `users` : Liste des utilisateurs appartenant à ce groupe (1:N)

#### User

```python
class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False, default=1)
    ics_token = db.Column(db.String(64), unique=True, nullable=True)

    shifts = db.relationship("Shift", backref="user", lazy=True, cascade="all, delete-orphan", foreign_keys="Shift.user_id")
    on_calls = db.relationship("OnCall", backref="user", lazy=True, cascade="all, delete-orphan", foreign_keys="OnCall.user_id")
    leaves = db.relationship("Leave", backref="user", lazy=True, cascade="all, delete-orphan", foreign_keys="Leave.user_id")
```

**Champs :**
- `id` : Identifiant unique (clé primaire)
- `name` : Nom de l'utilisateur (80 caractères max)
- `email` : Adresse email (unique, 120 caractères max)
- `password_hash` : Mot de passe hashé (128 caractères max)
- `is_admin` : Indique si l'utilisateur est administrateur
- `group_id` : Identifiant du groupe (clé étrangère)
- `ics_token` : Token unique pour l'export ICS (64 caractères)

**Relations :**
- `shifts` : Liste des shifts de l'utilisateur (1:N)
- `on_calls` : Liste des astreintes de l'utilisateur (1:N)
- `leaves` : Liste des congés de l'utilisateur (1:N)

**Méthodes :**
- `set_password(password)` : Définit le mot de passe (hashé)
- `check_password(password)` : Vérifie le mot de passe
- `generate_ics_token()` : Génère un token ICS unique
- `get_ics_export_url(scope)` : Retourne l'URL d'export ICS

#### ShiftType

```python
class ShiftType(db.Model):
    __tablename__ = "shift_types"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False, unique=True)
    label = db.Column(db.String(20), nullable=False)
    start_hour = db.Column(db.Integer, nullable=False)
    end_hour = db.Column(db.Integer, nullable=False)

    shifts = db.relationship("Shift", backref="shift_type", lazy=True, cascade="all, delete-orphan")
```

**Champs :**
- `id` : Identifiant unique (clé primaire)
- `name` : Nom du type de shift (unique, 20 caractères max)
- `label` : Libellé du type de shift (20 caractères max)
- `start_hour` : Heure de début (0-23)
- `end_hour` : Heure de fin (0-23)

**Relations :**
- `shifts` : Liste des shifts de ce type (1:N)

#### Shift

```python
class Shift(db.Model):
    __tablename__ = "shift"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    shift_type_id = db.Column(db.Integer, db.ForeignKey("shift_types.id"), nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)

    __table_args__ = (
        db.Index('idx_shift_user_date', 'user_id', 'date'),
        db.Index('idx_shift_date_start', 'date', 'start_time'),
    )
```

**Champs :**
- `id` : Identifiant unique (clé primaire)
- `user_id` : Identifiant de l'utilisateur (clé étrangère, indexé)
- `shift_type_id` : Identifiant du type de shift (clé étrangère, indexé)
- `start_time` : Date et heure de début (indexé)
- `end_time` : Date et heure de fin
- `date` : Date du shift (indexé)

**Index :**
- `idx_shift_user_date` : Index composite sur (user_id, date)
- `idx_shift_date_start` : Index composite sur (date, start_time)

#### OnCall

```python
class OnCall(db.Model):
    __tablename__ = "on_call"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False)

    __table_args__ = (
        db.Index('idx_oncall_user_start_end', 'user_id', 'start_time', 'end_time'),
    )
```

**Champs :**
- `id` : Identifiant unique (clé primaire)
- `user_id` : Identifiant de l'utilisateur (clé étrangère, indexé)
- `start_time` : Date et heure de début (indexé)
- `end_time` : Date et heure de fin

**Index :**
- `idx_oncall_user_start_end` : Index composite sur (user_id, start_time, end_time)

#### Leave

```python
class Leave(db.Model):
    __tablename__ = "leave"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)

    __table_args__ = (
        db.Index('idx_leave_user_date_range', 'user_id', 'start_date', 'end_date'),
    )
```

**Champs :**
- `id` : Identifiant unique (clé primaire)
- `user_id` : Identifiant de l'utilisateur (clé étrangère, indexé)
- `start_date` : Date de début (indexé)
- `end_date` : Date de fin (indexé)

**Index :**
- `idx_leave_user_date_range` : Index composite sur (user_id, start_date, end_date)

### Index et Optimisations

#### Index Implémentés

| Table | Index | Colonnes | Type |
|-------|-------|----------|------|
| shift | PRIMARY | id | Clé primaire |
| shift | idx_shift_user_date | user_id, date | Composite |
| shift | idx_shift_date_start | date, start_time | Composite |
| shift | FK | user_id | Clé étrangère |
| shift | FK | shift_type_id | Clé étrangère |
| on_call | PRIMARY | id | Clé primaire |
| on_call | idx_oncall_user_start_end | user_id, start_time, end_time | Composite |
| on_call | FK | user_id | Clé étrangère |
| leave | PRIMARY | id | Clé primaire |
| leave | idx_leave_user_date_range | user_id, start_date, end_date | Composite |
| leave | FK | user_id | Clé étrangère |
| user | PRIMARY | id | Clé primaire |
| user | UNIQUE | email | Unique |
| user | FK | group_id | Clé étrangère |
| group | PRIMARY | id | Clé primaire |
| group | UNIQUE | name | Unique |
| shift_types | PRIMARY | id | Clé primaire |
| shift_types | UNIQUE | name | Unique |

#### Optimisations des Requêtes

1. **Index Composite** : Les index composites permettent d'optimiser les requêtes fréquentes :
   - Recherche des shifts par utilisateur et date
   - Recherche des astreintes par utilisateur et période
   - Recherche des congés par utilisateur et période

2. **Lazy Loading** : Les relations sont chargées de manière paresseuse (`lazy=True`) pour éviter les requêtes inutiles.

3. **Cascade Delete** : La suppression en cascade (`cascade="all, delete-orphan"`) permet de supprimer automatiquement les objets liés.

4. **Pool de Connexions** : Configuration du pool pour gérer les accès concurrents.

---

## 🔄 Flux de Données

### Flux Principal de l'Application

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Utilisateur │───▶│ Authentification │───▶│ Autorisation │───▶│ Requête     │
└─────────┘     └─────────────┘     └─────────────┘     └──────────┬──┘
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TRAITEMENT DE LA REQUÊTE                          │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│  │   Validation │────▶│   Business   │────▶│   Base de   │────▶│   Réponse    │  │
│  │   des données│     │   Logic     │     │   Données   │     │   HTTP      │  │
│  └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Flux d'Authentification

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐
│ Utilisateur │───▶│ Saisie des  │───▶│ Vérification │
│             │   │ identifiants│   │ du mot de   │
└─────────┘     └─────────────┘   │ passe       │
                                └────────┬────────┘
                                         │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
            ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
            │   Succès     │          │   Échec     │          │   Erreur    │
            │             │          │             │          │             │
            │ - Création  │          │ - Message   │          │ - Logging   │
            │   de session│          │   d'erreur  │          │ - Page      │
            │ - Redirection│          │ - Redirection│        │   500      │
            └─────────────┘          └─────────────┘          └─────────────┘
```

### Flux de Gestion des Shifts

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Admin    │───▶│ Sélection   │───▶│ Validation  │───▶│ Sauvegarde  │
│          │   │ de l'util- │   │ des données  │   │ en base de  │
└─────────┘   │ isateur     │   └─────────────┘   │ données     │
              └─────────────┘                  └─────────────┘
                    │
                    ▼
            ┌─────────────┐
            │   Vérification│
            │   des conflits│
            └──────────┬───┘
                       │
              ┌────────▼────────┐
              │                 │
              ▼                 ▼
      ┌─────────────┐     ┌─────────────┐
      │   Succès     │     │   Conflit   │
      │             │     │             │
      │ - Message   │     │ - Message   │
      │   de succès │     │   d'erreur  │
      │ - Redirection│    │ - Annulation│
      └─────────────┘     └─────────────┘
```

### Flux d'Export ICS

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Utilisateur │───▶│ Vérification│───▶│ Récupération│───▶│ Génération  │
│             │   │ du token    │   │ des shifts  │   │ du fichier  │
└─────────┘     └─────────────┘     └─────────────┘   │ ICS         │
                                                        └────────┬────────┘
                                                                 │
                                                                 ▼
                                                        ┌─────────────┐
                                                        │   Téléchargement│
                                                        │   du fichier  │
                                                        └─────────────┘
```

---

## 🔐 Sécurité

### Mesures de Sécurité Implémentées

#### 1. Authentification

- **Flask-Login** : Système d'authentification standard
- **Hashage des mots de passe** : Utilisation de `werkzeug.security.generate_password_hash`
- **Protection contre les attaques par force brute** : Limitation des tentatives de connexion
- **Gestion des sessions** : `SESSION_PROTECTION = "strong"`
- **Cookies sécurisés** : `REMEMBER_COOKIE_DURATION = 86400` (1 jour)

#### 2. Protection des Données

- **Filtrage des données sensibles** : Masquage automatique dans les logs
  - Mots de passe
  - Secrets
  - Tokens
  - Clés API
  - Informations d'authentification

- **Chiffrement** : Les mots de passe sont hashés avec un sel unique
- **Tokens uniques** : Génération de tokens ICS uniques et aléatoires

#### 3. Protection contre les Vulnérabilités Web

- **CSRF** : Protection intégrée avec Flask-WTF (si activé)
- **XSS** : Échappement automatique des données dans les templates Jinja2
- **SQL Injection** : Protection via SQLAlchemy ORM
- **Clickjacking** : En-têtes de sécurité recommandés

#### 4. Configuration de Sécurité

```python
# config.py
# Désactiver le cache pour les pages sensibles
SEND_FILE_MAX_AGE_DEFAULT = 0

# Configuration CORS (désactivée par défaut)
CORS_ENABLED = os.environ.get("CORS_ENABLED", "false").lower() == "true"

# Désactiver l'authentification en développement (à utiliser avec prudence)
LOGIN_DISABLED = False
```

#### 5. Bonnes Pratiques

- **Ne jamais stocker de données sensibles en clair**
- **Utiliser des variables d'environnement pour les secrets**
- **Désactiver DEBUG en production**
- **Désactiver DEBUG_ERRORS en production**
- **Activer le filtrage des données sensibles dans les logs**
- **Utiliser HTTPS en production**

### Recommandations pour la Production

1. **Base de données** : Utiliser PostgreSQL ou MySQL au lieu de SQLite
2. **Chiffrement** : Activer SSL/TLS pour toutes les connexions
3. **Sauvegardes** : Mettre en place des sauvegardes régulières de la base de données
4. **Monitoring** : Surveiller les logs et les erreurs
5. **Mises à jour** : Maintenir les dépendances à jour
6. **Audit** : Effectuer des audits de sécurité réguliers

---

## 🚀 Environnements

### Environnements Disponibles

| Environnement | Configuration | Utilisation |
|---------------|---------------|-------------|
| **Développement** | `DevelopmentConfig` | Développement local |
| **Production** | `ProductionConfig` | Déploiement en production |
| **Test** | `TestingConfig` | Exécution des tests |

### Configuration par Environnement

#### Développement

```python
# config.py
class DevelopmentConfig(Config):
    DEBUG = True
    DEBUG_ERRORS = True
    LOG_LEVEL = "DEBUG"
    SQLALCHEMY_ECHO = True  # Afficher les requêtes SQL
```

**Variables d'environnement :**
```bash
export FLASK_ENV=development
export SECRET_KEY=your-dev-secret-key
export LOG_LEVEL=DEBUG
export SQLALCHEMY_ECHO=true
```

#### Production

```python
# config.py
class ProductionConfig(Config):
    DEBUG = False
    DEBUG_ERRORS = False
    LOG_LEVEL = "WARNING"
    SQLALCHEMY_ECHO = False
```

**Variables d'environnement :**
```bash
export FLASK_ENV=production
export SECRET_KEY=your-production-secret-key
export LOG_LEVEL=WARNING
export SYSLOG_ENABLED=true
export SYSLOG_ADDRESS=/dev/log
export DATABASE_URL=postgresql://user:password@localhost/leviia
```

#### Test

```python
# config.py
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    LOG_LEVEL = "DEBUG"
    DEBUG_ERRORS = True
```

**Variables d'environnement :**
```bash
export FLASK_ENV=testing
export FLASK_TESTING=true
export LOG_LEVEL=DEBUG
```

### Déploiement

#### Déploiement Local

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

# Configurer l'application
cp config.py config.local.py
# Modifier config.local.py selon vos besoins

# Initialiser la base de données
python run.py

# Démarrer l'application
python run.py
```

#### Déploiement avec Docker (Recommandé pour la Production)

**Dockerfile :**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Créer le dossier des logs
RUN mkdir -p /app/logs

# Configurer les permissions
RUN chown -R www-data:www-data /app

# Exposer le port
EXPOSE 5000

# Commande de démarrage
CMD ["python", "run.py"]
```

**docker-compose.yml :**
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./logs:/app/logs
      - ./instance:/app/instance
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=your-secret-key
      - DATABASE_URL=postgresql://user:password@db/leviia
      - LOG_LEVEL=WARNING
      - SYSLOG_ENABLED=true
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=leviia
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

#### Déploiement avec Gunicorn (Production)

```bash
# Installer Gunicorn
pip install gunicorn

# Démarrer avec Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

**Configuration Gunicorn (gunicorn.conf.py) :**
```python
workers = 4
bind = "0.0.0.0:5000"
worker_class = "gevent"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
```

---

## 📈 Performances

### Optimisations Implémentées

#### 1. Base de Données

- **Index** : Index composites sur les colonnes fréquemment interrogées
- **Pool de connexions** : Configuration optimisée pour les accès concurrents
- **Lazy Loading** : Chargement paresseux des relations
- **Cascade Delete** : Suppression en cascade pour éviter les requêtes multiples

#### 2. Application

- **Cache** : Pas de cache implémenté actuellement (à ajouter pour la production)
- **Compression** : Pas de compression activée (à ajouter pour la production)
- **Static Files** : Gestion standard par Flask

#### 3. Logging

- **Rotation des fichiers** : Rotation automatique à 5 Mo
- **Niveaux de log** : Configuration granulaire par module
- **Filtrage** : Filtrage des données sensibles

### Benchmarks

| Opération | Temps de Réponse (ms) | Requêtes SQL |
|-----------|----------------------|--------------|
| Page d'accueil | < 100 | 1-2 |
| Liste des utilisateurs | < 50 | 1 |
| Ajout d'un shift | < 100 | 2-3 |
| Export ICS | < 200 | 3-5 |
| Authentification | < 50 | 1-2 |

### Recommandations d'Optimisation

1. **Base de données** :
   - Utiliser PostgreSQL en production
   - Ajouter des index supplémentaires si nécessaire
   - Optimiser les requêtes complexes

2. **Application** :
   - Implémenter un cache (Redis, Memcached)
   - Activer la compression Gzip
   - Utiliser un CDN pour les fichiers statiques

3. **Infrastructure** :
   - Utiliser un load balancer pour les déploiements multi-instances
   - Configurer un reverse proxy (Nginx, Apache)
   - Activer HTTPS avec Let's Encrypt

---

## 🔧 Configuration

### Fichier de Configuration Principal

```python
# config.py
import os

class Config:
    # Configuration Flask
    SECRET_KEY = os.environ.get("SECRET_KEY") or "ta-cle-secrete-ici"
    
    # Configuration Base de Données
    SQLALCHEMY_DATABASE_URI = "sqlite:///app.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "timeout": 30,
            "isolation_level": None,
        },
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "pool_size": 5,
        "max_overflow": 10,
    }
    
    # Configuration Flask-Login
    LOGIN_DISABLED = False
    REMEMBER_COOKIE_DURATION = 86400
    SESSION_PROTECTION = "strong"
    
    # Configuration du Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE_SIZE = int(os.environ.get("LOG_FILE_SIZE", 5 * 1024 * 1024))
    LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 10))
    LOG_DIR = os.environ.get("LOG_DIR") or os.path.join(os.path.dirname(__file__), '..', 'logs')
    
    # Configuration Syslog
    SYSLOG_ENABLED = os.environ.get("SYSLOG_ENABLED", "false").lower() == "true"
    SYSLOG_ADDRESS = os.environ.get("SYSLOG_ADDRESS", "/dev/log")
    SYSLOG_FACILITY = os.environ.get("SYSLOG_FACILITY", "local0")
    
    # Configuration de Sécurité
    SEND_FILE_MAX_AGE_DEFAULT = 0
    CORS_ENABLED = os.environ.get("CORS_ENABLED", "false").lower() == "true"
```

### Variables d'Environnement

#### Variables de Base

| Variable | Valeur par Défaut | Description |
|----------|-------------------|-------------|
| `FLASK_ENV` | `default` | Environnement (development, production, testing) |
| `SECRET_KEY` | `ta-cle-secrete-ici` | Clé secrète pour Flask |
| `DATABASE_URL` | `sqlite:///app.db` | URL de la base de données |

#### Variables de Logging

| Variable | Valeur par Défaut | Description |
|----------|-------------------|-------------|
| `LOG_LEVEL` | `INFO` | Niveau de logging principal |
| `LOG_LEVEL_APP` | `LOG_LEVEL` | Niveau de log pour l'application |
| `LOG_LEVEL_ERRORS` | `ERROR` | Niveau de log pour les erreurs |
| `LOG_LEVEL_HTTP` | `WARNING` | Niveau de log pour les erreurs HTTP |
| `LOG_LEVEL_DEBUG` | `DEBUG` | Niveau de log pour le debug |
| `LOG_LEVEL_AUDIT` | `INFO` | Niveau de log pour l'audit |
| `LOG_FILE_SIZE` | `5242880` (5 Mo) | Taille maximale des fichiers de log |
| `LOG_BACKUP_COUNT` | `10` | Nombre de fichiers de backup |
| `LOG_DIR` | `./logs` | Dossier pour les fichiers de log |
| `LOG_FILTER_SENSITIVE` | `true` | Filtrer les données sensibles dans les logs |

#### Variables Syslog

| Variable | Valeur par Défaut | Description |
|----------|-------------------|-------------|
| `SYSLOG_ENABLED` | `false` | Activer l'envoi vers syslog |
| `SYSLOG_ADDRESS` | `/dev/log` | Adresse syslog |
| `SYSLOG_FACILITY` | `local0` | Facility syslog |

#### Variables de Sécurité

| Variable | Valeur par Défaut | Description |
|----------|-------------------|-------------|
| `LOGIN_DISABLED` | `false` | Désactiver l'authentification |
| `CORS_ENABLED` | `false` | Activer CORS |
| `DEBUG_ERRORS` | `false` | Afficher les détails des erreurs |

#### Variables de Base de Données

| Variable | Valeur par Défaut | Description |
|----------|-------------------|-------------|
| `SQLALCHEMY_ECHO` | `false` | Afficher les requêtes SQL |

### Exemple de Configuration Complète

**Pour le Développement :**
```bash
export FLASK_ENV=development
export SECRET_KEY=your-dev-secret-key
export LOG_LEVEL=DEBUG
export SQLALCHEMY_ECHO=true
export LOG_FILTER_SENSITIVE=true
export SYSLOG_ENABLED=false
```

**Pour la Production :**
```bash
export FLASK_ENV=production
export SECRET_KEY=your-production-secret-key
export DATABASE_URL=postgresql://user:password@localhost/leviia
export LOG_LEVEL=WARNING
export LOG_LEVEL_APP=INFO
export LOG_LEVEL_ERRORS=ERROR
export LOG_LEVEL_HTTP=WARNING
export LOG_LEVEL_AUDIT=INFO
export LOG_FILE_SIZE=5242880
export LOG_BACKUP_COUNT=10
export LOG_DIR=/var/log/leviia
export LOG_FILTER_SENSITIVE=true
export SYSLOG_ENABLED=true
export SYSLOG_ADDRESS=/dev/log
export SYSLOG_FACILITY=local0
export LOGIN_DISABLED=false
export CORS_ENABLED=false
export DEBUG_ERRORS=false
```

---

## 🧪 Tests et Qualité

### Outils de Qualité

| Outil | Version | Rôle |
|-------|---------|------|
| **pytest** | 8.3.5 | Exécution des tests unitaires |
| **Ruff** | 0.6.4 | Linting (style et bonnes pratiques) |
| **mypy** | 1.12.0 | Vérification des types |
| **Black** | 24.10.0 | Formatage automatique du code |
| **Bandit** | 1.7.10 | Analyse de sécurité statique |
| **Safety** | 2.3.5 | Scan des vulnérabilités des dépendances |

### Structure des Tests

```
tests/
├── __init__.py
├── conftest.py               # Fixtures pytest
├── test_models.py            # Tests des modèles
├── test_routes.py            # Tests des routes
├── test_auth.py              # Tests d'authentification
├── test_export.py            # Tests d'export ICS
├── test_error_handlers.py   # Tests des gestionnaires d'erreurs
└── ...
```

### Exécution des Tests

```bash
# Exécuter tous les tests
make test

# Exécuter avec couverture de code
pytest tests/ --cov=app --cov=config --cov-report=term-missing

# Exécuter un test spécifique
pytest tests/test_models.py::TestUserModel::test_user_creation -v

# Linting
make lint

# Formatage
make format

# Analyse de sécurité
make security

# Tout en une seule commande
make all
```

### Couverture de Code

- **Statut actuel** : 66% (248 tests)
- **Objectif** : 80%+

---

## 📚 Bonnes Pratiques

### Pour les Développeurs

1. **Structure du Code** :
   - Respecter la structure du projet existante
   - Utiliser des noms de fichiers et de classes clairs
   - Organiser le code par fonctionnalité

2. **Nommage** :
   - Utiliser des noms descriptifs pour les variables et fonctions
   - Suivre les conventions PEP 8
   - Utiliser snake_case pour les variables et fonctions
   - Utiliser PascalCase pour les classes

3. **Documentation** :
   - Documenter toutes les fonctions et classes
   - Ajouter des docstrings claires
   - Commenter le code complexe

4. **Tests** :
   - Écrire des tests pour toutes les nouvelles fonctionnalités
   - Tester les cas normaux et les cas d'erreur
   - Maintenir une couverture de code élevée

5. **Sécurité** :
   - Ne jamais stocker de données sensibles en clair
   - Utiliser les fonctions de hashage fournies
   - Valider toutes les entrées utilisateur
   - Échapper les sorties dans les templates

6. **Performance** :
   - Optimiser les requêtes de base de données
   - Utiliser les index appropriés
   - Éviter les requêtes N+1
   - Utiliser le lazy loading judicieusement

7. **Logging** :
   - Logger les actions importantes
   - Utiliser les niveaux de log appropriés
   - Inclure le contexte dans les logs
   - Ne pas logger de données sensibles

### Pour les Administrateurs

1. **Configuration** :
   - Utiliser des variables d'environnement pour les secrets
   - Configurer le logging selon l'environnement
   - Activer syslog en production

2. **Sécurité** :
   - Désactiver DEBUG en production
   - Désactiver DEBUG_ERRORS en production
   - Activer le filtrage des données sensibles
   - Utiliser HTTPS

3. **Monitoring** :
   - Surveiller les logs régulièrement
   - Configurer des alertes pour les erreurs critiques
   - Analyser les patterns d'erreurs

4. **Maintenance** :
   - Effectuer des sauvegardes régulières
   - Mettre à jour les dépendances
   - Effectuer des audits de sécurité

---

## 📝 Historique des Changements

| Version | Date | Auteur | Changements |
|---------|------|--------|-------------|
| 1.0.0 | Juin 2026 | Vibe Code | Création initiale de la documentation d'architecture |

---

## 📞 Contact

Pour toute question concernant l'architecture technique :
- Ouvrir une **Issue** sur GitHub
- Ouvrir une **Discussion** sur GitHub
- Contactez l'équipe via les canaux officiels

---

> **⚠️ Note importante** : Cette documentation est évolutive et peut être mise à jour en fonction des changements dans l'application. Vérifiez régulièrement les mises à jour.

---

*Documentation générée pour Leviia Schedule - Architecture Technique*
