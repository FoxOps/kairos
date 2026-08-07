# Security audit v1.1

> Follow-up to `SECURITY_AUDIT_v1.0.md`, conducted as part of the
> production-readiness audit (see `ROADMAP.md`, "In progress"). Scope this
> time: authorization coverage (admin routes, IDOR on user-owned resources),
> authentication flows (session login, OIDC/SSO), CSRF/CSP/session
> configuration, the public API v1 (ServiceAccount tokens), and ICS export.
> Bandit/pip-audit (already run unconditionally in `make security`/CI) were
> re-run as a baseline, not re-litigated in depth here. Does not replace a
> pentest or a third-party audit.

## Summary

One high-severity and one medium-severity finding, both fixed in this pass
(OIDC identity spoofing via an unverified JWT fallback, and an OIDC-granted
admin role that was never revoked on sync). Everything else audited —
authorization coverage on every admin/session-owned route, CSRF, CSP,
Talisman, backup download path-traversal guard, ServiceAccount token
handling — was found already correctly implemented, verified directly
rather than assumed. Two lower-severity items (login brute-force
throttling, default-password policy) are documented as recommendations,
not fixed here — see "Findings not fixed" below.

## Fixes applied during this audit

### 1. HIGH — OIDC login trusted an unverified JWT payload as a fallback

`app/auth/oidc_auth.py::extract_user_info_from_token()` had two paths to
resolve a logged-in user's identity: the real, authenticated call to the
provider's userinfo endpoint (`user_info`, safe — TLS + the access token
obtained via a client-secret-authenticated token exchange), and, when that
wasn't available, a **manual base64 decode of the `id_token`/`access_token`
JWT payload with zero signature verification**. `verify_token()`'s name is
misleading: it only checks an `expires_at` timestamp, never a signature.

This module builds its OIDC client with Authlib
(`authlib.integrations.flask_client.OAuth`) but never actually uses
Authlib's own JWKS-verifying helpers — it reimplements the token/userinfo
calls with plain `requests` and, in the fallback path, trusted whatever
claims sat inside the JWT's payload, including a `roles: ["admin"]` claim.
A JWT's payload is base64, not encryption — anyone who can influence what
ends up in the decoded id_token (a network position on a non-TLS/misconfigured
issuer, or simply a scenario where the real userinfo call transiently
fails) could have forged arbitrary claims, up to and including admin
access, without ever needing a valid signature.

**Fix**: removed the manual-decode fallback entirely. If the userinfo
endpoint can't be reached or the token exchange didn't yield an access
token, the login now fails closed (matches the existing "could not fetch
email" error path) instead of trusting unverified data. Regression tests
added: `test_does_not_trust_unverified_id_token_payload` (unit) and
`test_fails_closed_when_userinfo_endpoint_unreachable` (integration-shaped,
exercises the full `handle_oauth_callback` path with a forged admin-role
JWT and a failing userinfo call) — both verified red before the fix,
green after.

### 2. MEDIUM — OIDC-granted admin role was never revoked

`app/auth/user_manager.py::_sync_user_roles()` runs on every OIDC login
(new and existing users alike) and granted `is_admin = True` when
`"admin"` was present in the configured roles claim — but never set it
back to `False` when the claim no longer contained it. A user promoted to
admin via their IdP's role assignment kept local admin rights indefinitely
after that role was revoked at the IdP, until a Kairos admin manually
caught it and fixed it by hand at `/admin/users` — silent privilege
persistence, not by design.

**Fix**: `is_admin` is now set both ways from the presence/absence of the
`admin` role on every sync, not just granted. Regression test added:
`test_existing_admin_role_is_revoked_via_oidc_sync` (verified red before,
green after) alongside the existing grant-side test.

## Findings not fixed (recommendations)

These are real gaps, but policy/product decisions with UX tradeoffs, not
one-line bug fixes — flagging them here rather than changing behavior
unilaterally.

### 3. No login-specific brute-force throttling

> **Correction (see `PENTEST_v1.md`)**: this finding assumed the app-wide
> default rate limit was actually being enforced. A live pentest found it
> wasn't — a real ordering bug (`app.config["RATELIMIT_DEFAULT"]` was set
> *after* `limiter.init_app(app)` had already run, so Flask-Limiter never
> saw it) meant **no rate limit was enforced anywhere in the app**, not
> even the 50/hour bound this finding describes below. That bug is now
> fixed (`app/__init__.py`, verified live: 50 requests succeed, the 51st+
> get `429`). The observation below (no *login-specific*, stricter limit
> on top of the generic default) still stands as a recommendation.

