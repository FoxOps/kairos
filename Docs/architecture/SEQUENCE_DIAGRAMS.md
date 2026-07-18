# Sequence Diagrams

Key user flows, traced from the actual code (`app/routes/`,
`app/services/`, `app/auth/`).

## Basic login (email/password)

```mermaid
sequenceDiagram
    actor U as User
    participant B as Browser
    participant R as auth.py (route /login)
    participant FL as Flask-Login
    participant DB as Database

    U->>B: Opens /login
    B->>R: GET /login
    R-->>B: HTML form + csrf_token field
    U->>B: Enters email/password, submits
    B->>R: POST /login (email, password, csrf_token)
    Note over R: CSRFProtect verifies the token before<br/>even entering the view (400 if invalid)
    R->>DB: User.query.filter_by(email=...).first()
    DB-->>R: User (or None)
    alt user found and password correct
        R->>FL: login_user(user, remember=...)
        FL-->>R: session created
        R-->>B: 302 redirect to next or /
    else failure
        R-->>B: 200, form + "Incorrect email or password"
    end
```

## OIDC/SSO login

```mermaid
sequenceDiagram
    actor U as User
    participant B as Browser
    participant R as auth.py
    participant O as oidc_auth.py (Authlib)
    participant IdP as OIDC provider
    participant UM as UserManager

    U->>B: Opens /login
    B->>R: GET /login
    Note over R: is_basic_auth_disabled() true<br/>(OIDC_ENABLED + OIDC_DISABLE_BASIC_AUTH)
    R-->>B: 302 redirect /oidc/login
    B->>R: GET /oidc/login
    R->>O: get_authorization_url()
    O-->>R: Authorization URL (with state/nonce)
    R-->>B: 302 redirect to the IdP
    B->>IdP: User authentication
    IdP-->>B: 302 redirect /oidc/callback?code=...
    B->>R: GET /oidc/callback
    R->>O: handle_oauth_callback(request)
    O->>IdP: Exchange code for token (+ userinfo)
    IdP-->>O: id_token, access_token, user claims
    O-->>R: user_data (or None on failure)
    R->>O: login_user(user_data)
    O->>UM: sync_user_from_oidc(user_data)
    UM->>UM: Creates or updates the local User
    UM-->>O: User
    O-->>R: User (or None)
    R-->>B: 302 redirect / (Flask-Login session created)
```

## Adding leave with automatic shift rebalancing

```mermaid
sequenceDiagram
    actor U as User
    participant R as leave_routes.py
    participant LS as LeaveService
    participant LR as LeaveRepository
    participant ASA as AdvancedShiftAutomation
    participant DB as Database

    U->>R: POST /leave/add (user_id, start_date, end_date)
    Note over R: Checks permission:<br/>a non-admin can only act on their own behalf
    R->>LS: add_leave(target_user, start_date, end_date)
    LS->>LS: can_add_leave(...) — no overlap,<br/>consistent dates
    alt validation fails
        LS-->>R: (None, None)
        R-->>U: Flash "Unable to add this leave"
    else validation OK
        LS->>LR: create(user_id, start_date, end_date)
        LR->>DB: INSERT Leave
        LS->>DB: commit()
        LS->>ASA: rebalance_after_leave(leave, dry_run=False)
        Note over ASA: Recalculates shifts affected by<br/>the absence (reassignment if needed)
        ASA-->>LS: (regenerated_shifts, messages)
        LS-->>R: (leave, regenerated_shifts)
        R-->>U: Flash "Leave added, N shifts recalculated"
    end
```

## Updating a shift via drag-and-drop (JSON API + CSRF)

```mermaid
sequenceDiagram
    actor U as User (admin)
    participant JS as index.html (FullCalendar JS)
    participant R as shift_routes.py
    participant SS as ShiftService
    participant SR as ShiftRepository
    participant DB as Database

    U->>JS: Drags a shift to a new date
    JS->>JS: Reads the token from <meta name="csrf-token">
    JS->>R: PATCH /api/shifts/<id><br/>{start, end}, X-CSRFToken header
    Note over R: CSRFProtect verifies the header<br/>(400 if missing/invalid)
    R->>SR: get_by_id(shift_id)
    SR->>DB: SELECT
    DB-->>SR: Shift (or None)
    alt shift not found
        R-->>JS: 404 {"success": false, "error": "Shift not found"}
    else
        R->>SS: api_update(shift_id, new_start, new_end)
        SS->>SS: Rejects weekends,<br/>checks conflicts (find_conflict)
        alt conflict or weekend
            SS-->>R: (None, error message)
            R-->>JS: 400 {"success": false, "error": "..."}
        else OK
            SS->>DB: UPDATE Shift, commit()
            SS-->>R: (shift, None)
            R-->>JS: 200 {"success": true, "shift": {...}}
            JS->>JS: location.reload() to resync
        end
    end
```

## ICS export (session or bearer token)

```mermaid
sequenceDiagram
    actor U as User or external calendar app
    participant R as export.py
    participant ES as ExportService
    participant UR as UserRepository
    participant Ex as ics_exporter.py

    U->>R: GET /export/shifts?scope=my&token=... (or session cookie)
    R->>ES: resolve_user(token)
    alt authenticated session
        ES-->>R: current_user
    else token provided
        ES->>UR: get_by_ics_token(token)
        UR-->>ES: User (or None)
        ES-->>R: User or None
    end
    alt no user resolved
        R-->>U: 401 Unauthorized
    else
        R->>ES: export_shifts(scope, user)
        ES->>Ex: export_to_ics(shifts, title)
        Ex-->>ES: .ics content
        ES-->>R: .ics content
        R-->>U: 200, Content-Type: text/calendar
    end
```
