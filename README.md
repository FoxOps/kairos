# Leviia Schedule

> **⚠️ Avertissement : Version de développement**
> Ce projet est actuellement en phase de développement actif et **n'est pas prêt pour une utilisation en production**.
> Il peut contenir des bugs, des fonctionnalités incomplètes ou des problèmes de sécurité.
> **Ne l'utilisez pas en environnement de production sans une revue complète et des tests approfondis.**

---

## 📋 Description

**Leviia Schedule** est une application web de gestion des plannings et des astreintes conçue pour les équipes et organisations.
Elle permet de gérer les horaires de travail, les rotations d'astreinte et les congés des membres d'une équipe.

### Fonctionnalités principales

- ✅ **Gestion des utilisateurs et groupes**
  - Création et gestion des utilisateurs
  - Organisation en groupes avec permissions spécifiques
  - Rôles administrateur et utilisateur standard

- ✅ **Gestion des types de shifts**
  - Configuration des types de shifts (matin, après-midi, soirée)
  - Personnalisation des horaires de début et fin

- ✅ **Planning des shifts**
  - Attribution des shifts aux utilisateurs
  - Visualisation du planning par jour/semaine/mois
  - Historique des shifts passés

- ✅ **Gestion des astreintes (On-Call)**
  - Planification des rotations d'astreinte
  - Notification des personnes de garde

- ✅ **Gestion des congés**
  - Saisie des périodes de congé
  - Motif des absences
  - Visualisation dans le planning

- ✅ **Export des données**
  - Export du planning au format iCalendar (ICS)
  - Intégration avec les applications de calendrier (Google Calendar, Outlook, etc.)

- ✅ **Authentification sécurisée**
  - Système de login/mot de passe
  - Protection des routes sensibles
  - Gestion des sessions

## 🛠 Technologies utilisées

| Composant | Technologie | Version |
|-----------|-------------|---------|
| **Framework Web** | Flask | 3.1.1 |
| **ORM** | SQLAlchemy | 2.0.36 |
| **Base de données** | SQLite (par défaut) | - |
| **Authentification** | Flask-Login | 0.6.3 |
| **Export ICS** | icalendar | 5.0.14 |
| **Gestion des dates** | python-dateutil, pytz | - |
| **Tests** | pytest | 8.3.5 |

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

#### Variables d'environnement recommandées

