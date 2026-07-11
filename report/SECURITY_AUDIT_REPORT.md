# 🔒 Rapport d'Audit de Sécurité - Leviia Schedule

**Date :** 23 juin 2026  
**Version :** 1.0  
**Auditeur :** Vibe Code (Agent d'Audit de Sécurité)  
**Projet :** [FoxOps/leviia-schedule](https://github.com/FoxOps/leviia-schedule)  

---

## 📋 Sommaire

1. [Introduction](#1-introduction)
2. [Méthodologie](#2-méthodologie)
3. [Vulnérabilités des Dépendances](#3-vulnérabilités-des-dépendances)
4. [Analyse du Code Source](#4-analyse-du-code-source)
5. [Problèmes de Sécurité Identifiés](#5-problèmes-de-sécurité-identifiés)
6. [Recommandations](#6-recommandations)
7. [Conclusion](#7-conclusion)

---

## 1. Introduction

Ce rapport présente les résultats de l'audit de sécurité complet réalisé sur l'application **Leviia Schedule**, une application web de gestion des plannings et des astreintes.

L'objectif de cet audit est d'identifier les vulnérabilités potentielles, les risques de sécurité et les bonnes pratiques à améliorer pour garantir la sécurité de l'application en environnement de production.

> ⚠️ **Note importante :** L'application est actuellement en phase de développement actif et n'est pas recommandée pour une utilisation en production sans une revue complète et des tests approfondis.

---

## 2. Méthodologie

L'audit a été réalisé en utilisant les outils et méthodes suivants :

### Outils utilisés
- **Safety** (v3.8.1) : Analyse des vulnérabilités des dépendances Python
- **Bandit** (v1.9.4) : Analyse statique du code source pour détecter les problèmes de sécurité
- **Analyse manuelle** : Revue du code source, de la configuration et de l'architecture

### Périmètre de l'audit
- ✅ Analyse des dépendances (requirements.txt)
- ✅ Analyse du code source (app/, config.py, run.py)
- ✅ Revue de la configuration de sécurité
- ✅ Vérification des bonnes pratiques de développement
- ❌ Tests d'intrusion (non réalisés - hors scope)
- ❌ Audit des dépendances transitives (partiellement couvert)

---

## 3. Vulnérabilités des Dépendances

### 3.1 Résultats de Safety

**7 vulnérabilités identifiées** dans 2 packages :

#### 🔴 **Critique - cryptography (v46.0.3)**

| ID | CVE | Severity | Description | Solution |
|----|-----|----------|-------------|----------|
| SFTY-20260327-04621 | CVE-2026-34073 | High | Validation de certificat incorrecte due à une application incomplète des contraintes de nom DNS sur les noms de pairs | **Mettre à jour vers cryptography >= 46.0.6** |
| SFTY-20260408-76846 | CVE-2026-39892 | High | Buffer Overflow dû à une mauvaise gestion des buffers non contigus | **Mettre à jour vers cryptography >= 46.0.7** |
| 86217 | CVE-2026-26007 | High | Problème de sécurité non spécifié | **Mettre à jour vers cryptography >= 46.0.5** |

**Impact :** 
- Risque d'accès non autorisé via des certificats malveillants
- Exécution de code arbitraire possible via buffer overflow
- Attaques par déni de service

**Recommandation :** 
```bash
pip install --upgrade cryptography>=46.0.7
```

#### 🟡 **Moyen - pip (v25.0.1)**

| ID | CVE | Severity | Description | Solution |
|----|-----|----------|-------------|----------|
| 85681 | CVE-2026-1703 | Medium | Vulnérabilité non spécifiée | **Mettre à jour vers pip >= 26.0** |
| SFTY-20260420-60812 | CVE-2026-3219 | Medium | Vulnérabilité non spécifiée | **Mettre à jour vers pip >= 26.0.1** |
| SFTY-20260427-69629 | CVE-2026-6357 | Medium | Inclusion de fonctionnalité depuis une sphère de contrôle non fiable | **Mettre à jour vers pip >= 26.1** |

**Recommandation :** 
```bash
pip install --upgrade pip>=26.1
```

### 3.2 Analyse des dépendances

**Problème identifié dans requirements.txt :**
```python
cryptography>=49.0.0  # Commenté dans le fichier
# Note: Si vous utilisez mistral-vibe, vérifiez la compatibilité car mistral-vibe 2.9.3
#       nécessite cryptography<=46.0.3
```

**Recommandation :** 
- Supprimer le commentaire et appliquer la contrainte `cryptography>=49.0.0`
- Vérifier la compatibilité avec mistral-vibe et mettre à jour si nécessaire
- **Action immédiate :** Mettre à jour cryptography vers la dernière version stable

---

## 4. Analyse du Code Source

### 4.1 Résultats de Bandit

**3 problèmes de sécurité identifiés :**

| Fichier | Ligne | Test ID | Severity | Confidence | Description |
|--------|-------|---------|----------|------------|-------------|
| `app/utils/cache.py` | 755 | B324 | HIGH | HIGH | Utilisation de MD5 pour la sécurité |
| `app/utils/optimizations.py` | 156 | B324 | HIGH | HIGH | Utilisation de MD5 pour la sécurité |
| `app/utils/optimizations.py` | 231 | B324 | HIGH | HIGH | Utilisation de MD5 pour la sécurité |

#### 🔴 **Problème : Utilisation de MD5 pour le hachage**

**Code problématique :**
```python
# app/utils/cache.py:755
return hashlib.md5(key_string.encode('utf-8')).hexdigest()

# app/utils/optimizations.py:156, 231
return hashlib.md5(key_string.encode('utf-8')).hexdigest()
```

**Risque :** 
- MD5 est considéré comme cryptographiquement cassé depuis 2004
- Vulnérable aux attaques par collision
- Ne doit **jamais** être utilisé pour des fins de sécurité (authentification, intégrité, etc.)

**Contexte :**
Dans ce cas précis, MD5 est utilisé pour **générer des clés de cache** et non pour des fins de sécurité critiques. Cependant, Bandit signale cela comme un problème car :
1. Cela pourrait être mal interprété comme une utilisation sécurisée
2. Cela pourrait être réutilisé à mauvais escient dans le futur
3. C'est une mauvaise pratique générale

**Recommandation :** 
- Remplacer MD5 par SHA-256 pour la génération des clés de cache
- Ajouter un commentaire explicite indiquant que ce n'est pas pour la sécurité
- Ou utiliser `usedforsecurity=False` dans le contexte Bandit

**Code corrigé :**
```python
# Utilisation de SHA-256 pour la génération de clés de cache (non-sécurisé)
return hashlib.sha256(key_string.encode('utf-8')).hexdigest()
```

### 4.2 Analyse manuelle du code

#### ✅ **Bonnes pratiques identifiées**

1. **Authentification sécurisée**
   - Utilisation de Flask-Login avec gestion des sessions
   - Hashage des mots de passe avec `werkzeug.security.generate_password_hash`
   - Utilisation de `secrets.token_urlsafe()` pour générer les tokens ICS
   - ✅ **Bonne pratique**

2. **Protection des mots de passe**
   - Les mots de passe sont hashés avant stockage
   - Vérification avec `check_password_hash`
   - ✅ **Bonne pratique**

3. **Gestion des erreurs**
   - Pages d'erreur personnalisées (400, 401, 403, 404, 405, 500, etc.)
   - Logging complet des erreurs
   - ✅ **Bonne pratique**

4. **Filtrage des données sensibles dans les logs**
   - Implémentation d'un `SensitiveDataFilter` pour masquer mots de passe, tokens, etc.
   - Configuration activable via `LOG_FILTER_SENSITIVE`
   - ✅ **Excellente pratique**

5. **Protection contre les verrouillages SQLite**
   - Mécanisme de retry pour les erreurs "database is locked"
   - Configuration du pool de connexions
   - ✅ **Bonne pratique**

6. **Export ICS sécurisé**
   - Authentification par token unique
   - Tokens générés avec `secrets.token_urlsafe(32)`
   - Vérification de l'authentification avant export
   - ✅ **Bonne pratique**

#### ⚠️ **Problèmes potentiels identifiés**

1. **🔴 CSRF désactivé**
   - `WTF_CSRF_ENABLED = False` dans TestingConfig
   - **Risque :** Attaques CSRF possibles sur les formulaires
   - **Recommandation :** Activer CSRF en production

2. **🟡 Clé secrète par défaut non sécurisée**
   - `SECRET_KEY = os.environ.get("SECRET_KEY") or "ta-cle-secrete-ici"`
   - **Risque :** Si la variable d'environnement n'est pas définie, une clé faible est utilisée
   - **Recommandation :** Générer une clé sécurisée par défaut

3. **🟡 Authentification désactivable**
   - `LOGIN_DISABLED = get_bool_from_env("LOGIN_DISABLED", False)`
   - **Risque :** Possibilité de désactiver complètement l'authentification
   - **Recommandation :** Supprimer cette option ou la restreindre au développement uniquement

4. **🟡 Mot de passe admin par défaut faible**
   - `DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD") or "admin123"`
   - **Risque :** Mot de passe faible par défaut
   - **Recommandation :** Générer un mot de passe aléatoire par défaut

5. **🟡 Pas de protection contre les attaques par force brute**
   - Aucune limitation du nombre de tentatives de connexion
   - **Risque :** Attaques par force brute possibles
   - **Recommandation :** Implémenter un mécanisme de rate limiting

6. **🟡 Pas de configuration de sécurité HTTP**
   - Aucune configuration pour :
     - `SESSION_COOKIE_SECURE`
     - `SESSION_COOKIE_HTTPONLY`
     - `SESSION_COOKIE_SAMESITE`
     - `REMEMBER_COOKIE_SECURE`
     - En-têtes de sécurité (CSP, HSTS, X-Frame-Options, etc.)
   - **Risque :** Vulnérabilités XSS, CSRF, Clickjacking
   - **Recommandation :** Configurer les en-têtes de sécurité

7. **🟡 CORS potentiellement activable sans restriction**
   - `CORS_ENABLED = get_bool_from_env("CORS_ENABLED", False)`
   - **Risque :** Si activé sans configuration appropriée, accès non autorisé
   - **Recommandation :** Configurer CORS avec des origines spécifiques

8. **🟡 Pas de validation d'entrée stricte**
   - Certaines routes acceptent des paramètres sans validation
   - **Risque :** Injection SQL (bien que SQLAlchemy protège partiellement)
   - **Recommandation :** Valider et sanitizer toutes les entrées utilisateur

9. **🟡 Export ICS accessible via token**
   - Les tokens ICS permettent un accès sans authentification
   - **Risque :** Si un token est compromis, accès non autorisé aux données
   - **Recommandation :** 
     - Limiter la durée de validité des tokens
     - Permettre la révocation des tokens
     - Logger les accès via token

10. **🟡 Pas de chiffrement des données sensibles**
    - Les tokens ICS et mots de passe hashés sont stockés en clair dans la base
    - **Risque :** Si la base est compromise, accès aux données
    - **Recommandation :** Chiffrer les données sensibles

---

## 5. Problèmes de Sécurité Identifiés

### 🔴 **Critique (Priorité 1)**

| ID | Titre | Risque | Impact | Solution |
|----|-------|-------|--------|----------|
| SEC-001 | Vulnérabilités dans cryptography | Élevé | Accès non autorisé, Exécution de code | Mettre à jour cryptography >= 46.0.7 |
| SEC-002 | Utilisation de MD5 pour le hachage | Moyen | Mauvaise pratique, risque futur | Remplacer par SHA-256 |

### 🟡 **Moyen (Priorité 2)**

| ID | Titre | Risque | Impact | Solution |
|----|-------|-------|--------|----------|
| SEC-003 | CSRF désactivé | Moyen | Attaques CSRF | Activer WTF_CSRF_ENABLED |
| SEC-004 | Clé secrète par défaut faible | Moyen | Session hijacking | Générer une clé sécurisée |
| SEC-005 | Authentification désactivable | Moyen | Accès non autorisé | Supprimer l'option |
| SEC-006 | Mot de passe admin par défaut faible | Moyen | Accès admin non autorisé | Générer un mot de passe aléatoire |
| SEC-007 | Pas de rate limiting | Moyen | Force brute | Implémenter Flask-Limiter |
| SEC-008 | Pas d'en-têtes de sécurité | Moyen | XSS, Clickjacking | Configurer les en-têtes |
| SEC-009 | CORS non configuré | Moyen | Accès non autorisé | Configurer CORS |
| SEC-010 | Tokens ICS persistants | Moyen | Accès non autorisé | Limiter la durée de validité |

### 🟢 **Faible (Priorité 3)**

| ID | Titre | Risque | Impact | Solution |
|----|-------|-------|--------|----------|
| SEC-011 | Pas de validation d'entrée stricte | Faible | Injection SQL | Valider toutes les entrées |
| SEC-012 | Pas de chiffrement des données | Faible | Fuite de données | Chiffrer les données sensibles |

---

## 6. Recommandations

### 6.1 Recommandations Immédiates (À appliquer avant la production)

#### 1. Mettre à jour les dépendances vulnérables
```bash
# Mettre à jour cryptography
pip install --upgrade cryptography>=46.0.7

# Mettre à jour pip
pip install --upgrade pip>=26.1

# Mettre à jour requirements.txt
# Remplacer la ligne commentée par :
cryptography>=49.0.0
```

#### 2. Corriger les problèmes de hachage MD5
**Fichiers à modifier :**
- `app/utils/cache.py` (ligne 755)
- `app/utils/optimizations.py` (lignes 156, 231)

**Code corrigé :**
```python
# Remplacer :
return hashlib.md5(key_string.encode('utf-8')).hexdigest()

# Par :
return hashlib.sha256(key_string.encode('utf-8')).hexdigest()
```

#### 3. Configurer les en-têtes de sécurité
Ajouter dans `config.py` (ProductionConfig) :
```python
class ProductionConfig(Config):
    # ...
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
```

#### 4. Activer la protection CSRF
Dans `config.py` :
```python
class ProductionConfig(Config):
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 heure
```

#### 5. Générer une clé secrète sécurisée par défaut
Dans `config.py` :
```python
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
```

#### 6. Supprimer l'option de désactivation de l'authentification
Dans `config.py` :
```python
# Supprimer ou commenter :
# LOGIN_DISABLED = get_bool_from_env("LOGIN_DISABLED", False)
```

#### 7. Générer un mot de passe admin aléatoire par défaut
Dans `config.py` :
```python
class DefaultDataConfig:
    DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD") or secrets.token_urlsafe(16)
```

#### 8. Implémenter le rate limiting
Installer Flask-Limiter :
```bash
pip install flask-limiter
```

Configurer dans `app/__init__.py` :
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Appliquer aux routes sensibles
@limiter.limit("5 per minute")
@app.route("/login", methods=["POST"])
def login():
    # ...
```

#### 9. Configurer les en-têtes de sécurité HTTP
Installer Flask-Talisman :
```bash
pip install flask-talisman
```

Configurer dans `app/__init__.py` :
```python
from flask_talisman import Talisman

Talisman(
    app,
    force_https=True,
    strict_transport_security=True,
    session_cookie_secure=True,
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", "data:"],
        'font-src': ["'self'"],
        'connect-src': ["'self'"],
        'frame-ancestors': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
    },
    content_security_policy_nonce_in=['script-src']
)
```

#### 10. Limiter la durée de validité des tokens ICS
Dans `config.py` :
```python
class DefaultDataConfig:
    ICS_TOKEN_EXPIRY_DAYS = get_int_from_env("ICS_TOKEN_EXPIRY_DAYS", 30)  # 30 jours au lieu de 365
```

Ajouter un champ `expires_at` dans le modèle User et vérifier l'expiration.

### 6.2 Recommandations à Moyen Terme

#### 1. Implémenter un système de rotation des tokens
- Permettre aux utilisateurs de régénérer leurs tokens ICS
- Invalider les anciens tokens
- Logger les accès via token

#### 2. Chiffrer les données sensibles
- Chiffrer les tokens ICS dans la base de données
- Utiliser Fernet ou un autre système de chiffrement

#### 3. Implémenter la validation d'entrée
- Utiliser WTForms ou un système similaire
- Valider tous les paramètres de requête
- Sanitizer les entrées avant utilisation

#### 4. Configurer CORS de manière sécurisée
```python
from flask_cors import CORS

CORS(app, resources={
    r"/api/*": {
        "origins": ["https://votre-domaine.com"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

#### 5. Implémenter l'authentification à deux facteurs (2FA)
- Utiliser Flask-2FA ou un système similaire
- Rendre obligatoire pour les administrateurs

#### 6. Mettre en place un système de monitoring
- Surveiller les tentatives de connexion échouées
- Détecter les attaques par force brute
- Alerter en cas d'activité suspecte

### 6.3 Recommandations à Long Terme

#### 1. Migration vers PostgreSQL
- SQLite n'est pas adapté pour la production
- PostgreSQL offre une meilleure sécurité et scalabilité

#### 2. Implémenter un système de backup sécurisé
- Backups automatiques et chiffrés
- Stockage hors site
- Tests de restauration réguliers

#### 3. Audit de sécurité régulier
- Exécuter Safety et Bandit régulièrement
- Mettre à jour les dépendances
- Revue du code par des experts en sécurité

#### 4. Tests de pénétration
- Réaliser des tests d'intrusion réguliers
- Identifier les vulnérabilités avant les attaquants

---

## 7. Conclusion

### 7.1 Résumé des Findings

| Catégorie | Critique | Moyen | Faible | Total |
|----------|----------|-------|-------|-------|
| Dépendances | 3 | 0 | 0 | 3 |
| Code Source | 1 | 9 | 2 | 12 |
| **Total** | **4** | **9** | **2** | **15** |

### 7.2 Niveau de Risque Global

**🟡 MOYEN**

L'application présente des vulnérabilités significatives qui doivent être corrigées avant une mise en production. Cependant, aucune vulnérabilité critique exploitable directement n'a été identifiée.

### 7.3 Recommandation Finale

**❌ NE PAS METTRE EN PRODUCTION dans l'état actuel**

L'application nécessite les corrections suivantes avant toute mise en production :

1. ✅ Mettre à jour toutes les dépendances vulnérables
2. ✅ Corriger les problèmes de hachage MD5
3. ✅ Configurer les en-têtes de sécurité
4. ✅ Activer la protection CSRF
5. ✅ Générer des clés et mots de passe sécurisés par défaut
6. ✅ Implémenter le rate limiting
7. ✅ Limiter la durée de validité des tokens

Une fois ces corrections appliquées, un nouvel audit devrait être réalisé pour valider la sécurité de l'application.

### 7.4 Prochaines Étapes

1. **Corriger les problèmes critiques** (Priorité 1)
2. **Appliquer les recommandations immédiates** (Priorité 2)
3. **Planifier les améliorations à moyen terme** (Priorité 3)
4. **Réaliser un nouvel audit** après les corrections
5. **Mettre en place un processus de sécurité continu**

---

## 📞 Contact

Pour toute question ou clarification concernant ce rapport, veuillez contacter l'équipe de développement ou ouvrir une issue sur le dépôt GitHub.

---

## 📄 Annexes

### Annexe A : Commandes pour reproduire l'audit

```bash
# Installer les outils de sécurité
pip install safety bandit

# Exécuter Safety
safety check --full-report

# Exécuter Bandit
bandit -r app/ -f json -o bandit-results.json

# Exécuter tous les tests de sécurité
make security
```

### Annexe B : Références

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Safety Documentation](https://getsafety.com/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
- [Python Security](https://wiki.python.org/moin/Security)

---

**Fin du Rapport**  
*Généré automatiquement par Vibe Code - Agent d'Audit de Sécurité*
