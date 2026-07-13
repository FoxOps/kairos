# Architecture technique

> Réécrit intégralement en Phase 5 (2026-07) — la version précédente
> décrivait `app/models.py` en fichier plat et `app/utils/decorators.py`/
> `helpers.py`/`ics_exporter.py`/`automation.py` directement à la racine
> de `app/utils/` ; ces deux structures ont été remplacées par des
> packages depuis les Phases 2-4 (voir `report/Phase 2: Backend.md` et
> `CLAUDE.md` à la racine du dépôt pour l'historique).

## Vue d'ensemble

Leviia Schedule est une application Flask monolithique en couches :
routes → services → repositories → modèles, avec les gabarits Jinja2
rendus côté serveur (pas de frontend séparé/SPA).

```mermaid
graph TB
    subgraph Client["Navigateur"]
        UI[Templates Jinja2 + JS ES6 modules]
    end

    subgraph Flask["Application Flask (app/)"]
        direction TB
        Routes["routes/<br/>blueprints : auth, main, admin, export"]
        Services["services/<br/>logique métier"]
        Repos["repositories/<br/>accès aux données"]
        Models["models/<br/>SQLAlchemy ORM"]
        Auth["auth/<br/>décorateurs, OIDC, gestion utilisateur"]
        Utils["utils/<br/>automation, cache, export, logging, security, health"]

        Routes --> Services
        Services --> Repos
        Repos --> Models
        Routes --> Auth
        Services --> Utils
    end

    DB[(SQLite / PostgreSQL)]
    IdP[Fournisseur OIDC<br/>Keycloak / Okta / Auth0]

    UI -->|HTTP + CSRF token| Routes
    Models --> DB
    Auth -->|SSO optionnel| IdP
```

### Pourquoi une couche services/repositories

Avant la Phase 2, toute la logique (parsing de requête, règles métier,
requêtes SQL) vivait directement dans `app/main.py` (1287 lignes) et
`app/admin.py`. Ça a été scindé en trois responsabilités distinctes :

- **`app/routes/`** : parse la requête HTTP, appelle un service, transforme
  le résultat en flash/redirect/JSON. Aucune requête SQL ni règle métier
  ici.
- **`app/services/`** : logique métier (validations comme `can_add_shift`,
  effets de bord comme le rééquilibrage automatique des shifts après un
  changement de congé). Appelle les repositories, jamais Flask
  directement (pas de `request`/`flash`/`render_template`).
- **`app/repositories/`** : accès aux données, requêtes SQLAlchemy pures.
  Aucune logique métier ici (pas de `can_add_*`, pas de calcul de dates).

Chaque blueprint (`main`, `admin`) est en réalité découpé sur plusieurs
fichiers Python qui s'enregistrent tous sur le **même objet
`Blueprint`** (défini dans `main.py`/`admin.py`), pour éviter de casser
les références `url_for()` existantes :

```mermaid
graph LR
    subgraph main_bp["main_bp (app/routes/main.py)"]
        dashboard[dashboard_routes.py]
        shift[shift_routes.py]
        oncall[oncall_routes.py]
        leave[leave_routes.py]
    end
    subgraph admin_bp["admin_bp (app/routes/admin.py)"]
        admin_dash["/admin (dashboard)"]
        admin_user[admin_user_routes.py]
        admin_group[admin_group_routes.py]
        admin_shift_type[admin_shift_type_routes.py]
        admin_automation[admin_automation_routes.py]
    end
```

## Structure des dossiers

```
app/
├── __init__.py           # create_app() : factory, extensions (db, login_manager,
│                          # limiter, csrf, Talisman conditionnel), blueprints
├── config/                # Configuration active : base.py, development.py,
│                          # production.py, testing.py
├── auth/                  # decorators.py (garde-fous de route), user_manager.py,
│                          # oidc_auth.py (SSO via Authlib)
├── models/                 # BaseModel + Group, User, ShiftType, Shift, OnCall,
│                          # Leave, AutomationConfig, NotificationLog
├── repositories/           # UserRepository, GroupRepository, ShiftRepository,
│                          # ShiftTypeRepository, OnCallRepository, LeaveRepository
├── services/               # UserService, GroupService, ShiftService,
│                          # ShiftTypeService, OnCallService, LeaveService,
│                          # ExportService, ScheduleService, AutomationAdminService,
│                          # NotificationService (rappels email, appelé par
│                          # scripts/send_*_notifications.py, pas par une route)
├── routes/                 # auth.py, main.py + {dashboard,shift,oncall,leave}_routes.py,
│                          # admin.py + admin_{user,group,shift_type,automation}_routes.py,
│                          # export.py
├── utils/
│   ├── automation/         # AdvancedShiftAutomation (moteur unique de génération
│   │                      # de shifts), OnCallAutomation, status
│   ├── cache/              # init_cache, cache_manager (fallback dict cache)
│   ├── export/              # génération ICS (icalendar)
│   ├── helpers/             # common_helpers.py (can_add_shift/leave/oncall,
│   │                      # formatage/parsing de dates)
│   ├── logging/             # logger multi-handler (app/error/http/audit/sql/auth)
│   ├── notifications/       # email_sender.py (smtplib/email, stdlib) - appelé
│   │                      # par NotificationService, pas de route associée
│   ├── optimizations/       # eager_load (seul décorateur restant, Phase 4)
│   ├── security/            # (vide depuis Phase 4 — encryption.py et
│   │                      # token_manager.py supprimés, aucun appelant réel)
│   ├── health.py            # endpoints /health, /ready, /version (k8s probes)
│   └── prometheus_metrics.py # /metrics, gated par PROMETHEUS_ENABLED
├── static/
│   ├── css/                 # variables/base/utilities/components/layout/themes/vendor
│   └── js/                  # main.js (entrée module ES6) + theme/utils/notifications
└── templates/                # Jinja2, macros/errors.html pour les pages d'erreur,
                              # emails/ pour les gabarits de notification (HTML + texte)
```

`scripts/` (hors `app/`) contient les points d'entrée cron autonomes -
`send_shift_notifications.py`/`send_oncall_notifications.py` +
`notification_config.py` (config SMTP via variables d'environnement) -
suivant le même pattern que `backup_database.py`/`backup_config.py`.
Pas de scheduler intégré à l'application Flask (pas d'APScheduler) :
ces scripts sont déclenchés par une tâche cron externe, voir
`scripts/cron_example.sh`.

## Modèles de données

Voir [`ERD.md`](ERD.md) pour le schéma entité-relation complet.

Résumé : `Group` 1:N `User` 1:N `Shift`/`OnCall`/`Leave` (chacun 1:N
depuis `User`), `ShiftType` 1:N `Shift`. `AutomationConfig` est une table
autonome (clé/valeur JSON) sans relation, utilisée pour persister l'ordre
de rotation des astreintes. `NotificationLog` (user_id, notification_type,
period_start, contrainte unique sur les trois) enregistre les rappels
email déjà envoyés, pour empêcher un double envoi si un script cron est
relancé sur la même période.

## Authentification

Deux modes, contrôlés par `OIDCConfig` (`config_oidc.py`) :

1. **Basique** (par défaut) : email/mot de passe via Flask-Login,
   formulaire `/login`.
2. **OIDC/SSO** (optionnel) : si `OIDC_ENABLED=true`, redirection vers le
   fournisseur configuré. Si en plus `OIDC_DISABLE_BASIC_AUTH=true`, le
   formulaire classique est désactivé et `/login` redirige directement
   vers `/oidc/login`.

Voir [`SEQUENCE_DIAGRAMS.md`](SEQUENCE_DIAGRAMS.md) pour le détail des
deux flux.

## Sécurité

- **CSRF** : `Flask-WTF` `CSRFProtect` actif sur toute l'application
  (ajouté en Phase 4 — absent auparavant malgré la présence de la
  dépendance). Les formulaires HTML embarquent un champ caché
  `csrf_token`, les appels `fetch()` JS envoient l'en-tête
  `X-CSRFToken` (lu depuis une balise `<meta name="csrf-token">` dans
  `base.html`).
- **Talisman** : en-têtes de sécurité HTTP (X-Content-Type-Options,
  X-Frame-Options, etc.), activé seulement si `TALISMAN_FORCE_HTTPS=true`
  (voir `app/config/`).
- **Mots de passe** : hashés via Werkzeug (`generate_password_hash`),
  jamais stockés en clair, jamais sérialisés (`User.to_dict()` exclut
  explicitement `password_hash` et `ics_token`).
- **Export ICS** : accessible soit via une session authentifiée, soit via
  un token porteur (`ics_token`, `secrets.token_urlsafe(32)`) passé en
  paramètre d'URL — voir [`api/API.md`](../api/API.md).

## Base de données

SQLite par défaut (fichier `instance/app.db`), PostgreSQL supporté en
production (voir [`deployment/DEPLOYMENT_ADVANCED.md`](../deployment/DEPLOYMENT_ADVANCED.md)).
Index composites présents sur `Shift(user_id, date)`,
`Shift(date, start_time)`, `OnCall(user_id, start_time, end_time)`,
`Leave(user_id, start_date, end_date)` — à préserver si vous touchez aux
patterns de requête.

## Tests

Voir `tests/` (`unit/`, `integration/`, `e2e/`, `fixtures/`) et
`report/Phase 4: AMÉLIORATION DES TESTS.md` pour la structure et
l'historique de la couverture (81% au moment de la Phase 5).
