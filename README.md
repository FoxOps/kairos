# Leviia Schedule

> **⚠️ Avertissement : Version de développement**
> Ce projet est actuellement en phase de développement actif et **n'est pas prêt pour une utilisation en production**.
> Il peut contenir des bugs, des fonctionnalités incomplètes ou des problèmes de sécurité.
> **Ne l'utilisez pas en environnement de production sans une revue complète et des tests approfondis.**

---

## 📚 Documentation

> **📖 Documentation complète disponible dans [docs/](docs/)**

| Type | Document | Description | Public |
|------|----------|-------------|--------|
| **📖 Utilisateur** | [USER_GUIDE.md](docs/USER_GUIDE.md) | Guide utilisateur complet (15 chapitres) | ✅ Tous |
| **🚀 Démarrage** | [QUICK_START.md](docs/QUICK_START.md) | Installation et configuration en 5 minutes | ✅ Tous |
| **🛡️ Admin** | [ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md) | Configuration avancée, sécurité, maintenance | ⚠️ Administrateurs |
| **🏗️ Technique** | [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture technique complète | ✅ Développeurs |
| **📡 API** | [API.md](docs/API.md) | Documentation API REST complète | ✅ Développeurs |
| **🔍 Erreurs** | [ERROR_HANDLING.md](docs/ERROR_HANDLING.md) | Gestion des erreurs et exceptions | ✅ Développeurs |
| **📝 Résumé** | [SUMMARY.md](docs/SUMMARY.md) | Résumé technique complet | ✅ Développeurs |

---

## 📋 Description

**Leviia Schedule** est une application web de gestion des plannings et des astreintes conçue pour les équipes et organisations.
Elle permet de gérer les horaires de travail, les rotations d'astreinte et les congés des membres d'une équipe.

> **💡 Pour une prise en main rapide, consultez le [Guide de Démarrage Rapide](docs/QUICK_START.md)**

### Fonctionnalités principales

- ✅ **Gestion des utilisateurs et groupes**
  - Création et gestion des utilisateurs
  - Organisation en groupes avec permissions spécifiques
  - Rôles administrateur et utilisateur standard
  - Génération de tokens ICS uniques pour chaque utilisateur

- ✅ **Gestion des types de shifts**
  - Configuration des types de shifts (matin 07h-15h, après-midi 09h-17h, soirée 13h-21h)
  - Personnalisation des horaires de début et fin
  - Création dynamique de types de shifts

- ✅ **Planning des shifts**
  - Attribution des shifts aux utilisateurs
  - Visualisation du planning par jour/semaine/mois
  - Historique des shifts passés
  - **Automatisation avancée** avec règles métiers complexes

- ✅ **Gestion des astreintes (On-Call)**
  - Planification des rotations d'astreinte
  - Notification des personnes de garde
  - **Règles de rotation automatiques**
  - Contrainte légale : pas 2 astreintes de suite (minimum 2 semaines sans astreinte)

- ✅ **Gestion des congés**
  - Saisie des périodes de congé
  - Motif des absences
  - Visualisation dans le planning
  - Gestion des conflits avec les shifts et astreintes

- ✅ **Export des données**
  - Export du planning au format iCalendar (ICS)
  - Intégration avec les applications de calendrier (Google Calendar, Outlook, Thunderbird, etc.)
  - **Export par token** : accès sans authentification via URL unique
  - Export séparé pour shifts, astreintes et congés

- ✅ **Authentification sécurisée**
  - Système de login/mot de passe avec hashage
  - Protection des routes sensibles
  - Gestion des sessions avec Flask-Login
  - Option de "remember me" pour les sessions persistantes

- ✅ **Gestion des erreurs avancée**
  - Pages d'erreur personnalisées (400, 401, 403, 404, 405, 500, 502, 503, 504)
  - Gestion des erreurs de base de données (verrouillage SQLite)
  - Réponses JSON pour les requêtes AJAX

- ✅ **Système de logging complet**
  - Rotation automatique des fichiers de log
  - Filtrage des données sensibles (mots de passe, tokens, etc.)
  - Support syslog pour la production
  - Niveaux de log configurables par module
  - Journaux dédiés (application, erreurs, HTTP, debug, audit)

- ✅ **Automatisation intelligente**
  - Génération automatique des shifts selon des règles métiers
  - Rotation automatique des astreintes
  - Gestion des conflits et remplacements
  - Optimisation des requêtes SQL

## 🛠 Technologies utilisées

| Composant | Technologie | Version |
|-----------|-------------|---------|
| **Framework Web** | Flask | 3.1.3 |
| **ORM** | SQLAlchemy | 2.0.51 |
| **Base de données** | SQLite (par défaut), PostgreSQL | - |
| **Authentification** | Flask-Login | 0.6.3 |
| **Export ICS** | icalendar | 7.1.3 |
| **Gestion des dates** | python-dateutil, pytz | 2.9.0.post0, 2026.2 |
| **Tests** | pytest | 9.1.1 |
| **Linting** | Ruff | 0.15.18 |
| **Vérification des types** | mypy | 2.1.0 |
| **Formatage** | Black | 26.5.1 |
| **Sécurité** | Bandit, Safety | 1.9.4, 3.8.1 |

## 📦 Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)
- Git (optionnel, pour le clonage du dépôt)

## 🚀 Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/FoxOps/leviia-schedule.git
cd leviia-schedule
```

### 2. Créer un environnement virtuel (recommandé)

```bash
# Sur Linux/macOS
python -m venv venv
source venv/bin/activate

# Sur Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer l'application

#### Configuration de base

Le fichier `config.py` contient la configuration par défaut. Vous pouvez le modifier directement ou utiliser des variables d'environnement :

```python
# config.py
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ta-cle-secrete-ici'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOGIN_DISABLED = False  # Désactive l'authentification si True
```

#### Configuration avancée

Le projet supporte de nombreuses options de configuration via variables d'environnement :

```bash
# Générer une clé secrète sécurisée
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Configuration du logging
export LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
export LOG_FILE_SIZE=5242880  # 5 Mo
export LOG_BACKUP_COUNT=10
export LOG_DIR=/var/log/leviia

# Activation du logging syslog
export SYSLOG_ENABLED=true
export SYSLOG_ADDRESS=/dev/log
export SYSLOG_FACILITY=local0

# Filtrage des données sensibles dans les logs
export LOG_FILTER_SENSITIVE=true

# Configuration SQLite pour éviter les verrouillages
export SQLALCHEMY_ENGINE_OPTIONS='{"connect_args": {"timeout": 30}}'

# Pour utiliser PostgreSQL
export SQLALCHEMY_DATABASE_URI='postgresql://user:password@localhost/leviia'

# Désactiver l'authentification (développement uniquement)
export LOGIN_DISABLED=true

# Mode développement
export FLASK_ENV=development
export FLASK_DEBUG=true
```

### 5. Initialiser la base de données

```bash
# Exécuter l'application pour la première fois
# Cela créera la base de données et les tables nécessaires
python run.py
```

> **Note** : La première exécution créera automatiquement :
> - Un utilisateur administrateur par défaut
> - Email : `admin@leviia.local`
> - Mot de passe : `admin123`
> - Un groupe par défaut ("Défaut")
> - Les types de shifts par défaut (07h-15h, 09h-17h, 13h-21h)

### 6. Démarrer l'application

```bash
python run.py
```

L'application sera accessible à l'adresse : **http://localhost:5000**

> **⚠️ Note** : Le reloader Flask est désactivé par défaut pour éviter les problèmes de "database is locked" avec SQLite. Pour le développement, vous pouvez modifier `run.py` si nécessaire.

## 🎯 Utilisation

> **📖 Pour une documentation utilisateur complète, consultez le [Guide Utilisateur](docs/USER_GUIDE.md)**

### Première connexion

1. Connectez-vous avec les identifiants par défaut :
   - Email : `admin@leviia.local`
   - Mot de passe : `admin123`

2. **Changez immédiatement le mot de passe** après la première connexion via le menu Profil.

> **⚠️ IMPORTANT** : Voir [ADMIN_GUIDE.md - Gestion de la Sécurité](docs/ADMIN_GUIDE.md#gestion-de-la-sécurité) pour les bonnes pratiques de sécurité.

### Gestion des utilisateurs

- Les administrateurs peuvent créer, modifier et supprimer des utilisateurs
- Chaque utilisateur appartient à un groupe
- Les groupes peuvent être inclus ou exclus du planning et des astreintes
- Chaque utilisateur peut générer un **token ICS unique** pour exporter son planning

> **📖 Documentation détaillée** : [ADMIN_GUIDE.md - Gestion Avancée des Utilisateurs](docs/ADMIN_GUIDE.md#gestion-avancée-des-utilisateurs)

### Gestion des shifts

1. Configurez les types de shifts dans l'interface d'administration
2. Attribuez des shifts aux utilisateurs via le calendrier
3. Visualisez le planning par jour, semaine ou mois
4. **Automatisation** : Utilisez le système d'automatisation pour générer des shifts selon des règles métiers

> **📖 Documentation détaillée** : [USER_GUIDE.md - Gestion des Shifts](docs/USER_GUIDE.md#gestion-des-shifts)

### Règles métiers avancées pour les shifts

Le système implémente les règles suivantes :
- **Créneau 13h-21h** : Réservé à la personne d'astreinte SI elle fait partie d'un groupe schedule
- **Rotation des créneaux** : Si une personne était sur 13h-21h une semaine, elle doit être sur 07h-15h la semaine suivante
- **Créneau par défaut** : 09h-17h pour tous les autres cas (plusieurs personnes peuvent être sur ce créneau)
- **Cas des congés** : Si seulement 2 personnes disponibles, la personne NON d'astreinte doit être sur 07h-15h
- **Contrainte légale** : Pas 2 astreintes de suite - minimum 2 semaines sans astreinte entre deux astreintes

### Gestion des astreintes

1. Activez la participation aux astreintes pour les groupes concernés
2. Planifiez les rotations d'astreinte (début le vendredi à 21h, durée 7 jours)
3. Les utilisateurs sont notifiés de leurs périodes d'astreinte
4. **Automatisation** : Utilisez le système de rotation automatique

> **📖 Documentation détaillée** : [USER_GUIDE.md - Gestion des Astreintes](docs/USER_GUIDE.md#gestion-des-astreintes-on-call)

### Export du planning

- Exportez votre planning personnel au format ICS
- Importez le fichier dans votre application de calendrier préférée
- Les mises à jour du planning sont automatiquement synchronisées
- **3 types d'export** :
  - `/export/shifts` - Export des shifts
  - `/export/oncall` - Export des astreintes
  - `/export/leaves` - Export des congés
- **2 modes** :
  - `?scope=my` - Uniquement vos données
  - `?scope=all` - Toutes les données (admin uniquement)
- **Accès par token** : `?token=VOTRE_TOKEN_ICS` pour un accès sans authentification

> **📖 Documentation détaillée** : [USER_GUIDE.md - Export ICS](docs/USER_GUIDE.md#export-ics-et-intégration-calendrier)

## 📁 Structure du projet

```
leviia-schedule/
├── app/
│   ├── __init__.py          # Initialisation Flask, extensions, logging, gestion des erreurs
│   ├── models.py            # Modèles de la base de données (6 modèles)
│   │
│   ├── routes/
│   │   ├── __init__.py      # Import des modules de routes
│   │   ├── admin.py         # Routes d'administration (utilisateurs, groupes, shifts, astreintes)
│   │   ├── auth.py          # Routes d'authentification (login, logout, profil)
│   │   ├── export.py        # Export ICS (shifts, astreintes, congés)
│   │   └── main.py          # Routes principales (calendrier, planning)
│   │
│   └── utils/
│       ├── __init__.py
│       ├── advanced_shift_automation.py  # Automatisation avancée des shifts avec règles métiers
│       ├── automation.py    # Automatisation des astreintes et shifts
│       ├── decorators.py    # Décorateurs de permissions (admin_required, user_owns_resource)
│       ├── helpers.py       # Fonctions utilitaires (vérifications, validations)
│       └── ics_exporter.py  # Export ICS
│
├── config.py                # Configuration de l'application (dev, prod, test)
├── run.py                   # Point d'entrée de l'application
├── requirements.txt         # Dépendances Python
├── Makefile                 # Commandes utiles (test, lint, format, security)
├── .ruff.toml               # Configuration de Ruff
├── tests/                   # 403 tests unitaires
│   ├── conftest.py          # Configuration des tests
│   ├── test_models.py       # Tests des modèles
│   ├── test_routes.py       # Tests des routes
│   ├── test_auth_priority.py # Tests d'authentification
│   ├── test_admin_*.py      # Tests des fonctionnalités admin
│   ├── test_automation.py   # Tests de l'automatisation
│   ├── test_advanced_shift_automation.py # Tests de l'automatisation avancée
│   ├── test_error_handlers.py # Tests des gestionnaires d'erreurs
│   ├── test_export_routes.py # Tests des routes d'export
│   ├── test_ics_export.py   # Tests de l'export ICS
│   ├── test_helpers.py      # Tests des helpers
│   ├── test_decorators.py   # Tests des décorateurs
│   ├── test_config.py       # Tests de la configuration
│   └── ...
├── docs/                    # 📚 Documentation complète
│   ├── README.md           # Index de la documentation
│   ├── QUICK_START.md      # Guide de démarrage rapide
│   ├── USER_GUIDE.md       # Guide utilisateur complet (15 chapitres)
│   ├── ADMIN_GUIDE.md      # Guide administrateur
│   ├── ARCHITECTURE.md     # Architecture technique
│   ├── API.md              # Documentation API REST
│   ├── ERROR_HANDLING.md   # Gestion des erreurs
│   └── SUMMARY.md          # Résumé technique
├── instance/                # Fichiers d'instance (base de données)
│   └── app.db               # Base de données SQLite
└── logs/                    # Fichiers de log (créés automatiquement)
```

> **📖 Documentation technique complète** : [ARCHITECTURE.md](docs/ARCHITECTURE.md)

### Modèles de données

| Modèle | Description | Relations |
|--------|-------------|-----------|
| **User** | Utilisateur | → Group, Shift, OnCall, Leave |
| **Group** | Groupe d'utilisateurs | → User |
| **ShiftType** | Type de shift (horaires) | → Shift |
| **Shift** | Shift attribué | → User, ShiftType |
| **OnCall** | Astreinte | → User |
| **Leave** | Congé | → User |

## 🔧 Configuration avancée

> **📖 Documentation technique détaillée** : [ADMIN_GUIDE.md - Configuration Technique](docs/ADMIN_GUIDE.md#configuration-technique)

### Utiliser PostgreSQL

1. Installez PostgreSQL et créez une base de données :
   ```bash
   sudo apt-get install postgresql postgresql-contrib
   sudo -u postgres createdb leviia
   sudo -u postgres createuser leviia_user
   ```

2. Modifiez la configuration :
   ```bash
   export SQLALCHEMY_DATABASE_URI='postgresql://leviia_user:password@localhost/leviia'
   ```

3. Installez le driver PostgreSQL :
   ```bash
   pip install psycopg2-binary
   ```

> **📖 Architecture technique** : [ARCHITECTURE.md - Environnements](docs/ARCHITECTURE.md#environnements)

### Désactiver l'authentification (développement uniquement)

Dans `config.py` ou via variable d'environnement :
```python
LOGIN_DISABLED = True
```

> ⚠️ **Ne jamais utiliser cette option en production !**

### Configurer le niveau de log

```bash
# Niveaux disponibles : DEBUG, INFO, WARNING, ERROR, CRITICAL
export LOG_LEVEL=DEBUG

# Niveaux par module
export LOG_LEVEL_APP=INFO
export LOG_LEVEL_ERRORS=ERROR
export LOG_LEVEL_HTTP=WARNING
export LOG_LEVEL_DEBUG=DEBUG
export LOG_LEVEL_AUDIT=INFO
```

### Configurer syslog pour la production

```bash
export SYSLOG_ENABLED=true
export SYSLOG_ADDRESS=/dev/log
export SYSLOG_FACILITY=local0
```

### Optimisation des performances

Le projet inclut plusieurs optimisations :
- **Index composites** sur les tables Shift, OnCall, Leave pour les requêtes fréquentes
- **joinedload** pour éviter le problème N+1 dans les requêtes
- **Pool de connexions** SQLite configuré pour éviter les verrouillages
- **Requêtes batch** pour les vérifications multiples

## 🧪 Tests et Qualité de Code

> **✅ Statut** : **403 tests** - Tous passent - Couverture : ~66%

> **📖 Documentation des tests** : [TESTING_SUMMARY.md](TESTING_SUMMARY.md) - Documentation détaillée de tous les tests unitaires

### Outils utilisés

Ce projet utilise les outils suivants pour garantir la qualité, la sécurité et la cohérence du code :

| Outil | Rôle | Version |
|-------|------|---------|
| **pytest** | Exécution des tests unitaires | 9.1.1 |
| **pytest-flask** | Plugin Flask pour pytest | 1.3.0 |
| **Ruff** | Linting (style et bonnes pratiques) | 0.15.18 |
| **mypy** | Vérification des types | 2.1.0 |
| **Black** | Formatage automatique du code | 26.5.1 |
| **Bandit** | Analyse de sécurité statique | 1.9.4 |
| **Safety** | Scan des vulnérabilités des dépendances | 3.8.1 |

---

### 📦 Installation des dépendances

Avant d'exécuter les tests ou les outils de qualité, installez les dépendances :

```bash
# Méthode 1 : Utiliser le Makefile (recommandé)
make install

# Méthode 2 : Installer manuellement
pip install -r requirements.txt
```

---

### 🏃 Exécuter les tests

#### Exécuter tous les tests
```bash
# Méthode 1 : Avec le Makefile
make test

# Méthode 2 : Directement avec pytest
pytest tests/ -v --tb=short
```

#### Exécuter les tests avec couverture de code
```bash
# Installer pytest-cov si ce n'est pas déjà fait
pip install pytest-cov

# Exécuter avec couverture
pytest tests/ --cov=app --cov=config --cov-report=term-missing

# Générer un rapport HTML (ouvrir htmlcov/index.html dans un navigateur)
pytest tests/ --cov=app --cov=config --cov-report=html
```

#### Exécuter un test spécifique
```bash
# Syntaxe : pytest <fichier>::<classe>::<méthode>
pytest tests/test_models.py::TestUserModel::test_user_creation -v
```

#### Exécuter les tests par catégorie
```bash
# Tests des modèles
pytest tests/test_models.py -v

# Tests des routes
pytest tests/test_routes.py -v

# Tests de l'automatisation
pytest tests/test_automation.py -v

# Tests de l'export ICS
pytest tests/test_export_routes.py tests/test_ics_export.py -v

# Tests des décorateurs
pytest tests/test_decorators.py -v

# Tests de la configuration
pytest tests/test_config.py -v
```

---

### 🔍 Vérification de la qualité du code

#### Linting avec Ruff et mypy
```bash
# Méthode 1 : Avec le Makefile
make lint

# Méthode 2 : Exécuter manuellement
ruff check . --config=.ruff.toml
mypy app/ tests/ --ignore-missing-imports --allow-untyped-decorators
```

#### Corriger automatiquement les erreurs Ruff
```bash
ruff check . --config=.ruff.toml --fix
```

---

### 🎨 Formatage du code avec Black

#### Vérifier le formatage (sans modifier les fichiers)
```bash
# Méthode 1 : Avec le Makefile
make format

# Méthode 2 : Directement avec Black
black --check . --exclude=".git|__pycache__|instance|venv"
```

#### Appliquer le formatage
```bash
# Méthode 1 : Avec le Makefile
make format-fix

# Méthode 2 : Directement avec Black
black . --exclude=".git|__pycache__|instance|venv"
```

---

### 🔒 Analyse de sécurité

#### Exécuter Bandit et Safety
```bash
# Méthode 1 : Avec le Makefile
make security

# Méthode 2 : Exécuter manuellement
bandit -r app/ tests/ -f json -o bandit-results.json
safety check --full-report
```

> **Note** : Les commandes de sécurité peuvent générer des avertissements même si le code est sûr. Vérifiez toujours les résultats manuellement.

---

### 🚀 Exécuter tout en une seule commande

Pour exécuter **tous les tests, le linting, le formatage et l'analyse de sécurité** en une seule commande :

```bash
make all
```

---

### 🧹 Nettoyage

Pour supprimer les fichiers temporaires (ex: `__pycache__`, `.pyc`, rapports de sécurité) :

```bash
make clean
```

---

### 📄 Documentation complète

Voir les fichiers suivants pour une documentation détaillée :
- **[docs/README.md](docs/README.md)** - Index complet de la documentation
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Architecture technique complète
- **[docs/API.md](docs/API.md)** - Documentation API REST
- **[docs/SUMMARY.md](docs/SUMMARY.md)** - Résumé technique complet
- [TESTING_SUMMARY.md](TESTING_SUMMARY.md) - Documentation détaillée de tous les tests unitaires
- [TESTS_SUMMARY.md](TESTS_SUMMARY.md) - Résumé des tests
- [ROADMAP.md](ROADMAP.md) - Feuille de route du projet

## 📝 Contribution

Les contributions sont les bienvenues ! Voici comment contribuer :

1. **Forker** le dépôt
2. Créer une branche pour votre fonctionnalité (`git checkout -b feature/ma-fonctionnalité`)
3. Commiter vos changements (`git commit -m 'Ajout de ma fonctionnalité'`)
4. Pousser vers la branche (`git push origin feature/ma-fonctionnalité`)
5. Ouvrir une **Pull Request**

### Bonnes pratiques

- Respectez le style de code existant
- Ajoutez des tests pour les nouvelles fonctionnalités
- Documentez votre code avec des commentaires clairs
- Mettez à jour ce README si nécessaire
- Utilisez les décorateurs de permissions appropriés
- Suivez les conventions de nommage existantes

> **📖 Guide de contribution** : Voir [docs/README.md - Contribuer à la Documentation](docs/README.md#contribuer-à-la-documentation) pour les règles de contribution à la documentation.

## 🐛 Signaler un bug

Pour signaler un bug, ouvrez une **Issue** sur GitHub avec les informations suivantes :

- Version de l'application
- Étapes pour reproduire le bug
- Comportement attendu
- Comportement réel
- Captures d'écran (si applicable)
- Logs d'erreur (si applicable)
- Configuration utilisée (SQLite/PostgreSQL, etc.)

## 📜 Licence

Ce projet est sous licence **CeCILL v2.1**. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

La licence CeCILL est une licence de logiciel libre conforme au droit français, compatible avec les principes du logiciel libre et open source.

## 🙏 Remerciements

- [Flask](https://flask.palletsprojects.com/) - Framework web léger et puissant
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM Python
- [icalendar](https://github.com/collective/icalendar) - Bibliothèque d'export ICS
- [pytest](https://docs.pytest.org/) - Framework de test
- [Ruff](https://github.com/astral-sh/ruff) - Linter rapide
- [mypy](https://mypy-lang.org/) - Vérificateur de types
- [Black](https://github.com/psf/black) - Formateur de code

## 📞 Contact

Pour toute question ou suggestion, n'hésitez pas à ouvrir une **Issue** ou une **Discussion** sur le dépôt GitHub.

---

## 📌 Notes de version

### Version actuelle (en développement)

- **Statut** : Développement actif
- **Stabilité** : Non recommandé pour la production
- **Fonctionnalités** : Toutes les fonctionnalités de base sont implémentées
- **Tests** : 403 tests unitaires (tous passent)
- **Couverture** : ~66%

### Fonctionnalités implémentées

✅ **Cœur de l'application**
- Gestion complète des utilisateurs et groupes
- Système d'authentification sécurisé
- Gestion des shifts avec types personnalisables
- Gestion des astreintes avec rotations
- Gestion des congés

✅ **Export et intégration**
- Export ICS pour shifts, astreintes et congés
- Authentification par token pour l'export
- Intégration avec les calendriers externes

✅ **Automatisation**
- Génération automatique des shifts
- Rotation automatique des astreintes
- Règles métiers avancées
- Gestion des conflits

✅ **Qualité et sécurité**
- 403 tests unitaires
- Système de logging complet
- Gestion des erreurs personnalisées
- Analyse de sécurité (Bandit, Safety)
- Linting (Ruff) et vérification des types (mypy)
- Formatage automatique (Black)

✅ **Infrastructure**
- Support SQLite et PostgreSQL
- Configuration flexible via variables d'environnement
- Makefile pour les tâches courantes
- Documentation complète

### Prochaines étapes

Voir [ROADMAP.md](ROADMAP.md) pour la feuille de route détaillée.

---

> **⚠️ Rappel : Version de développement**
> Ce logiciel est fourni "tel quel", sans garantie d'aucune sorte.
> L'auteur ne peut être tenu responsable de tout dommage direct, indirect,
> accessoire, spécial ou consécutif découlant de l'utilisation de ce logiciel.
> **Utilisez-le à vos propres risques.**
