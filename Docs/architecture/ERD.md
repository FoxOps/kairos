# Schéma entité-relation (ERD)

Généré à partir de `app/models/*.py` (Phase 5, 2026-07, complété 2026-07-16
avec `Setting`/`SwapRequest`/`AppNotification`/`AuditLog` — voir CLAUDE.md
"Shift swaps"/"In-app notifications"/"Audit trail" pour le détail
fonctionnel de chacun) — les champs `id`, `created_at`, `updated_at` sont
hérités de `BaseModel` (`app/models/base.py`) et communs à toutes les
tables ci-dessous.

```mermaid
erDiagram
    GROUP ||--o{ USER : "a pour membres"
    USER ||--o{ SHIFT : "assigné à"
    USER ||--o{ ON_CALL : "assigné à"
    USER ||--o{ LEAVE : "demande"
    USER ||--o{ NOTIFICATION_LOG : "reçoit"
    USER ||--o{ APP_NOTIFICATION : "reçoit"
    USER ||--o{ SWAP_REQUEST : "requester/target_user/reviewer (3 FK)"
    SHIFT ||--o{ SWAP_REQUEST : "shift/target_shift (2 FK)"
    USER ||--o{ AUDIT_LOG : "acteur (nullable)"
    SHIFT_TYPE ||--o{ SHIFT : "définit le créneau de"

    GROUP {
        int id PK
        string name UK "unique, not null"
        bool is_part_of_schedule
        bool is_part_of_oncall
        datetime created_at
        datetime updated_at
    }

    USER {
        int id PK
        string name
        string email UK
        string password_hash "jamais sérialisé (to_dict)"
        bool is_admin
        int group_id FK
        string ics_token UK "nullable, jamais sérialisé"
        string timezone "nullable, repli sur Setting.default_timezone"
        string language "nullable String(5), repli sur Setting.default_language"
        string date_format "nullable, repli sur Setting.default_date_format"
        string time_format "nullable, repli sur Setting.default_time_format"
        bool shift_notifications_enabled "défaut true"
        bool oncall_notifications_enabled "défaut true"
        datetime created_at
        datetime updated_at
    }

    SETTING {
        int id PK
        string key UK "ex. default_timezone, notifications_enabled"
        text value "sérialisé (str/bool/int)"
        datetime created_at
        datetime updated_at
    }

    SWAP_REQUEST {
        int id PK
        int requester_id FK "vers user.id"
        int target_user_id FK "vers user.id"
        int reviewer_id FK "vers user.id, nullable tant que non traité"
        int shift_id FK "vers shift.id"
        int target_shift_id FK "vers shift.id, nullable (don simple)"
        string status "PENDING/APPROVED/REJECTED/CANCELLED/REVERTED"
        text admin_comment "nullable"
        datetime reviewed_at "nullable"
        datetime created_at
        datetime updated_at
    }

    APP_NOTIFICATION {
        int id PK
        int user_id FK
        string message
        string link "nullable, ex. /admin/swaps"
        bool is_read "défaut false"
        datetime created_at
        datetime updated_at
    }

    AUDIT_LOG {
        int id PK
        int actor_id FK "nullable, vers user.id"
        string action "namespacé domaine.verbe, ex. shift.create"
        string resource_type "nullable, ex. Shift, User, Setting"
        int resource_id "nullable"
        text details "résumé court, pas un diff structuré"
        string ip_address "nullable, IPv6-safe"
        datetime created_at
        datetime updated_at "hérité, jamais modifié - append-only"
    }

    SHIFT_TYPE {
        int id PK
        string name UK
        string label
        int start_hour
        int end_hour
        datetime created_at
        datetime updated_at
    }

    SHIFT {
        int id PK
        int user_id FK
        int shift_type_id FK
        datetime start_time "indexé"
        datetime end_time "indexé"
        date date "indexé"
        datetime created_at
        datetime updated_at
    }

    ON_CALL {
        int id PK
        int user_id FK
        datetime start_time "indexé"
        datetime end_time "indexé"
        datetime created_at
        datetime updated_at
    }

    LEAVE {
        int id PK
        int user_id FK
        date start_date "indexé"
        date end_date "indexé"
        datetime created_at
        datetime updated_at
    }

    AUTOMATION_CONFIG {
        int id PK
        string config_key UK
        text config_value "JSON encodé"
        datetime created_at
        datetime updated_at
    }

    NOTIFICATION_LOG {
        int id PK
        int user_id FK
        string notification_type "shift_weekly ou oncall_weekly"
        date period_start "UK avec user_id+notification_type"
        datetime created_at
        datetime updated_at
    }
```

