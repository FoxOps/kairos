# 🎯 **Guide de Chasse au Bug - Leviia Schedule**

*Comment utiliser les outils de chasse au bug pour améliorer la qualité du code*

---

## 🚀 **Démarrage Rapide**

### 1. Installer les dépendances

```bash
# Installer les dépendances du projet
make install

# Installer les outils de chasse au bug (déjà inclus dans requirements.txt)
pip install ruff bandit safety pytest pytest-cov
```

### 2. Exécuter une analyse complète

```bash
# Méthode 1: Utiliser le script principal
./scripts/bug_hunt.sh --full --report

# Méthode 2: Utiliser Makefile
make bug-hunt-full

# Méthode 3: Exécuter manuellement
./scripts/bug_hunt.sh --security --lint --test --duplicate --report
```

### 3. Voir les résultats

Tous les rapports sont générés dans le répertoire `reports/` :
- `bandit-results.json` - Résultats de l'analyse de sécurité
- `safety-results.json` - Vulnérabilités des dépendances
- `ruff-results.json` - Erreurs de linter
- `duplicates-results.txt` - Code dupliqué
- `bug-hunt-report-*.md` - Rapport complet

---

## 🛠️ **Commandes Disponibles**

### **Analyse Complète**

| Commande | Description | Durée |
|----------|-------------|-------|
| `make bug-hunt-full` | Exécute tous les checks | ~5-10 min |
| `./scripts/bug_hunt.sh --full` | Idem, avec plus d'options | ~5-10 min |
| `make all` | Tests + Linting + Formatage + Sécurité | ~5 min |

### **Analyse par Catégorie**

#### **Sécurité**
```bash
# Analyse complète de sécurité
make bug-hunt-security
./scripts/bug_hunt.sh --security

# Bandit uniquement (analyse statique du code)
bandit -r app/ -f json -o reports/bandit-results.json

# Safety uniquement (vulnérabilités des dépendances)
safety check --json --output reports/safety-results.json
```

#### **Qualité du Code**
```bash
# Vérification du linter
make bug-hunt-lint
./scripts/bug_hunt.sh --lint
ruff check app/ --output-file=reports/ruff-results.json

# Vérification du formatage
make format
black --check . --exclude=".git|__pycache__|instance|venv"

# Correction du formatage
make format-fix
black . --exclude=".git|__pycache__|instance|venv"
```

#### **Tests**
```bash
# Exécuter tous les tests
make bug-hunt-tests
./scripts/bug_hunt.sh --test
python -m pytest tests/ -v --tb=short

# Tests avec couverture
make test-coverage
python -m pytest tests/ --cov=app --cov=config --cov-report=html

# Tests rapides
make test-quick
python -m pytest tests/ --tb=no -q
```

#### **Code Dupliqué**
```bash
# Recherche de code dupliqué
make bug-hunt-duplicates
./scripts/bug_hunt.sh --duplicate
python scripts/find_duplicates.py --check-imports

# Recherche complète (inclut code similaire)
python scripts/find_duplicates.py --check-imports --check-similar
```

### **Analyse Rapide**

```bash
# Sécurité + Linter (rapide)
make bug-hunt-quick
./scripts/bug_hunt.sh --quick

# Générer un rapport
make bug-hunt-report
./scripts/bug_hunt.sh --full --report
```

---

## 📊 **Interprétation des Résultats**

### **Score Global**

Le script `bug_hunt.sh` calcule un score global basé sur :

| Critère | Poids | Impact sur le Score |
|---------|--------|---------------------|
| Sécurité (Bandit) | 40% | -10 points par problème |
| Sécurité (Safety) | 40% | -10 points par vulnérabilité |
| Linter (Ruff) | 30% | -15 points si erreurs |
| Tests | 20% | -20 points si échecs |
| Code Dupliqué | 10% | -10 points si duplications |

**Score :**
- 90-100 : A ✅ Excellent
- 80-89 : B ✅ Bon
- 70-79 : C ⚠️ Moyen
- 60-69 : D ⚠️ À améliorer
- 0-59 : F ❌ Critique

