# Entity-Relationship Diagram (ERD)

Generated from `app/models/*.py` — the `id`, `created_at`, `updated_at`
fields are inherited from `BaseModel` (`app/models/base.py`) and common
to all tables below.

```mermaid
erDiagram
    GROUP ||--o{ USER : "has members"
    USER ||--o{ SHIFT : "assigned to"
    USER ||--o{ ON_CALL : "assigned to"
    USER ||--o{ LEAVE : "requests"
    USER ||--o{ NOTIFICATION_LOG : "receives"
    USER ||--o{ APP_NOTIFICATION : "receives"
    USER ||--o{ SWAP_REQUEST : "requester/target_user/reviewer (3 FK)"
    SHIFT ||--o{ SWAP_REQUEST : "shift/target_shift (2 FK)"
    USER ||--o{ AUDIT_LOG : "actor (nullable)"
    SHIFT_TYPE ||--o{ SHIFT : "defines the slot for"

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
        string password_hash "never serialized (to_dict)"
        bool is_admin
        int group_id FK
        string ics_token UK "nullable, never serialized"
        datetime ics_token_created_at "nullable, drives ICS_TOKEN_EXPIRY_DAYS enforcement"
        string timezone "nullable, falls back to Setting.default_timezone"
        string language "nullable String(5), falls back to Setting.default_language"
        string date_format "nullable, falls back to Setting.default_date_format"
        string time_format "nullable, falls back to Setting.default_time_format"
        bool shift_notifications_enabled "default true"
        bool oncall_notifications_enabled "default true"
        text apprise_shift_target_ids "nullable, JSON-encoded list of NotificationTarget ids"
        text apprise_oncall_target_ids "nullable, JSON-encoded list of NotificationTarget ids"
        datetime created_at
        datetime updated_at
    }

    SETTING {
        int id PK
        string key UK "e.g. default_timezone, notifications_enabled"
        text value "serialized (str/bool/int)"
        datetime created_at
        datetime updated_at
    }

    SWAP_REQUEST {
        int id PK
        int requester_id FK "to user.id"
        int target_user_id FK "to user.id"
        int reviewed_by_id FK "to user.id, nullable until processed"
        int shift_id FK "to shift.id"
        int target_shift_id FK "to shift.id, nullable (one-way give-away)"
        string status "PENDING/AWAITING_ADMIN/APPROVED/REJECTED/CANCELLED/REVERTED"
        text admin_comment "nullable"
        datetime reviewed_at "nullable"
        datetime created_at
        datetime updated_at
    }

    APP_NOTIFICATION {
        int id PK
        int user_id FK
        string notification_type "e.g. swap_request_created, swap_approved"
        text message
        string link "nullable, e.g. /admin/swaps"
        datetime read_at "nullable, null = unread"
        datetime created_at
        datetime updated_at
    }

    AUDIT_LOG {
        int id PK
        int actor_id FK "nullable, to user.id"
        string action "namespaced domain.verb, e.g. shift.create"
        string resource_type "nullable, e.g. Shift, User, Setting"
        int resource_id "nullable"
        text details "short summary, not a structured diff"
        string ip_address "nullable, IPv6-safe"
        datetime created_at
        datetime updated_at "inherited, never modified - append-only"
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
        datetime start_time "indexed"
        datetime end_time "indexed"
        date date "indexed"
        datetime created_at
        datetime updated_at
    }

    ON_CALL {
        int id PK
        int user_id FK
        datetime start_time "indexed"
        datetime end_time "indexed"
        datetime created_at
        datetime updated_at
    }

    LEAVE {
        int id PK
        int user_id FK
        date start_date "indexed"
        date end_date "indexed"
        datetime created_at
        datetime updated_at
    }

    AUTOMATION_CONFIG {
        int id PK
        string config_key UK
        text config_value "JSON encoded"
        datetime created_at
        datetime updated_at
    }

    NOTIFICATION_LOG {
        int id PK
        int user_id FK
        string notification_type "shift_weekly or oncall_weekly"
        date period_start "UK with user_id+notification_type"
        datetime created_at
        datetime updated_at
    }

    NOTIFICATION_TARGET {
        int id PK
        string name
        text apprise_url "Apprise service URL, treated as a secret - never logged"
        bool enabled "default true, indexed"
        text categories "nullable, JSON-encoded list; empty/null = all categories"
        datetime created_at
        datetime updated_at
    }

    SERVICE_ACCOUNT {
        int id PK
        string name
        text description "nullable"
        string token_prefix "first chars after ksak_, shown in the admin UI"
        string token_hash UK "SHA-256 of the full token, never the token itself"
        bool is_active "default true, indexed"
        datetime expires_at "nullable = never expires"
        datetime last_used_at "nullable, best-effort, admin UI only"
        datetime created_at
        datetime updated_at
    }
```