`/login` is only covered by the app-wide default rate limit
(`RATE_LIMIT_DEFAULT`, 200/day · 50/hour per IP) — there is no
login-specific stricter limit and no account lockout after repeated
failures. 50 attempts/hour per IP is a real but not tight bound for
password guessing. A dedicated `@limiter.limit("5 per minute")` (or
similar) on the `/login` POST path, layered on top of the existing global
default, would close this without touching the rest of the app's rate
limiting.

### 4. Weak, disclosed default password for admin-created users

`UserService.create()` (`app/services/user_service.py`) falls back to a
hardcoded `"password123"` when an admin creates a user without setting a
password. This is disclosed to the admin in the UI
(`add_user.html`'s help text literally shows `password123`), not a hidden
default — but there is no minimum password length/strength check anywhere
in the app (`User.set_password()` accepts any non-empty string), and no
forced-password-change-on-first-login mechanism. Between account creation
and the new user's first login, any account left on the default password
is guessable by anyone who also knows (or enumerates) the email. A
`must_change_password` flag checked at login, plus a minimum length
check in `set_password()`/the profile-update route, would close this.

## Confirmed already correct (verified, not assumed)

- **Admin route authorization**: every one of the 44 `@admin_bp.route(...)`
  endpoints across `app/routes/admin_*.py` carries `@admin_required`
  (`login_required` + `is_admin` check) — verified by parsing every route
  definition and its decorator stack programmatically, not by sampling.
- **IDOR on user-owned resources**: shift/on-call writes are admin-only
  (`@admin_required` on every create/update/delete route — regular users
  have no direct write path to spoof); leave read/write routes check
  `current_user.is_admin or current_user.id == resource.user_id` on every
  mutating route (`api_delete_leave`, `api_update_leave`, and the
  `user_owns_resource` decorator on `delete_leave`); swap confirm/reject
  check `target_user_id == current_user.id`, cancel is delegated to
  `SwapService.cancel_swap()` which checks `requester_id == user.id or
  user.is_admin`.
- **CSRF**: `Flask-WTF` `CSRFProtect` active app-wide; the only exemption
  (`app/api/` flask-smorest blueprints) is justified — that surface never
  accepts cookie-based auth, so the cross-site-request-with-a-valid-cookie
  risk CSRF protects against doesn't apply there.
- **CSP/Talisman**: `script-src 'self' <CDN hosts>` (no `'unsafe-inline'`
  for actual `<script>` tags — only `script-src-attr`/`style-src` allow
  inline, for static developer-written `onclick=`/one dynamic style, never
  user data), `object-src 'none'`, security headers always active
  regardless of `TALISMAN_FORCE_HTTPS` (a prior real bug, already fixed
  before this pass — see `SECURITY_AUDIT_v1.0.md`).
- **Password hashing**: Werkzeug `generate_password_hash`/`check_password_hash`
  (scrypt by default), timing-safe comparison, never logged/serialized
  (`User.to_dict()` excludes `password_hash`).
- **Open redirect**: `auth.py::_is_safe_next_url()` validates the
  post-login `?next=` parameter's scheme+netloc against the request's own
  host before honoring it — a classic CWE-601 vector already closed.
- **OIDC state/nonce**: `get_authorization_url()` generates and
  session-stores a random `state`/`nonce` (`secrets.token_urlsafe(32)`
  each); `handle_oauth_callback()` rejects the callback outright if the
  returned `state` doesn't match the session's — standard CSRF protection
  for the OAuth redirect itself.
- **ServiceAccount (public API v1) tokens**: SHA-256 hash lookup (never
  the plaintext token stored), `is_valid()` checked (active + not expired)
  on every request via `resolve_service_account()`, always fails with a
  JSON 401 (never an HTML redirect that could leak session-oriented
  behavior into a token-only client).
- **Backup download path traversal**: `BackupService.get_local_backup_path()`
  requires the filename to start with the configured backup prefix,
  resolves it against the backup directory, and rejects anything whose
  resolved absolute path doesn't stay under that directory — verified by
  reading the actual containment check, not just its docstring.
- **Static analysis baseline**: `bandit -r app/` — 0 findings. `pip-audit -r
  requirements.txt` — no known vulnerabilities. Both already run
  unconditionally in `make security` and the CI `security` job (see
  `CLAUDE.md`).

## Out of scope for this pass

- Full penetration test / third-party audit.
- Dependency supply-chain review beyond `pip-audit`'s CVE database (e.g. no
  SBOM generation, no manual review of transitive dependency source).
- Infrastructure-level review (reverse proxy configuration, TLS cipher
  suites, container image hardening beyond the non-root `appuser` already
  documented in `Docs/deployment/docker.md`).
