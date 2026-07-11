# Schéma entité-relation (ERD)

Généré à partir de `app/models/*.py` (Phase 5, 2026-07) — les champs
`id`, `created_at`, `updated_at` sont hérités de `BaseModel`
(`app/models/base.py`) et communs à toutes les tables ci-dessous.

```mermaid
erDiagram
    GROUP ||--o{ USER : "a pour membres"
    USER ||--o{ SHIFT : "assigné à"
    USER ||--o{ ON_CALL : "assigné à"
    USER ||--o{ LEAVE : "demande"
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
        datetime created_at
        datetime updated_at
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
