# 🛡️ Guide Administrateur - Leviia Schedule

> **Version** : 1.1.0 | **Dernière mise à jour** : Juillet 2026
> **Public** : Administrateurs Leviia Schedule uniquement

---

## 📋 Table des Matières

1. [🎯 Rôle de l'Administrateur](#-rôle-de-ladministrateur)
2. [🔐 Gestion de la Sécurité](#-gestion-de-la-sécurité)
3. [👥 Gestion Avancée des Utilisateurs](#-gestion-avancée-des-utilisateurs)
4. [🏢 Architecture des Groupes](#-architecture-des-groupes)
5. [⚙️ Configuration des Types de Shifts](#️-configuration-des-types-de-shifts)
6. [📊 Tableau de Bord et Statistiques](#-tableau-de-bord-et-statistiques)
7. [⚡ Automatisation Complète](#-automatisation-complète)
8. [🔧 Configuration Technique](#-configuration-technique)
9. [📤 Export et Intégrations](#-export-et-intégrations)
10. [🎨 Personnalisation](#-personnalisation)
11. [🔄 Maintenance et Sauvegardes](#-maintenance-et-sauvegardes)
12. [🚨 Gestion des Erreurs](#-gestion-des-erreurs)

---

## 🎯 Rôle de l'Administrateur

### Responsabilités

En tant qu'administrateur Leviia Schedule, vous êtes responsable de :

- ✅ **Gestion des utilisateurs** : Création, modification, suppression
- ✅ **Configuration des groupes** : Organisation et permissions
- ✅ **Paramétrage des shifts** : Types de shifts et règles métiers
- ✅ **Planification** : Shifts, astreintes, congés
- ✅ **Automatisation** : Configuration et supervision
- ✅ **Sécurité** : Gestion des accès et des permissions
- ✅ **Maintenance** : Sauvegardes et mises à jour

### Bonnes Pratiques

1. **Sécurité** : Changez toujours le mot de passe par défaut
2. **Sauvegardes** : Effectuez des sauvegardes régulières de la base de données
3. **Tests** : Testez les modifications dans un environnement de développement
4. **Documentation** : Documentez les configurations spécifiques
5. **Audit** : Vérifiez régulièrement les logs et les activités

---

## 🔐 Gestion de la Sécurité

### Sécurité des Comptes

#### Mot de passe par défaut

**⚠️ CRITIQUE** : Le compte administrateur par défaut a les identifiants :
- Email : `DEFAULT_ADMIN_EMAIL` (`.env`), `admin@leviia.local` par défaut
- Mot de passe : `DEFAULT_ADMIN_PASSWORD` (`.env`), `admin123` par défaut

**Action immédiate** : Changez ce mot de passe dès la première connexion.
En production, définissez `DEFAULT_ADMIN_PASSWORD` à une valeur forte
avant le tout premier démarrage plutôt que de compter sur le
changement post-installation.

#### Politique de mots de passe

Recommandations :
- Minimum 12 caractères
- Mélange de majuscules, minuscules, chiffres et symboles
- Pas de mots du dictionnaire
- Unique pour chaque utilisateur

#### Réinitialisation des mots de passe

Pour réinitialiser le mot de passe d'un utilisateur :

1. Allez dans **Admin** > **Utilisateurs**
2. Cliquez sur **Modifier** pour l'utilisateur concerné
3. Entrez un nouveau mot de passe dans le champ **Mot de passe**
4. **Enregistrer**

> 💡 **Astuce** : Vous pouvez laisser le champ vide pour conserver le mot de passe actuel.

### Gestion des Permissions

#### Rôles

| Rôle | Accès |
|------|--------|
| **Administrateur** | Accès complet à toutes les fonctionnalités |
| **Utilisateur** | Accès limité à son propre planning et congés |

#### Permissions par groupe

| Permission | Description |
|------------|-------------|
| **Participe au planning** | Les membres peuvent avoir des shifts attribués |
| **Participe aux astreintes** | Les membres peuvent être en astreinte |

### Sécurité de l'Application

#### Variables d'environnement sensibles

| Variable | Sensibilité | Recommandation |
|----------|-------------|----------------|
| `SECRET_KEY` | ⭐⭐⭐⭐⭐ CRITIQUE | Générer une clé aléatoire de 32 octets |
| `DATABASE_URL` | ⭐⭐⭐⭐ Élevée | Utiliser des identifiants DB sécurisés |
| `LOGIN_DISABLED` | ⭐⭐⭐ Moyenne | Ne JAMAIS activer en production |

#### Générer une clé secrète sécurisée

```bash
# Méthode 1 : Python
python -c "import secrets; print(secrets.token_hex(32))"

# Méthode 2 : OpenSSL
openssl rand -hex 32
```

#### Désactiver l'authentification (DÉVELOPPEMENT UNIQUEMENT)

Dans `.env` :
```bash
LOGIN_DISABLED=true
```

> ⚠️ **DANGER** : Ne jamais utiliser cette option en production !

#### Protection CSRF

Active sur toute l'application depuis la Phase 4 (`Flask-WTF`
`CSRFProtect`) — rien à configurer côté admin, mais bon à savoir si vous
scriptez des appels vers l'application (import en masse, intégration
tierce) : toute requête POST/PUT/PATCH/DELETE sans jeton CSRF valide est
rejetée avec `400 Bad Request`. Voir
[`api/API.md`](../api/API.md#authentification) pour la marche à suivre
côté script.

#### En-têtes de sécurité HTTP (Talisman)

`Flask-Talisman` (X-Content-Type-Options, X-Frame-Options, etc.) n'est
activé que si `TALISMAN_FORCE_HTTPS=true` dans `.env` — pertinent
uniquement derrière un reverse proxy TLS (voir
[`deployment/DEPLOYMENT_GUIDE.md`](../deployment/DEPLOYMENT_GUIDE.md)).
Laissé désactivé par défaut pour ne pas casser un accès HTTP simple en
développement.

### Configuration SSO/OIDC

Leviia Schedule supporte l'authentification via un fournisseur OIDC
(Keycloak, Okta, Auth0, ou tout fournisseur OpenID Connect standard),
en complément ou à la place de l'authentification par mot de passe.

#### Activer OIDC

Dans `.env` :

```bash
OIDC_ENABLED=true
OIDC_ISSUER=https://votre-fournisseur.com/realms/votre-realm
OIDC_CLIENT_ID=votre-client-id
OIDC_CLIENT_SECRET=votre-client-secret
OIDC_REDIRECT_URI=http://localhost:5000/oidc/callback
```

Côté fournisseur OIDC, enregistrez `OIDC_REDIRECT_URI` comme URL de
callback autorisée pour le client.

#### Désactiver l'authentification par mot de passe

Pour forcer tous les utilisateurs à passer par SSO (masque le
formulaire email/mot de passe, `/login` redirige directement vers
`/oidc/login`) :

```bash
OIDC_DISABLE_BASIC_AUTH=true
```

> ⚠️ Assurez-vous que la connexion OIDC fonctionne avant d'activer cette
> option — sans authentification basique de secours, un problème de
> configuration OIDC bloquerait tous les accès, y compris le vôtre.

#### Déconnexion complète (RP-initiated logout)

Sans configuration supplémentaire, `/logout` ne termine que la session
locale : la session côté fournisseur OIDC reste active, donc la
prochaine visite de `/login` ré-authentifie silencieusement via SSO.
Pour une déconnexion complète, enregistrez une URL de redirection
post-déconnexion côté fournisseur (ex. `PostLogoutRedirectUris` sur
Keycloak) puis :

```bash
OIDC_POST_LOGOUT_REDIRECT_URI=http://localhost:5000
```

#### Mapper les claims du token

Si les noms de claims de votre fournisseur diffèrent des noms standards :

```bash
OIDC_EMAIL_CLAIM=email
OIDC_NAME_CLAIM=name
OIDC_USERNAME_CLAIM=preferred_username
OIDC_GROUPS_CLAIM=          # optionnel, synchronise les groupes locaux
OIDC_ROLES_CLAIM=           # optionnel, synchronise is_admin
```

#### Déploiement Docker : issuer interne vs. externe

Si le fournisseur OIDC et l'application tournent tous deux dans Docker
(ex. Keycloak sur le même réseau que le conteneur Leviia Schedule),
l'URL joignable par le conteneur (`http://keycloak:8080/realms/...`)
diffère souvent de l'URL joignable par le navigateur de l'utilisateur
(`https://auth.exemple.com/realms/...`). Dans ce cas, définissez
`OIDC_INTERNAL_ISSUER` avec l'URL joignable par le conteneur ;
`OIDC_ISSUER` reste l'URL publique utilisée pour les redirections
navigateur (authorization/logout endpoints).

Liste complète des variables OIDC :
[`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md).
Détail du flux de connexion :
[`architecture/SEQUENCE_DIAGRAMS.md`](../architecture/SEQUENCE_DIAGRAMS.md#connexion-oidcsso).

### Audit et Journalisation

#### Historique des modifications (audit trail)

Depuis la version 0.9.0, `/admin/audit-log` (lien depuis le tableau de bord admin)
liste chaque action métier significative : qui, quoi, quand, sur quelle ressource.
Couverture : CRUD utilisateurs/groupes/shifts/astreintes/congés/types de shift,
tout le cycle de vie des échanges de shifts (demande/annulation/approbation/
rejet/annulation d'un échange approuvé/purge), modification des paramètres admin,
et les événements de connexion (réussie, échouée, déconnexion, inscription,
changement de mot de passe).

La page permet de filtrer par auteur, domaine d'action (`shift`, `oncall`,
`leave`, `swap`, `user`, `group`, `shift_type`, `setting`, `auth`, `profile`) et
plage de dates. Chaque entrée est aussi écrite dans `logs/audit.log` (double
écriture, défense en profondeur) — voir CLAUDE.md "Audit trail" pour le détail
technique.

**Purge** : le bouton "Purger selon la rétention" supprime les entrées plus
anciennes que la durée configurée dans **Paramètres → Audit trail**
(`/admin/settings`). Tant qu'aucune valeur n'y a été enregistrée, aucune purge
n'est possible — l'historique est conservé indéfiniment par défaut, contrairement
à la rétention des sauvegardes qui a un repli numérique.

#### Activer le logging avancé

Dans `.env` :
```bash
LOG_LEVEL=DEBUG
```

#### Fichiers de log

`logs/app.log`, `logs/error.log`, `logs/debug.log`, `logs/http_errors.log` et
`logs/audit.log` sont créés automatiquement au démarrage, avec rotation
(`LOG_MAX_BYTES` / `LOG_BACKUP_COUNT`, voir
[`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md#-configuration-du-logging)).
`LOG_FILE` permet en plus de rediriger la sortie racine vers un fichier
supplémentaire :

```bash
LOG_FILE=leviia.log
```

---

## 👥 Gestion Avancée des Utilisateurs

### Import/Export des Utilisateurs

> 📌 **Fonctionnalité à venir** : L'import/export CSV des utilisateurs sera disponible dans une future version.

### Gestion en Masse

#### Supprimer tous les utilisateurs d'un groupe

1. Allez dans **Admin** > **Utilisateurs**
2. Filtrez par groupe
3. Pour chaque utilisateur, cliquez sur **Supprimer**

> ⚠️ **Attention** : Vous devez d'abord supprimer les shifts, astreintes et congés associés.

#### Changer le groupe de plusieurs utilisateurs

1. Allez dans **Admin** > **Utilisateurs**
2. Cliquez sur **Modifier** pour chaque utilisateur
3. Changez le groupe
4. **Enregistrer**

### Utilisateurs Système

| Utilisateur | Rôle | Description |
|-------------|------|-------------|
| `admin@leviia.local` | Administrateur | Compte par défaut, doit être renommé |

### Bonnes Pratiques

1. **Nommage** : Utilisez des emails professionnels
2. **Groupes** : Organisez les utilisateurs par équipe/département
3. **Permissions** : Donnez uniquement les permissions nécessaires
4. **Audit** : Vérifiez régulièrement la liste des utilisateurs

---

## 🏢 Architecture des Groupes

### Stratégie de Groupement

#### Exemple 1 : Par Département

```
Groupe: Développement
├── Participe au planning: ✅
├── Participe aux astreintes: ✅
└── Utilisateurs: Jean, Marie, Pierre

Groupe: Support
├── Participe au planning: ✅
├── Participe aux astreintes: ✅
└── Utilisateurs: Sophie, Thomas

Groupe: Direction
├── Participe au planning: ❌
├── Participe aux astreintes: ❌
└── Utilisateurs: Monsieur Dupont
```

#### Exemple 2 : Par Type de Contrat

```
Groupe: Temps Plein
├── Participe au planning: ✅
├── Participe aux astreintes: ✅
└── Utilisateurs: ...

Groupe: Temps Partiel
├── Participe au planning: ✅
├── Participe aux astreintes: ❌
└── Utilisateurs: ...

Groupe: Stagiaires
├── Participe au planning: ✅
├── Participe aux astreintes: ❌
└── Utilisateurs: ...
```

### Migration des Utilisateurs

Pour déplacer un utilisateur vers un autre groupe :

1. Vérifiez que le nouveau groupe a les bonnes permissions
2. Allez dans **Admin** > **Utilisateurs**
3. Cliquez sur **Modifier** pour l'utilisateur
4. Changez le groupe
5. **Enregistrer**

> ⚠️ **Attention** : Si le nouvel groupe n'a pas la permission de participer au planning, l'utilisateur perdra ses shifts.

---

## ⚙️ Configuration des Types de Shifts

### Types de Shifts par Défaut

| Nom | Libellé | Heure Début | Heure Fin | Durée |
|-----|---------|--------------|-----------|-------|
| `morning` | Matin | 8h00 | 12h00 | 4h |
| `afternoon` | Après-midi | 12h00 | 18h00 | 6h |
| `evening` | Soirée | 18h00 | 22h00 | 4h |

### Créer un Type de Shift Personnalisé

#### Exemple 1 : Shift de Nuit

1. **Admin** > **Types de Shifts** > **Ajouter**
2. Nom : `night`
3. Libellé : `Nuit`
4. Heure de début : `22`
5. Heure de fin : `6`
6. **Enregistrer**

> ⚠️ **Attention** : Un shift qui passe minuit doit avoir une heure de fin > heure de début (ex: 22 à 6 = 22 à 30 pour 8h).

#### Exemple 2 : Shift Court

1. **Admin** > **Types de Shifts** > **Ajouter**
2. Nom : `short_morning`
3. Libellé : `Matin Court`
4. Heure de début : `9`
5. Heure de fin : `12`
6. **Enregistrer**

### Modifier un Type de Shift

1. **Admin** > **Types de Shifts**
2. Cliquez sur **Modifier** pour le type de shift
3. Modifiez les champs nécessaires
4. **Enregistrer**

> ⚠️ **Attention** : La modification d'un type de shift affecte tous les shifts existants qui l'utilisent.

### Supprimer un Type de Shift

1. **Admin** > **Types de Shifts**
2. Cliquez sur **Supprimer** pour le type de shift
3. Confirmez

> ⚠️ **Attention** : Vous ne pouvez pas supprimer un type de shift utilisé dans des shifts existants.

### Bonnes Pratiques

1. **Nommage** : Utilisez des noms courts et descriptifs (sans espaces)
2. **Libellés** : Utilisez des libellés clairs pour l'interface
3. **Chevauchement** : Évitez les chevauchements d'horaires
4. **Couverture** : Assurez-vous que tous les créneaux nécessaires sont couverts

---

## 📊 Tableau de Bord et Statistiques

### Vue d'Ensemble

Le tableau de bord administrateur affiche :

- **Utilisateurs** : Nombre total d'utilisateurs
- **Groupes** : Nombre total de groupes
- **Shifts** : Nombre total de shifts planifiés
- **Astreintes** : Nombre total d'astreintes
- **Congés** : Nombre total de congés

### Statistiques Avancées

> 📌 **À venir** : Des graphiques et rapports détaillés seront ajoutés.

### Accès Rapide

Depuis le tableau de bord, vous pouvez accéder à :
- **Utilisateurs** : Gestion complète des utilisateurs
- **Groupes** : Configuration des groupes
- **Types de Shifts** : Paramétrage des types de shifts
- **Automatisation** : Configuration de l'automatisation

---

## ⚡ Automatisation Complète

### Architecture de l'Automatisation

Leviia Schedule propose plusieurs niveaux d'automatisation :

```
┌─────────────────────────────────────────────────┐
│                AUTOMATISATION                     │
├─────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐          │
│  │  Astreintes   │    │    Shifts     │          │
│  │  (On-Call)    │    │              │          │
│  └──────────────┘    └──────────────┘          │
│         │                   │                 │
│         ▼                   ▼                 │
│  ┌─────────────────────────────────────────┐  │
│  │         Génération Complète              │  │
│  │   (Astreintes + Shifts en une fois)       │  │
│  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Configuration des Astreintes Automatiques

#### Étape 1 : Définir l'ordre de rotation

1. Allez dans **Admin** > **Automatisation** > **Génération complète**
2. Pour chaque utilisateur éligible :
   - ✅ **Inclure dans la rotation** : Cochez pour inclure
   - **Position** : Définissez l'ordre (1 = premier)
3. Cliquez sur **Enregistrer l'ordre**

Exemple d'ordre de rotation :
```
Position 1: Jean Dupont
Position 2: Marie Martin
Position 3: Pierre Durand
Position 4: Sophie Leroy
```

#### Étape 2 : Configurer la période

1. **Date de début** : Premier vendredi de la période
2. **Date de fin** : Dernier jour de la période
3. Cliquez sur **Simuler** pour prévisualiser

#### Étape 3 : Générer

1. Vérifiez le résultat de la simulation
2. Cliquez sur **Générer** pour créer les astreintes

### Configuration des Shifts Automatiques

#### Étape 1 : Définir les besoins quotidiens

1. Allez dans **Admin** > **Automatisation** > **Shifts**
2. Pour chaque jour (lundi à vendredi) :
   - **Matin** : Nombre de personnes nécessaires
   - **Après-midi** : Nombre de personnes nécessaires
   - **Soirée** : Nombre de personnes nécessaires

Exemple de configuration :
```
Lundi:
  - Matin: 2 personnes
  - Après-midi: 2 personnes
  - Soirée: 1 personne

Mardi à Vendredi: Même configuration
```

#### Étape 2 : Configurer la période

1. **Date de début** : Premier jour de la période
2. **Date de fin** : Dernier jour de la période
3. Cliquez sur **Simuler** pour prévisualiser

#### Étape 3 : Générer

1. Vérifiez le résultat de la simulation
2. Cliquez sur **Générer** pour créer les shifts

### Génération Complète (Astreintes + Shifts)

Pour générer tout en une seule opération :

1. Allez dans **Admin** > **Automatisation** > **Génération complète**
2. Configurez l'ordre de rotation des astreintes
3. Sélectionnez la période
4. Cliquez sur **Simuler**
5. Vérifiez que tout est correct
6. Cliquez sur **Générer**

> 💡 **Astuce** : La génération complète prend en compte les astreintes pour éviter les conflits avec les shifts.

### Rafraîchir les Shifts

Si vous avez modifié manuellement des astreintes :

1. Allez dans **Admin** > **Automatisation** > **Rafraîchir les shifts**
2. Sélectionnez la période à recalculer
3. Cliquez sur **Rafraîchir**

> ⚠️ **Attention** : Cette action supprimera tous les shifts existants pour la période sélectionnée !

### Règles Métiers

#### Règles par défaut pour les astreintes

```python
{
    "rotation_order": [1, 2, 3, 4],  # Ordre des utilisateurs
    "duration_days": 7,              # Durée en jours
    "start_hour": 21,               # Heure de début (21h = 9 PM)
    "end_hour": 7,                 # Heure de fin (7h = 7 AM)
    "start_day": 4                 # Jour de la semaine (4 = Vendredi)
}
```

#### Règles par défaut pour les shifts

```python
{
    "daily_requirements": {
        "monday": {"morning": 2, "afternoon": 2, "evening": 1},
        "tuesday": {"morning": 2, "afternoon": 2, "evening": 1},
        "wednesday": {"morning": 2, "afternoon": 2, "evening": 1},
        "thursday": {"morning": 2, "afternoon": 2, "evening": 1},
        "friday": {"morning": 2, "afternoon": 2, "evening": 1}
    },
    "weekend_excluded": True
}
```

### Personnalisation des Règles

Vous pouvez personnaliser les règles dans le fichier de configuration ou via l'interface d'automatisation.

---

## 🔧 Configuration Technique

### Paramètres administrables via l'UI (`/admin/settings`)

Depuis les versions 0.7.10 à 0.9.0, un ensemble croissant de réglages,
auparavant uniquement des variables d'environnement, est éditable à chaud
depuis `/admin/settings` sans redéploiement : fuseau horaire par défaut,
langue par défaut (Français/Anglais), formats de date/heure par défaut,
URL publique, pagination (éléments par page), notifications par email
(activation globale), rétention des sauvegardes, durée d'expiration du
token ICS, et rétention de l'audit trail. Chaque réglage suit la même
règle : une valeur enregistrée en base l'emporte toujours ; tant
qu'aucune valeur n'a été enregistrée, l'application se rabat en direct
sur la variable d'environnement/valeur par défaut correspondante (donc un
déploiement piloté uniquement par variables d'environnement continue de
fonctionner à l'identique tant que personne ne passe par cette page).
Chaque utilisateur peut aussi surcharger individuellement son fuseau
horaire, sa langue, et ses formats de date/heure depuis `/profile/settings`
(sinon la valeur par défaut de l'organisation s'applique).

Chaque modification effectuée sur cette page (comme toute action métier)
est enregistrée dans l'historique des modifications — voir "Audit et
Journalisation" ci-dessus.

### Fichier de Configuration

La configuration active vit dans `app/config/` (`base.py`, `testing.py`),
lue à partir des variables d'environnement (`.env`). `create_app()` charge
toujours `app.config.base.Config` en production comme en développement
(`FLASK_ENV` ne sélectionne qu'entre Gunicorn et le serveur de
développement Flask, pas une classe de configuration) ; `TestingConfig`
n'est utilisée que par la suite de tests.

```python
# app/config/base.py (extrait)
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_urlsafe(32)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOGIN_DISABLED = get_bool_from_env('LOGIN_DISABLED', False)
```

### Variables d'Environnement

| Variable | Description | Valeur par défaut | Recommandation |
|----------|-------------|------------------|----------------|
| `SECRET_KEY` | Clé secrète pour la sécurité | Aléatoire si absente | ⭐⭐⭐⭐⭐ Générer une clé forte et la fixer explicitement |
| `DATABASE_URL` | URI de la base de données | `sqlite:///app.db` | Utiliser PostgreSQL ou MariaDB en production |
| `LOGIN_DISABLED` | Désactive l'authentification | `false` | ❌ Ne JAMAIS activer en production |
| `LOG_LEVEL` | Niveau de journalisation | `INFO` | `DEBUG` pour le développement |

Liste complète : [`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md).

### Configuration de la Base de Données

Toutes les variantes se configurent via `DATABASE_URL` dans `.env` — pas
de fichier Python à modifier.

#### SQLite (par défaut)

```bash
DATABASE_URL=sqlite:///app.db
```

- **Avantages** : Simple, pas de serveur requis
- **Inconvénients** : Pas adapté pour la production, pas de concurrency

#### PostgreSQL (recommandé pour la production)

```bash
DATABASE_URL=postgresql://user:password@localhost/leviia
```

Le driver (`psycopg[binary]`, psycopg 3) est déjà inclus par défaut dans
`requirements.txt` — aucune installation supplémentaire nécessaire. Voir
[`deployment/DEPLOYMENT_ADVANCED.md`](../deployment/DEPLOYMENT_ADVANCED.md)
pour une configuration complète.

- **Avantages** : Robuste, scalable, support de la concurrency
- **Inconvénients** : Requiert un serveur PostgreSQL

#### MariaDB / MySQL

```bash
DATABASE_URL=mariadb://user:password@localhost:3306/leviia
# ou : DATABASE_URL=mysql://user:password@localhost:3306/leviia
```

Déjà supporté (SQLAlchemy gère le choix du backend via l'URI). Le driver
`PyMySQL` — 100% pur Python, aucune bibliothèque système requise — est
déjà inclus par défaut dans `requirements.txt`, aucune installation
supplémentaire nécessaire. C'est ce qui permet de connecter l'app à un
serveur MySQL/MariaDB **externe** sans rien installer côté MySQL, ni sur
la machine hôte ni dans l'image Docker. Voir
[`deployment/DEPLOYMENT_GUIDE.md`](../deployment/DEPLOYMENT_GUIDE.md#73-mysqlmariadb)
section 7.3 pour un exemple complet.

### Configuration du Serveur

#### Développement (Flask intégré)

```bash
python run.py
```

- **Port** : 5000
- **Host** : localhost
- **Debug** : Activé

#### Production (Gunicorn + Nginx)

1. Installer Gunicorn :
   ```bash
   pip install gunicorn
   ```

2. Créer un fichier `wsgi.py` :
   ```python
   from app import app
   
   if __name__ == "__main__":
       app.run()
   ```

3. Lancer Gunicorn :
   ```bash
   gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
   ```

4. Configurer Nginx comme reverse proxy

---

## 📤 Export et Intégrations

### Export ICS

#### Configuration

L'export ICS est disponible via l'URL :
```
/export/shifts?scope={scope}&token={token}
```

**Paramètres** :
- `scope` : `my` (planning personnel) ou `all` (tous les plannings)
- `token` : Token ICS de l'utilisateur

#### Générer un token ICS

La génération de token est **en libre-service** — chaque utilisateur
génère le sien depuis son propre profil (**Profil > Token ICS >
Générer un nouveau token**, route `POST /profile/ics-token`). Il n'y a
pas de workflow admin permettant de générer le token d'un autre
utilisateur depuis l'écran **Admin > Utilisateurs**.

#### Intégration avec Google Calendar

1. Dans Google Calendar : **Paramètres** > **Ajouter un calendrier** > **À partir d'une URL**
2. Collez l'URL : `http://votre-serveur/export/shifts?scope=my&token=VOTRE_TOKEN`
3. **Ajouter un calendrier**

#### Intégration avec Outlook

1. Dans Outlook : **Fichier** > **Paramètres du compte** > **Paramètres du compte**
2. **Nouveau** > **Calendrier Internet**
3. Collez l'URL
4. **Suivant**

### Export Avancé

Leviia Schedule propose trois endpoints d'export distincts :

#### Endpoints disponibles

| Endpoint | Description | Paramètres |
|----------|-------------|------------|
| `/export/shifts` | Exporte les shifts (plannings de travail) | `scope`, `token` |
| `/export/oncall` | Exporte les astreintes (on-call) | `scope`, `token` |
| `/export/leaves` | Exporte les congés | `scope`, `token` |

#### Paramètres communs

| Paramètre | Valeurs possibles | Description |
|-----------|-------------------|-------------|
| `scope` | `my`, `all` | `my` = données de l'utilisateur, `all` = toutes les données (admin seulement) |
| `token` | Token ICS | Token d'authentification généré dans le profil |

#### Exemples d'URLs

```bash
# Export personnel
/export/shifts?scope=my&token=VOTRE_TOKEN
/export/oncall?scope=my&token=VOTRE_TOKEN
/export/leaves?scope=my&token=VOTRE_TOKEN

# Export complet (admin)
/export/shifts?scope=all&token=TOKEN_ADMIN
/export/oncall?scope=all&token=TOKEN_ADMIN
/export/leaves?scope=all&token=TOKEN_ADMIN
```

### API REST (À venir)

> 📌 **Fonctionnalité prévue** : Une API REST publique sera disponible dans la version 0.8.

### Webhooks (À venir)

> 📌 **Fonctionnalité prévue** : Les webhooks seront disponibles dans la version 0.8.

---

## 🎨 Personnalisation

### Personnalisation de l'Interface

#### Logo et Favicon

Remplacez les fichiers dans `app/templates/` :
- `favicon.ico` : Favicon de l'application
- (À venir) : Logo dans le header

#### CSS Personnalisé

1. Créez un fichier `app/static/css/custom.css`
2. Ajoutez vos styles personnalisés
3. Le fichier sera automatiquement chargé

### Notifications par Email

Leviia Schedule envoie des rappels hebdomadaires par email :
- Un récapitulatif des shifts de la semaine à venir, envoyé le
  **dimanche** (24h avant le début des shifts du lundi).
- Un rappel d'astreinte, envoyé le **jeudi** (24h avant le début de
  l'astreinte du vendredi 21h).

Ces emails sont envoyés par deux scripts autonomes
(`scripts/send_shift_notifications.py` et
`scripts/send_oncall_notifications.py`), déclenchés par une tâche cron
externe - **pas** par l'application Flask elle-même. Un seul email est
envoyé par semaine et par utilisateur (garde-fou anti-doublon en base).

#### Activer les notifications

1. Configurez les variables SMTP dans `.env` (voir
   [`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md#-configuration-des-notifications)) :
   `NOTIFICATIONS_ENABLED=true`, `NOTIFICATION_FROM_EMAIL`, `SMTP_HOST`,
   `SMTP_PORT`, `SMTP_USERNAME`/`SMTP_PASSWORD` si votre serveur SMTP
   requiert une authentification.
2. Ajoutez les deux entrées crontab (voir `scripts/cron_example.sh`
   pour un exemple complet) :

```bash
# Dimanche 9h : rappel des shifts de la semaine
0 9 * * 0 cd /chemin/vers/leviia-schedule && venv/bin/python scripts/send_shift_notifications.py >> /var/log/leviia-notifications.log 2>&1

# Jeudi 9h : rappel de l'astreinte du vendredi
0 9 * * 4 cd /chemin/vers/leviia-schedule && venv/bin/python scripts/send_oncall_notifications.py >> /var/log/leviia-notifications.log 2>&1
```

Si `NOTIFICATIONS_ENABLED` n'est pas activé (ou si la config SMTP est
incomplète), les scripts se terminent silencieusement sans rien
envoyer - pas besoin de désactiver le cron pour couper les
notifications, une seule variable d'environnement suffit.

#### Personnaliser le contenu des emails

Les gabarits (HTML + texte) sont dans `app/templates/emails/` :
`shift_weekly.html`/`.txt` et `oncall_weekly.html`/`.txt`. Ce sont des
templates Jinja2 classiques - modifiez-les directement pour changer le
contenu, la mise en forme ou la marque (logo, couleurs).

### Personnalisation des Règles Métiers

Vous pouvez personnaliser les règles métiers dans :
- `app/utils/automation/` : règles d'automatisation
  (`advanced_shift_automation.py`, `oncall_automation.py`)
- `app/utils/helpers/common_helpers.py` : fonctions de validation
  (`can_add_shift`, `can_add_leave`, `can_add_oncall`)
- `app/auth/decorators.py` : décorateurs de garde de route
  (`@admin_required`, `@user_owns_resource`, etc.)

Voir [`architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md)
pour la structure complète.

---

## 🔄 Maintenance et Sauvegardes

### Sauvegarde de la Base de Données

Le système de sauvegarde intégré (`scripts/backup_database.py`) gère la
sauvegarde locale et/ou S3/S3-compatible, la compression, la
vérification d'intégrité, la rétention et les alertes email - voir le
[Guide de Sauvegarde](BACKUP_GUIDE.md) pour le détail complet. Piloté
entièrement par variables d'environnement (`BACKUP_ENABLED` en premier
lieu, voir [`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md#-configuration-des-sauvegardes)) -
désactivé par défaut.

Deux façons de déclencher une sauvegarde :

- **Interface d'administration** (`/admin/backups`) : configuration
  active, liste des sauvegardes locales/S3, création à la demande,
  nettoyage, téléchargement. La création manuelle est refusée si
  `BACKUP_ENABLED=false`.
- **Cron** (recommandé pour l'automatisation) : voir
  [Automatisation avec Cron](BACKUP_GUIDE.md#-automatisation-avec-cron)
  ou, en Docker, `BACKUP_ENABLED=true` suffit (même conteneur que
  l'application, planning dans `docker/crontabs/appuser`, voir
  [`deployment/docker.md`](../deployment/docker.md)).

Pour une sauvegarde ponctuelle manuelle sans passer par ce système
(dépannage, avant une opération risquée) :

```bash
# SQLite
cp instance/app.db instance/app.db.backup-$(date +%Y%m%d)

# PostgreSQL
pg_dump leviia > leviia-backup-$(date +%Y%m%d).sql
```

### Mise à Jour de l'Application

1. Sauvegardez la base de données
2. Sauvegardez votre fichier `.env` (contient `SECRET_KEY` et les autres
   secrets, non versionné)
3. Mettez à jour le code :
   ```bash
   git pull origin main
   ```
4. Installez les nouvelles dépendances :
   ```bash
   pip install -r requirements.txt
   ```
5. Redémarrez l'application

### Nettoyage

#### Supprimer les données obsolètes

1. **Shifts passés** : Supprimez les shifts anciens pour améliorer les performances
2. **Astreintes passées** : Supprimez les astreintes terminées
3. **Congés passés** : Supprimez les congés terminés

#### Optimisation de la Base de Données

Pour SQLite :
```bash
# Réorganiser la base de données
sqlite3 instance/app.db "VACUUM;"
```

Pour PostgreSQL :
```bash
# Réorganiser et analyser
psql leviia -c "VACUUM ANALYZE;"
```

---

## 🚨 Gestion des Erreurs

### Erreurs Courantes et Solutions

#### Erreur : "Impossible de supprimer... des données sont associées"

**Cause** : Vous essayez de supprimer un élément qui a des dépendances.

**Solution** : Supprimez d'abord les données associées (shifts, astreintes, congés).

#### Erreur : "Format de date invalide"

**Cause** : La date n'est pas au format `AAAA-MM-JJ`.

**Solution** : Utilisez le format `2026-06-15`.

#### Erreur : "L'astreinte doit commencer un vendredi"

**Cause** : Vous essayez de créer une astreinte qui ne commence pas un vendredi.

**Solution** : Sélectionnez un vendredi comme date de début.

#### Erreur : "Email ou mot de passe incorrect"

**Cause** : Identifiants invalides.

**Solution** : Vérifiez votre email et mot de passe. Utilisez la réinitialisation si nécessaire.

#### Erreur 500 : Erreur serveur

**Cause** : Problème interne du serveur.

**Solution** :
1. Vérifiez les logs de l'application
2. Vérifiez que la base de données est accessible
3. Redémarrez l'application
4. Contactez le support si le problème persiste

### Logs et Dépannage

#### Activer le mode debug

Dans `run.py` :
```python
app.run(debug=True)
```

#### Voir les logs

```bash
# Lancer l'application avec logs
python run.py
```

#### Problèmes de Base de Données

**Symptôme** : L'application ne démarre pas, erreurs de connexion.

**Solutions** :
1. Vérifiez que le fichier `instance/app.db` existe
2. Vérifiez les permissions : `chmod 666 instance/app.db`
3. Vérifiez que SQLite est installé
4. Pour PostgreSQL, vérifiez que le serveur est en cours d'exécution

---

## 📚 Ressources pour Administrateurs

### Documentation

- [📖 Guide Utilisateur Complet](USER_GUIDE.md)
- [🚀 Guide de Démarrage Rapide](QUICK_START.md)
- [❓ FAQ](FAQ.md)
- [🏗️ Architecture Technique](../architecture/ARCHITECTURE.md)
- [🚀 Guide de Déploiement](../deployment/DEPLOYMENT_GUIDE.md)
- [🗺️ Feuille de Route](../../ROADMAP.md)
- [📋 README Technique](../../README.md)

### Outils

- **SQLite Browser** : [https://sqlitebrowser.org/](https://sqlitebrowser.org/)
- **PostgreSQL Admin** : pgAdmin, DBeaver
- **Monitoring** : Prometheus, Grafana (pour la production)

### Communautés

- **GitHub Issues** : [https://github.com/FoxOps/leviia-schedule/issues](https://github.com/FoxOps/leviia-schedule/issues)
- **GitHub Discussions** : [https://github.com/FoxOps/leviia-schedule/discussions](https://github.com/FoxOps/leviia-schedule/discussions)

---

## 📝 Checklist Administrateur

### Après l'Installation

- [ ] Changer le mot de passe administrateur par défaut
- [ ] Configurer les groupes nécessaires
- [ ] Ajouter les utilisateurs
- [ ] Configurer les types de shifts
- [ ] Tester l'application
- [ ] Configurer les sauvegardes automatiques

### Mensuellement

- [ ] Vérifier les sauvegardes
- [ ] Vérifier les logs pour les erreurs
- [ ] Mettre à jour l'application
- [ ] Vérifier l'espace disque
- [ ] Auditer les utilisateurs et permissions

### Trimestriellement

- [ ] Tester la restauration des sauvegardes
- [ ] Optimiser la base de données
- [ ] Revoir les règles d'automatisation
- [ ] Mettre à jour la documentation

---

## 📞 Support Administrateur

### Contacter le Support

1. **Issues GitHub** : Pour les bugs et demandes de fonctionnalités
2. **Discussions GitHub** : Pour les questions générales
3. **Documentation** : Consultez ce guide et les autres documents

### Informations à Fournir

Lors de la signalisation d'un problème, fournissez :
- Version de l'application
- Type de base de données
- Étapes pour reproduire
- Logs d'erreur
- Capture d'écran (si applicable)

---

> **⚠️ Rappel** : En tant qu'administrateur, vous êtes responsable de la sécurité et de la bonne utilisation de l'application.

---

*© 2026 Leviia Schedule - Tous droits réservés selon la licence CeCILL v2.1*
