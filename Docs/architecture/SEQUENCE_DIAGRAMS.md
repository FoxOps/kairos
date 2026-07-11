# Diagrammes de séquence

Flux utilisateur clés, tracés à partir du code réel (`app/routes/`,
`app/services/`, `app/auth/`) — Phase 5, 2026-07.

## Connexion basique (email/mot de passe)

```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant B as Navigateur
    participant R as auth.py (route /login)
    participant FL as Flask-Login
    participant DB as Base de données

    U->>B: Ouvre /login
    B->>R: GET /login
    R-->>B: Formulaire HTML + champ csrf_token
    U->>B: Saisit email/mot de passe, soumet
    B->>R: POST /login (email, password, csrf_token)
    Note over R: CSRFProtect vérifie le token avant<br/>même d'entrer dans la vue (400 si invalide)
    R->>DB: User.query.filter_by(email=...).first()
    DB-->>R: User (ou None)
    alt utilisateur trouvé et mot de passe correct
        R->>FL: login_user(user, remember=...)
        FL-->>R: session créée
        R-->>B: 302 redirect vers next ou /
    else échec
        R-->>B: 200, formulaire + "Email ou mot de passe incorrect"
    end
```

## Connexion OIDC/SSO

```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant B as Navigateur
    participant R as auth.py
    participant O as oidc_auth.py (Authlib)
    participant IdP as Fournisseur OIDC
    participant UM as UserManager

    U->>B: Ouvre /login
    B->>R: GET /login
    Note over R: is_basic_auth_disabled() vrai<br/>(OIDC_ENABLED + OIDC_DISABLE_BASIC_AUTH)
    R-->>B: 302 redirect /oidc/login
    B->>R: GET /oidc/login
    R->>O: get_authorization_url()
    O-->>R: URL d'autorisation (avec state/nonce)
    R-->>B: 302 redirect vers l'IdP
    B->>IdP: Authentification utilisateur
    IdP-->>B: 302 redirect /oidc/callback?code=...
    B->>R: GET /oidc/callback
    R->>O: handle_oauth_callback(request)
    O->>IdP: Échange code contre token (+ userinfo)
    IdP-->>O: id_token, access_token, claims utilisateur
    O-->>R: user_data (ou None si échec)
    R->>O: login_user(user_data)
    O->>UM: sync_user_from_oidc(user_data)
    UM->>UM: Crée ou met à jour le User local
    UM-->>O: User
    O-->>R: User (ou None)
    R-->>B: 302 redirect / (session Flask-Login créée)
```

## Ajout de congé avec rééquilibrage automatique des shifts

```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant R as leave_routes.py
    participant LS as LeaveService
    participant LR as LeaveRepository
    participant ASA as AdvancedShiftAutomation
    participant DB as Base de données

    U->>R: POST /leave/add (user_id, start_date, end_date)
    Note over R: Vérifie permission :<br/>non-admin ne peut agir que pour lui-même
    R->>LS: add_leave(target_user, start_date, end_date)
    LS->>LS: can_add_leave(...) — pas de chevauchement,<br/>dates cohérentes
    alt validation échoue
        LS-->>R: (None, None)
        R-->>U: Flash "Impossible d'ajouter ce congé"
    else validation OK
        LS->>LR: create(user_id, start_date, end_date)
        LR->>DB: INSERT Leave
        LS->>DB: commit()
        LS->>ASA: rebalance_after_leave(leave, dry_run=False)
        Note over ASA: Recalcule les shifts affectés par<br/>l'absence (réassignation si nécessaire)
        ASA-->>LS: (regenerated_shifts, messages)
        LS-->>R: (leave, regenerated_shifts)
        R-->>U: Flash "Congé ajouté, N shifts recalculés"
    end
```

## Mise à jour d'un shift par glisser-déposer (API JSON + CSRF)

```mermaid
sequenceDiagram
    actor U as Utilisateur (admin)
    participant JS as index.html (FullCalendar JS)
    participant R as shift_routes.py
    participant SS as ShiftService
    participant SR as ShiftRepository
    participant DB as Base de données

    U->>JS: Glisse un shift vers une nouvelle date
    JS->>JS: Lit le token depuis <meta name="csrf-token">
    JS->>R: PATCH /api/shifts/<id><br/>{start, end}, en-tête X-CSRFToken
    Note over R: CSRFProtect vérifie l'en-tête<br/>(400 si absent/invalide)
    R->>SR: get_by_id(shift_id)
    SR->>DB: SELECT
    DB-->>SR: Shift (ou None)
    alt shift introuvable
        R-->>JS: 404 {"success": false, "error": "Shift non trouvé"}
    else
        R->>SS: api_update(shift_id, new_start, new_end)
        SS->>SS: Rejette les week-ends,<br/>vérifie les conflits (find_conflict)
        alt conflit ou week-end
            SS-->>R: (None, message d'erreur)
            R-->>JS: 400 {"success": false, "error": "..."}
        else OK
            SS->>DB: UPDATE Shift, commit()
            SS-->>R: (shift, None)
            R-->>JS: 200 {"success": true, "shift": {...}}
            JS->>JS: location.reload() pour resynchroniser
        end
    end
```

## Export ICS (session ou token porteur)

```mermaid
sequenceDiagram
    actor U as Utilisateur ou app calendrier externe
    participant R as export.py
    participant ES as ExportService
    participant UR as UserRepository
    participant Ex as ics_exporter.py

    U->>R: GET /export/shifts?scope=my&token=... (ou cookie de session)
    R->>ES: resolve_user(token)
    alt session authentifiée
        ES-->>R: current_user
    else token fourni
        ES->>UR: get_by_ics_token(token)
        UR-->>ES: User (ou None)
        ES-->>R: User ou None
    end
    alt aucun utilisateur résolu
        R-->>U: 401 Unauthorized
    else
        R->>ES: export_shifts(scope, user)
        ES->>Ex: export_to_ics(shifts, titre)
        Ex-->>ES: contenu .ics
        ES-->>R: contenu .ics
        R-->>U: 200, Content-Type: text/calendar
    end
```