### **Niveaux de Sévérité**

| Niveau | Couleur | Description | Action |
|--------|---------|-------------|--------|
| 🔴 Critique | Rouge | Problèmes bloquants | Corriger IMMEDIATEMENT |
| 🟡 Moyen | Jaune | Problèmes importants | Corriger rapidement |
| 🟢 Faible | Vert | Problèmes mineurs | Corriger si possible |

---

## 🎯 **Correction des Problèmes**

### **1. Code Dupliqué**

#### **Problème :** Fonctions `_make_cache_key` dupliquées

**Fichiers :**
- `app/utils/cache.py:732`
- `app/utils/optimizations.py:125, 218`

**Solution :**
```python
# Créer un nouveau fichier : app/utils/cache_helpers.py

def make_cache_key(f: Callable, args: tuple, kwargs: dict, 
                  key_prefix: str = '', vary_on: Optional[list] = None) -> str:
    """Fonction unifiée pour générer des clés de cache."""
    import hashlib
    from flask import current_app
    from flask_login import current_user
    
    key_parts = [f.__module__, f.__name__]
    
    if key_prefix:
        key_parts.insert(0, key_prefix)
    
    if vary_on:
        for arg_name in vary_on:
            if arg_name in kwargs:
                key_parts.append(str(kwargs[arg_name]))
    else:
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        key_parts.append(f"user_id={current_user.id}")
    
    key_string = ':'.join(key_parts)
    return hashlib.sha256(key_string.encode('utf-8')).hexdigest()
```

**Puis remplacer dans tous les fichiers :**
```python
# Avant
from app.utils.cache import _make_cache_key

# Après
from app.utils.cache_helpers import make_cache_key
```

#### **Problème :** Fonctions `get_bool` et `get_int` dupliquées

**Fichiers :** 4 fichiers différents

**Solution :**
```python
# Créer : app/utils/env_helpers.py

def get_bool(env_var: str, default: bool = False) -> bool:
    """Récupère une variable d'environnement booléenne."""
    import os
    value = os.environ.get(env_var, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')

def get_int(env_var: str, default: int = 0) -> int:
    """Récupère une variable d'environnement entière."""
    import os
    try:
        return int(os.environ.get(env_var, str(default)))
    except ValueError:
        return default
```

### **2. Problèmes de Sécurité**

#### **Problème :** Clé secrète par défaut faible

**Fichier :** `config.py`

**Solution :**
```python
# Avant
SECRET_KEY = os.environ.get("SECRET_KEY") or "ta-cle-secrete-ici"

# Après
import secrets
SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
```

#### **Problème :** CSRF désactivé

**Fichier :** `config.py`

**Solution :**
```python
# Dans ProductionConfig
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = 3600  # 1 heure
```

#### **Problème :** Authentification désactivable

**Fichier :** `config.py`

**Solution :**
```python
# Supprimer ou commenter
# LOGIN_DISABLED = get_bool_from_env("LOGIN_DISABLED", False)
```

### **3. Erreurs de Linter**

#### **Problème :** Imports non utilisés

**Fichier :** `app/__init__.py`

**Solution :**
```python
# Avant
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import time
import sqlite3
import logging
from logging.handlers import RotatingFileHandler, SysLogHandler
import os
import traceback
import re
from datetime import datetime

# Après
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import logging
import os
```

#### **Problème :** Guillemets simples

**Solution :** Remplacer tous les guillemets simples par des guillemets doubles :
```bash
# Utiliser un script de remplacement
find app/ -name "*.py" -exec sed -i 's/'\''/"/g' {} \;
# Puis corriger manuellement les cas où les guillemets simples sont nécessaires
```

### **4. Tests Échoués**

#### **Problème :** Fonction `create_app` manquante

**Fichier :** `app/__init__.py`

