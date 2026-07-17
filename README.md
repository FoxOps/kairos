# Leviia Schedule

> **⚠️ Avertissement : Version de développement**
> Ce projet est actuellement en phase de développement actif et **n'est pas prêt pour une utilisation en production**.
> Il peut contenir des bugs, des fonctionnalités incomplètes ou des problèmes de sécurité.
> **Ne l'utilisez pas en environnement de production sans une revue complète et des tests approfondis.**

---

## 📚 Documentation

**La documentation complète est disponible dans [Docs/](Docs/)**

### 🎯 **Par où commencer ?**

| Rôle | Document Recommandé | Description |
|------|---------------------|-------------|
| **👥 Utilisateur** | [Docs/guides/QUICK_START.md](Docs/guides/QUICK_START.md) | Guide de démarrage rapide (5 min) |
| **🛡️ Administrateur** | [Docs/guides/ADMIN_GUIDE.md](Docs/guides/ADMIN_GUIDE.md) | Configuration, sécurité, maintenance |
| **💻 Développeur** | [Docs/architecture/ARCHITECTURE.md](Docs/architecture/ARCHITECTURE.md) | Architecture technique, diagrammes |
| **📖 Tous** | [Docs/README.md](Docs/README.md) | **Index complet** de toute la documentation |

> **💡 Pour une prise en main rapide, consultez le [Guide de Démarrage Rapide](Docs/guides/QUICK_START.md)**

---

## 📋 Description

**Leviia Schedule** est une application web de gestion des plannings, astreintes et congés d'équipe.
Elle permet de gérer les horaires de travail, les rotations d'astreinte et les congés des membres d'une équipe.

### Fonctionnalités principales

- ✅ **Gestion des utilisateurs et groupes** (avec permissions)
- ✅ **Gestion des types de shifts** (horaires personnalisables)
- ✅ **Planning des shifts** avec visualisation jour/semaine/mois
- ✅ **Gestion des astreintes (On-Call)** avec rotations automatiques
- ✅ **Gestion des congés** avec visualisation dans le planning
- ✅ **Notifications par email** : rappels hebdomadaires des shifts et
  de l'astreinte à venir (SMTP configurable, scripts cron autonomes)
- ✅ **Échanges de shifts entre utilisateurs** : demande (don simple ou
  réciproque), validation/rejet/annulation par un admin, notifications
  internes (cloche)
- ✅ **Multi-langues** (Français/Anglais) et **multi-fuseau horaire**,
  personnalisables par utilisateur ou par défaut pour toute
  l'organisation (`/admin/settings`)
- ✅ **Formats de date/heure configurables** (par utilisateur ou par défaut)
- ✅ **Historique des modifications (audit trail)** : qui a fait quoi,
  quand, consultable dans `/admin/audit-log`
- ✅ **Export ICS** pour intégration avec Google Calendar, Outlook, etc.
- ✅ **Authentification sécurisée** (Flask-Login)
- ✅ **Authentification SSO/OIDC** (Keycloak, Okta, Auth0, etc.)
- ✅ **Système de logging complet** avec rotation automatique
- ✅ **Automatisation intelligente** avec règles métiers

---

## 🛠 Technologies

| Composant | Technologie | Version |
|-----------|-------------|---------|
| **Framework Web** | Flask | 3.1.3 |
| **ORM** | SQLAlchemy | 2.0.51 |
| **Base de données** | SQLite (par défaut), PostgreSQL | - |
| **Authentification** | Flask-Login, Authlib (OIDC) | 0.6.3, 1.7.2 |
| **Export ICS** | icalendar | 7.2.0 |
| **Internationalisation** | Flask-Babel | 4.0.0 |
| **Migrations** | Flask-Migrate (Alembic) | - |

---

## 📦 Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)
- Git (optionnel, pour le clonage du dépôt)

---

## 🐳 Installation (méthode recommandée : Docker Compose)

Pas besoin de cloner le dépôt - deux fichiers suffisent :

```bash
mkdir leviia-schedule && cd leviia-schedule
curl -o docker-compose.yml https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker/docker-compose.example.yml
curl -o .env https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker/.env.example

nano .env  # LEVIIA_IMAGE=harbor.leviia.com/<HARBOR_PROJECT>/leviia-schedule:latest, SECRET_KEY, DEFAULT_ADMIN_PASSWORD

docker compose up -d
```

L'application sera accessible à l'adresse : **http://localhost:5000**

> **📖 Documentation détaillée** : [Docs/deployment/docker.md](Docs/deployment/docker.md)

### Installation locale (développement / cas particuliers)

Réservé au développement sur le code ou aux cas où Docker n'est pas
disponible - l'image Docker ci-dessus reste la façon principale de
lancer l'application.

