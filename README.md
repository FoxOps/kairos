# Leviia Schedule

> **⚠️ Avertissement : Version de développement**
> Ce projet est actuellement en phase de développement actif et **n'est pas prêt pour une utilisation en production**.
> Il peut contenir des bugs, des fonctionnalités incomplètes ou des problèmes de sécurité.
> **Ne l'utilisez pas en environnement de production sans une revue complète et des tests approfondis.**

---

## 📚 Documentation

**La documentation complète est disponible dans [docs/](docs/)**

### 🎯 **Par où commencer ?**

| Rôle | Document Recommandé | Description |
|------|---------------------|-------------|
| **👥 Utilisateur** | [docs/QUICK_START.md](docs/QUICK_START.md) | Guide de démarrage rapide (5 min) |
| **🛡️ Administrateur** | [docs/ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md) | Configuration, sécurité, maintenance |
| **💻 Développeur** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture technique, API |
| **📖 Tous** | [docs/README.md](docs/README.md) | **Index complet** de toute la documentation |

> **💡 Pour une prise en main rapide, consultez le [Guide de Démarrage Rapide](docs/QUICK_START.md)**

---

## 📋 Description

**Leviia Schedule** est une application web de gestion des plannings et des astreintes conçue pour les équipes et organisations.
Elle permet de gérer les horaires de travail, les rotations d'astreinte et les congés des membres d'une équipe.

### Fonctionnalités principales

- ✅ **Gestion des utilisateurs et groupes** (avec permissions)
- ✅ **Gestion des types de shifts** (horaires personnalisables)
- ✅ **Planning des shifts** avec visualisation jour/semaine/mois
- ✅ **Gestion des astreintes (On-Call)** avec rotations automatiques
- ✅ **Gestion des congés** avec visualisation dans le planning
- ✅ **Export ICS** pour intégration avec Google Calendar, Outlook, etc.
- ✅ **Authentification sécurisée** (Flask-Login)
- ✅ **Système de logging complet** avec rotation automatique
- ✅ **Automatisation intelligente** avec règles métiers

---

## 🛠 Technologies

| Composant | Technologie | Version |
|-----------|-------------|---------|
| **Framework Web** | Flask | 3.1.3 |
| **ORM** | SQLAlchemy | 2.0.51 |
| **Base de données** | SQLite (par défaut), PostgreSQL | - |
| **Authentification** | Flask-Login | 0.6.3 |
| **Export ICS** | icalendar | 7.1.3 |

---

## 📦 Prérequis

- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)
- Git (optionnel, pour le clonage du dépôt)

---

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

### 4. Démarrer l'application

```bash
python run.py
```

L'application sera accessible à l'adresse : **http://localhost:5000**

> **📖 Documentation détaillée** : [docs/QUICK_START.md](docs/QUICK_START.md)

---

## 🎯 Utilisation

### Première connexion

1. Connectez-vous avec les identifiants par défaut :
   - Email : `admin@leviia.local`
   - Mot de passe : `admin123`

2. **⚠️ Changez immédiatement le mot de passe** après la première connexion via le menu Profil.

> **📖 Documentation complète** :
> - [Guide Utilisateur](docs/USER_GUIDE.md) - Pour l'utilisation quotidienne
> - [Guide Administrateur](docs/ADMIN_GUIDE.md) - Pour la configuration et la gestion

---

## 📁 Structure du projet

```
leviia-schedule/
├── app/                    # Code source de l'application
│   ├── __init__.py         # Initialisation Flask
│   ├── models.py           # Modèles de la base de données
│   ├── routes/             # Routes de l'application
│   └── utils/              # Fonctions utilitaires
├── config.py               # Configuration de l'application
├── run.py                  # Point d'entrée
├── requirements.txt        # Dépendances Python
├── docs/                   # 📚 Documentation complète
│   ├── README.md          # Index de la documentation (ce fichier)
│   ├── QUICK_START.md     # Guide de démarrage rapide
│   ├── USER_GUIDE.md      # Guide utilisateur complet
│   ├── ADMIN_GUIDE.md     # Guide administrateur
│   ├── ARCHITECTURE.md    # Architecture technique
│   ├── API.md             # Documentation API REST
│   ├── ERROR_HANDLING.md  # Gestion des erreurs
│   └── SUMMARY.md         # Résumé technique
└── tests/                  # Tests unitaires (403 tests)
```

> **📖 Documentation technique** : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 🧪 Tests et Qualité de Code

> **✅ Statut** : **403 tests** - Tous passent - Couverture : ~66%

### Exécuter les tests

```bash
# Installer les dépendances de test
pip install -r requirements.txt

# Exécuter tous les tests
pytest tests/ -v --tb=short

# Exécuter avec couverture de code
pytest tests/ --cov=app --cov=config --cov-report=term-missing
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

> **📖 Documentation des tests** : [TESTING_SUMMARY.md](TESTING_SUMMARY.md)

---

## 📝 Contribution

Les contributions sont les bienvenues !

1. **Forker** le dépôt
2. Créer une branche pour votre fonctionnalité (`git checkout -b feature/ma-fonctionnalité`)
3. Commiter vos changements (`git commit -m 'Ajout de ma fonctionnalité'`)
4. Pousser vers la branche (`git push origin feature/ma-fonctionnalité`)
5. Ouvrir une **Pull Request**

> **📖 Guide de contribution** : [docs/README.md - Contribuer à la Documentation](docs/README.md#-contribuer-à-la-documentation)

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
- **Tests** : 403 tests unitaires (tous passent)
- **Couverture** : ~66%

> **📖 Feuille de route** : [ROADMAP.md](ROADMAP.md)

---

> **⚠️ Rappel : Version de développement**
> Ce logiciel est fourni "tel quel", sans garantie d'aucune sorte.
> L'auteur ne peut être tenu responsable de tout dommage direct, indirect,
> accessoire, spécial ou consécutif découlant de l'utilisation de ce logiciel.
> **Utilisez-le à vos propres risques.**