**Solution :**
```python
# Ajouter à la fin de app/__init__.py
def create_app(config_object="config.Config"):
    """Factory function to create and configure the Flask app."""
    app = Flask(__name__)
    app.config.from_object(config_object)
    
    # Initialiser les extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    # Initialiser le cache
    init_cache(app)
    
    # Importer les routes
    from app.routes import main, admin, export, auth
    app.register_blueprint(main.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(export.bp)
    app.register_blueprint(auth.bp)
    
    return app
```

---

## 📈 **Bonnes Pratiques**

### **1. Écrire du Code Maintenable**

✅ **À faire :**
- Utiliser des noms de fonctions et variables clairs
- Commenter le code complexe
- Éviter le code dupliqué (principe DRY)
- Garder les fonctions courtes (< 50 lignes)

❌ **À éviter :**
- Code dupliqué
- Fonctions trop longues
- Commentaires inutiles
- Noms de variables ambiguës

### **2. Sécurité**

✅ **À faire :**
- Toujours valider les entrées utilisateur
- Utiliser des mots de passe forts
- Chiffrer les données sensibles
- Limiter les permissions

❌ **À éviter :**
- Mots de passe en clair
- Clés secrètes dans le code
- Confiance aveugle dans les entrées utilisateur
- Désactivation des protections de sécurité

### **3. Tests**

✅ **À faire :**
- Tester les cas positifs et négatifs
- Tester les cas limites
- Maintenir une bonne couverture (> 80%)
- Exécuter les tests régulièrement

❌ **À éviter :**
- Tests qui dépendent de l'ordre d'exécution
- Tests trop lents
- Tests qui ne testent rien

---

## 🔧 **Automatisation**

### **1. Intégration Continue (CI)**

Créer un fichier `.github/workflows/bug-hunt.yml` :

```yaml
name: Bug Hunt

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  bug-hunt:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run Bug Hunt
      run: |
        ./scripts/bug_hunt.sh --full --report
    
    - name: Upload reports
      uses: actions/upload-artifact@v3
      with:
        name: bug-hunt-reports
        path: reports/
```

### **2. Pré-commit Hooks**

Créer un fichier `.pre-commit-config.yaml` :

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.18
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
  
  - repo: https://github.com/psf/black-pre-commit
    rev: 26.5.1
    hooks:
      - id: black
        language_version: python3.12
  
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

Installer les hooks :
```bash
pip install pre-commit
pre-commit install
```

---

## 📚 **Ressources**

### **Documentation**
- [Rapport Complet de Chasse au Bug](BUG_HUNT_REPORT.md)
- [Résumé de la Chasse au Bug](BUG_HUNT_SUMMARY.md)
- [Rapport d'Audit de Sécurité](SECURITY_AUDIT_REPORT.md)
- [Résumé des Tests](TESTING_SUMMARY.md)

### **Outils**
- [Ruff](https://docs.astral.sh/ruff/) - Linter rapide
- [Bandit](https://bandit.readthedocs.io/) - Analyse de sécurité
- [Safety](https://getsafety.com/) - Vulnérabilités des dépendances
- [pytest](https://docs.pytest.org/) - Framework de test
- [Black](https://black.readthedocs.io/) - Formateur de code

### **Bonnes Pratiques**
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
- [Python Security](https://wiki.python.org/moin/Security)
- [12 Factor App](https://12factor.net/)

---

## 🎉 **Checklist de Chasse au Bug**

- [ ] Exécuter `make bug-hunt-full`
- [ ] Corriger les problèmes critiques (🔴)
- [ ] Corriger les problèmes moyens (🟡)
- [ ] Corriger les problèmes mineurs (🟢)
- [ ] Vérifier que tous les tests passent
- [ ] Atteindre 80%+ de couverture
- [ ] Exécuter un nouvel audit de sécurité
- [ ] Documenter les corrections
- [ ] Mettre à jour le rapport de chasse au bug

---

*"La qualité du code est la responsabilité de tous." - Kent Beck*

*Guide généré automatiquement par Vibe Code - Agent de Chasse au Bug*
