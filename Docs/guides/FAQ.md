# FAQ

> Content verified against the actual code in Phase 5 (2026-07). Formerly
> a section of `USER_GUIDE.md`, extracted here to avoid duplication and
> corrected on several inaccurate points (see inline notes).

## Frequently Asked Questions

### How do I reset my password?

Contact your administrator — there is no self-service reset feature (no
"forgot password"). An administrator can set a new password via
**Admin > Users > Edit**.

### I don't see my shifts on the calendar

Check that:
1. You are logged in with the correct account.
2. Your shifts are actually assigned to your user.
3. The selected period covers your shifts — the home page calendar
   displays a ±180-day window around today; the **Schedule** page
   lists everything, with pagination.

### I can't add a shift for a user

Check that:
1. The user belongs to a group that participates in the schedule
   (`is_part_of_schedule`).
2. You are an administrator — only admins can add shifts
   (`/schedule/add`).
3. The shift type actually exists.
4. The period doesn't fall only on a weekend — shifts are only created
   for business days (Monday-Friday).

### I can't add a leave

Check that:
1. You are an administrator, or you are adding the leave for yourself
   (a non-admin can only create a leave for their own account).
2. The dates are valid (start ≤ end).
3. The leave doesn't overlap with an **other existing leave** for the
   same user.

> **Correction**: contrary to what previous versions of this guide
> documented, a leave that overlaps with an existing shift or on-call
> assignment **is not blocked** — the application automatically
> rebalances the affected shifts instead. Dates in the past are also
> accepted (no future-date check).

### ICS export isn't working

Check that:
1. Your ICS token is valid (regenerate it from **Profile > ICS Token**
   if needed).
2. The URL is correct (`scope=my` for your personal schedule,
   `scope=all` for everyone — requires being an admin or having an
   admin token to be useful).
3. Your calendar application supports ICS subscriptions by URL.

### How do I modify an existing shift/on-call/leave?

There is no dedicated edit form. Two options:
1. **Drag and drop on the calendar** (home page), in edit mode —
   **restricted to administrators**, including for a regular user's
   leaves.
2. Delete the entry and recreate a new one via the corresponding add
   form.

### How do I disable authentication for development?

In the `.env` file:

```bash
LOGIN_DISABLED=true
```

> ⚠️ **Never use this option in production!**

### What is the default administrator password?

`admin@kairos.local` / `admin123` — **but only if you copied
`.env.example` to `.env`** before the first startup (`cp .env.example .env`).
Without this file, `DEFAULT_ADMIN_PASSWORD` is not set and the
application generates a random password at startup, never displayed
anywhere. See
[`guides/QUICK_START.md`](QUICK_START.md).

## Technical Issues

### 404 Error (Page not found)

- Check that the URL is correct.
- Check that you are logged in.
- Check that you have the necessary permissions (some pages are
  restricted to administrators).

### 500 Error (Server error)

- Check the application logs (`logs/` locally, see
  [`reference/ERROR_HANDLING.md`](../reference/ERROR_HANDLING.md)).
- Contact the administrator.
- Report the bug on GitHub with reproduction steps.

### The database is not being created

- Check that the `instance/` folder exists and is writable:
  `mkdir -p instance`.
- Check that you actually copied `.env.example` to `.env`.

### Changes are not being saved

- Check that you clicked **"Save"**.
- Check that you have the necessary permissions.
- Check that no validation error is displayed (missing required
  field, invalid format).

### A POST request fails with "Bad Request" / unexpected 400 error

Since Phase 4, every write request (form or API call) requires a
valid CSRF token. If you are scripting calls to the application (curl,
automated requests) instead of using the interface, you must first
retrieve a CSRF token (hidden `csrf_token` field of the form, or
`<meta name="csrf-token">` tag) and include it in your request. See
[`api/API.md`](../api/API.md#authentication).

## Common Error Messages

| Message | Cause | Solution |
|---|---|---|
| "All fields are required" | A required field is empty | Fill in all fields marked as required |
| "Invalid date format" | The date is not in YYYY-MM-DD format | Use the format `2026-06-15` |
| "On-call must start on a Friday" | The start date is not a Friday | Select a Friday |
| "Cannot delete... associated data exists" | The item has dependencies (e.g. a user with shifts) | Delete the associated data first |
| "Incorrect email or password" | Invalid credentials | Check your email and password |
| "You can only add leaves for yourself" | Attempt to add a leave for another user (non-admin) | Log in as an admin, or add the leave for yourself |

## See Also

- [Quick Start Guide](QUICK_START.md)
- [User Guide](USER_GUIDE.md)
- [Administrator Guide](ADMIN_GUIDE.md)