```bash
git clone https://github.com/FoxOps/leviia-schedule.git
cd leviia-schedule
python -m venv venv
source venv/bin/activate  # Windows : venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

L'application sera accessible à l'adresse : **http://localhost:5000**

> **📖 Documentation détaillée** : [Docs/guides/QUICK_START.md](Docs/guides/QUICK_START.md)

---

## 🎯 Utilisation

### Première connexion

1. Connectez-vous avec les identifiants par défaut :
   - Email : `admin@leviia.local`
   - Mot de passe : `admin123`

2. **⚠️ Changez immédiatement le mot de passe** après la première connexion via le menu Profil.

> **📖 Documentation complète** :
> - [Guide Utilisateur](Docs/guides/USER_GUIDE.md) - Pour l'utilisation quotidienne
> - [Guide Administrateur](Docs/guides/ADMIN_GUIDE.md) - Pour la configuration et la gestion

---

## 📁 Structure du projet

```
leviia-schedule/
├── app/                    # Code source de l'application
│   ├── __init__.py         # Initialisation Flask (factory create_app)
│   ├── models/              # Modèles de la base de données (package)
│   ├── repositories/        # Accès aux données
│   ├── services/             # Logique métier
│   ├── routes/              # Routes / blueprints Flask
│   └── utils/               # Fonctions utilitaires (par sous-package)
├── app/config/              # Configuration (base + testing)
├── run.py                   # Point d'entrée
├── requirements.txt         # Dépendances Python
├── Docs/                    # 📚 Documentation complète
│   ├── README.md            # Index de la documentation
│   ├── architecture/        # Architecture, ERD, diagrammes de séquence
│   ├── api/                 # Documentation API + spec OpenAPI
│   ├── guides/               # Guides utilisateur/admin/démarrage/FAQ
│   ├── deployment/           # Déploiement, Docker, sauvegardes
│   └── reference/             # Variables d'env, erreurs, performance
└── tests/                    # Tests (unit/integration/e2e/fixtures)
```

> **📖 Documentation technique** : [Docs/architecture/ARCHITECTURE.md](Docs/architecture/ARCHITECTURE.md)

---

## 🧪 Tests et Qualité de Code

> **⚠️ Statut** : **1133 tests**, tous passent - Couverture : ~92%

### Exécuter les tests

```bash
# Installer les dépendances de test
pip install -r requirements.txt

# Exécuter tous les tests
pytest tests/ -v --tb=short

# Exécuter avec couverture de code
pytest tests/ --cov=app --cov-report=term-missing
```

### Vérification de la qualité du code

```bash
# Linting avec Ruff
ruff check . --config=.ruff.toml

# Vérification des types avec mypy
mypy app/ tests/ --ignore-missing-imports --allow-untyped-decorators

# Formatage avec Black
black --check . --exclude=".git|__pycache__|instance|venv"
```

> **📖 Documentation des tests** : [report/Phase 4: AMÉLIORATION DES TESTS.md](report/Phase%204%3A%20AM%C3%89LIORATION%20DES%20TESTS.md)

---

## 📝 Contribution

Les contributions sont les bienvenues !

1. **Forker** le dépôt
2. Créer une branche pour votre fonctionnalité (`git checkout -b feature/ma-fonctionnalité`)
3. Commiter vos changements (`git commit -m 'Ajout de ma fonctionnalité'`)
4. Pousser vers la branche (`git push origin feature/ma-fonctionnalité`)
5. Ouvrir une **Pull Request**

> **📖 Guide de contribution** : [Docs/README.md - Contribuer à la documentation](Docs/README.md#contribuer-à-la-documentation)

---

## 🐛 Signaler un bug

Pour signaler un bug, ouvrez une **Issue** sur GitHub avec les informations suivantes :

- Version de l'application
- Étapes pour reproduire le bug
- Comportement attendu
- Comportement réel
- Captures d'écran (si applicable)
- Logs d'erreur (si applicable)
- Configuration utilisée (SQLite/PostgreSQL, etc.)

---

## 📜 Licence

Ce projet est sous licence **CeCILL v2.1**. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## 📞 Contact

Pour toute question ou suggestion, n'hésitez pas à ouvrir une **Issue** ou une **Discussion** sur le dépôt GitHub.

---

## 📌 Notes de version

### Version actuelle (en développement)

- **Statut** : Développement actif
- **Stabilité** : Non recommandé pour la production
- **Fonctionnalités** : Toutes les fonctionnalités de base sont implémentées
- **Tests** : 1133 tests (tous passent)
- **Couverture** : ~92%

> **📖 Feuille de route** : [ROADMAP.md](ROADMAP.md)

---

> **⚠️ Rappel : Version de développement**
> Ce logiciel est fourni "tel quel", sans garantie d'aucune sorte.
> L'auteur ne peut être tenu responsable de tout dommage direct, indirect,
> accessoire, spécial ou consécutif découlant de l'utilisation de ce logiciel.
> **Utilisez-le à vos propres risques.**