## Notes

- **`NotificationTarget`** and **`ServiceAccount`** have no FK
  relationship to any other table. `NotificationTarget` rows are picked
  by id in `User.apprise_shift_target_ids`/`apprise_oncall_target_ids`
  (a JSON-encoded list of ids on `User`, not a real foreign key —
  deleting a target silently drops it from any user's list on next
  read rather than cascading). `ServiceAccount` is a standalone bearer
  credential for the public `/api/v1/*` API, unrelated to `User`/
  Flask-Login sessions entirely.
- **`AutomationConfig`** has no relationship to the other tables:
  it's a generic key/value store (used to persist the on-call
  rotation order across restarts). Absent from any previous
  documentation despite its real use in
  `app/utils/automation/`.
- **`Leave` has no `reason` field** — the old API documentation
  described a `reason: string` field on leaves that never
  existed in the model.
- **`NotificationLog`**: unique constraint on
  `(user_id, notification_type, period_start)` - prevents a duplicate
  send if a notification script (`scripts/send_*_notifications.py`)
  is rerun for an already-processed period.
- **Composite indexes** (beyond the simple indexes listed above,
  defined in the model classes):
  - `Shift(user_id, date)` and `Shift(date, start_time)`
  - `OnCall(user_id, start_time, end_time)`
  - `Leave(user_id, start_date, end_date)`

  Preserve these indexes if you modify the query patterns in
  `app/repositories/`.
- **Cascade delete**: `Group.users`, `User.shifts`,
  `User.on_calls` and `User.leaves` are all declared
  `cascade="all, delete-orphan"` — deleting a group deletes its
  users, deleting a user deletes all their shifts/
  on-calls/leaves.
- **`Setting`**: generic key/value store (same shape as `AutomationConfig`)
  for admin settings editable at runtime from `/admin/settings`
  (timezone, language, date/time formats, public URL,
  pagination, notifications, backup/audit retention, ICS
  token expiry) — a present row always wins; its absence falls
  straight back to the corresponding environment variable/default value
  (`SettingsService`).
- **`SwapRequest`**: the first model in the project with several FKs to
  the same table (`requester_id`/`target_user_id`/`reviewed_by_id` → `User`).
  Deliberately **without** `db.relationship()` (a typing limitation of
  SQLAlchemy 2.0's stubs on relationships not configured with the
  dedicated mypy plugin) — `requester`/`target_user`/`reviewer`/`shift`/`target_shift`
  are plain `@property` lookups via `db.session.get(...)`.
- **`AppNotification`**: the in-app notification bell (unread badge
  in the sidebar) — **not to be confused** with `NotificationLog`
  (anti-duplicate guard for weekly emails, never displayed) nor
  with `AuditLog` below.
- **`AuditLog`**: append-only, never modified after creation
  (`updated_at` inherited from `BaseModel` but always equal to `created_at`
  in practice). `actor_id` nullable (no action in this project is
  currently attributed to a system/unauthenticated caller, but the
  column stays nullable as a cautious default). Composite index on
  `(resource_type, resource_id)` in addition to the simple indexes on
  `actor_id`/`action`. Single write point: `AuditService.log()` — never
  insert directly via the repository from a route/service.