## Notes

- **`AutomationConfig`** n'a aucune relation avec les autres tables :
  c'est un stockage clé/valeur générique (utilisé pour persister l'ordre
  de rotation des astreintes entre redémarrages). Absent de toute
  documentation précédente malgré son usage réel dans
  `app/utils/automation/`.
- **`Leave` n'a pas de champ `reason`** — l'ancienne documentation API
  décrivait un champ `reason: string` sur les congés qui n'a jamais
  existé dans le modèle.
- **`NotificationLog`** : contrainte unique sur
  `(user_id, notification_type, period_start)` - empêche un double
  envoi si un script de notification (`scripts/send_*_notifications.py`)
  est relancé pour une période déjà traitée.
- **Index composites** (au-delà des index simples listés ci-dessus,
  définis dans les classes de modèle) :
  - `Shift(user_id, date)` et `Shift(date, start_time)`
  - `OnCall(user_id, start_time, end_time)`
  - `Leave(user_id, start_date, end_date)`

  Préservez ces index si vous modifiez les patterns de requête dans
  `app/repositories/`.
- **Suppression en cascade** : `Group.users`, `User.shifts`,
  `User.on_calls` et `User.leaves` sont tous déclarés
  `cascade="all, delete-orphan"` — supprimer un groupe supprime ses
  utilisateurs, supprimer un utilisateur supprime tous ses shifts/
  astreintes/congés.
- **`Setting`** : store clé/valeur générique (même forme qu'`AutomationConfig`)
  pour les réglages admin éditables à chaud depuis `/admin/settings`
  (fuseau horaire, langue, formats de date/heure, URL publique,
  pagination, notifications, rétention sauvegardes/audit, expiration
  token ICS) — une ligne présente l'emporte toujours ; son absence fait
  retomber en direct sur la variable d'environnement/valeur par défaut
  correspondante (`SettingsService`, voir CLAUDE.md "Configuration:
  two parallel systems").
- **`SwapRequest`** : le premier modèle du projet avec plusieurs FK vers
  la même table (`requester_id`/`target_user_id`/`reviewer_id` → `User`).
  Délibérément **sans** `db.relationship()` (limite de typage des stubs
  SQLAlchemy 2.0 sur les relations non configurées avec le plugin mypy
  dédié) — `requester`/`target_user`/`reviewer`/`shift`/`target_shift`
  sont de simples `@property` via `db.session.get(...)`.
- **`AppNotification`** : la cloche de notification in-app (badge non-lu
  dans la sidebar) — **à ne pas confondre** avec `NotificationLog`
  (garde-fou anti-doublon des emails hebdomadaires, jamais affiché) ni
  avec `AuditLog` ci-dessous.
- **`AuditLog`** : append-only, jamais modifié après création
  (`updated_at` hérité de `BaseModel` mais toujours égal à `created_at`
  en pratique). `actor_id` nullable (aucune action de ce projet n'est
  aujourd'hui attribuée à un appelant système/non-authentifié, mais la
  colonne reste nullable par défaut prudent). Index composite sur
  `(resource_type, resource_id)` en plus des index simples sur
  `actor_id`/`action`. Seul point d'écriture : `AuditService.log()` — ne
  jamais insérer directement via le repository depuis une route/un
  service.