```bash
# Générer une clé secrète sécurisée
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Pour utiliser une autre base de données (ex: PostgreSQL)
# export SQLALCHEMY_DATABASE_URI='postgresql://user:password@localhost/leviia'
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
> - Un groupe par défaut
> - Les types de shifts par défaut (matin, après-midi, soirée)

### 6. Démarrer l'application

```bash
python run.py
```

L'application sera accessible à l'adresse : **http://localhost:5000**

## 🎯 Utilisation

### Première connexion

1. Connectez-vous avec les identifiants par défaut :
   - Email : `admin@leviia.local`
   - Mot de passe : `admin123`

2. **Changez immédiatement le mot de passe** après la première connexion.

### Gestion des utilisateurs

- Les administrateurs peuvent créer, modifier et supprimer des utilisateurs
- Chaque utilisateur appartient à un groupe
- Les groupes peuvent être inclus ou exclus du planning et des astreintes

### Gestion des shifts

1. Configurez les types de shifts dans l'interface d'administration
2. Attribuez des shifts aux utilisateurs via le calendrier
3. Visualisez le planning par jour, semaine ou mois

### Gestion des astreintes

1. Activez la participation aux astreintes pour les groupes concernés
2. Planifiez les rotations d'astreinte
3. Les utilisateurs sont notifiés de leurs périodes d'astreinte

### Export du planning

- Exportez votre planning personnel au format ICS
- Importez le fichier dans votre application de calendrier préférée
- Les mises à jour du planning sont automatiquement synchronisées

## 📁 Structure du projet

```
leviia-schedule/
├── app/
│   ├── __init__.py          # Initialisation Flask et extensions
│   ├── models.py            # Modèles de la base de données
│   ├── routes/
│   │   ├── __init__.py      # Routes principales
│   │   ├── admin.py         # Routes d'administration
│   │   ├── auth.py          # Routes d'authentification
│   │   ├── export.py        # Export ICS
│   │   └── main.py          # Routes principales
│   └── utils/
│       ├── decorators.py    # Décorateurs personnalisés
│       ├── helpers.py       # Fonctions utilitaires
│       └── ics_exporter.py  # Export ICS
├── config.py                # Configuration de l'application
├── run.py                   # Point d'entrée de l'application
├── requirements.txt         # Dépendances Python
├── instance/                # Fichiers d'instance (base de données)
│   └── app.db               # Base de données SQLite
└── tests/                   # Tests unitaires
```

## 🔧 Configuration avancée

### Utiliser PostgreSQL

1. Installez PostgreSQL et créez une base de données :
   ```bash
   sudo apt-get install postgresql postgresql-contrib
   sudo -u postgres createdb leviia
   sudo -u postgres createuser leviia_user
   ```

2. Modifiez la configuration :
   ```python
   SQLALCHEMY_DATABASE_URI = 'postgresql://leviia_user:password@localhost/leviia'
   ```

3. Installez le driver PostgreSQL :
   ```bash
   pip install psycopg2-binary
   ```

### Désactiver l'authentification (développement uniquement)

Dans `config.py` :
```python
LOGIN_DISABLED = True
```

> ⚠️ **Ne jamais utiliser cette option en production !**

### Configurer le niveau de log

Ajoutez dans `config.py` :
```python
import logging
LOG_LEVEL = logging.DEBUG
```

## 🧪 Tests

> **✅ Statut** : 248 tests - Tous passent - Couverture : 66%

### Exécuter les tests

```bash
pytest tests/
```

### Exécuter les tests avec couverture

```bash
pip install pytest-cov
pytest --cov=app --cov=config tests/
```

### Exécuter un test spécifique

```bash
pytest tests/test_models.py::TestUserModel::test_user_creation -v
```

### Voir le rapport de couverture détaillé

```bash
pytest tests/ --cov=app --cov=config --cov-report=html
# Ouvre htmlcov/index.html dans ton navigateur
```

### Documentation complète

Voir [TESTING_SUMMARY.md](TESTING_SUMMARY.md) pour une documentation détaillée de tous les tests.

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

## 🐛 Signaler un bug

Pour signaler un bug, ouvrez une **Issue** sur GitHub avec les informations suivantes :

- Version de l'application
- Étapes pour reproduire le bug
- Comportement attendu
- Comportement réel
- Captures d'écran (si applicable)
- Logs d'erreur (si applicable)

## 📜 Licence

Ce projet est sous licence **CeCILL v2.1**. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

La licence CeCILL est une licence de logiciel libre conforme au droit français, compatible avec les principes du logiciel libre et open source.

## 🙏 Remerciements

- [Flask](https://flask.palletsprojects.com/) - Framework web léger et puissant
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM Python
- [icalendar](https://github.com/collective/icalendar) - Bibliothèque d'export ICS

## 📞 Contact

Pour toute question ou suggestion, n'hésitez pas à ouvrir une **Issue** ou une **Discussion** sur le dépôt GitHub.

---

## 📌 Notes de version

### Version actuelle (en développement)

- **Statut** : Développement actif
- **Stabilité** : Non recommandé pour la production
- **Fonctionnalités** : Toutes les fonctionnalités de base sont implémentées

### Prochaines étapes

- [ ] Tests complets de toutes les fonctionnalités
- [ ] Documentation utilisateur détaillée
- [ ] Interface utilisateur améliorée
- [ ] Support multi-langues
- [ ] Notifications par email
- [ ] Intégration avec des services externes (Google Calendar API, etc.)
- [ ] Audit de sécurité complet
- [ ] Optimisation des performances

---

> **⚠️ Rappel : Version de développement**
> Ce logiciel est fourni "tel quel", sans garantie d'aucune sorte.
> L'auteur ne peut être tenu responsable de tout dommage direct, indirect,
> accessoire, spécial ou consécutif découlant de l'utilisation de ce logiciel.
> **Utilisez-le à vos propres risques.**
