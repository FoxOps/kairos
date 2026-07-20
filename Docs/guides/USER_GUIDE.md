# 📖 Complete User Guide - Kairos

> **Version**: 1.0.0 - User Documentation
> **Last updated**: June 2026
> **Application**: Kairos v1.0.0-rc2 (`app/utils/health.py::APP_VERSION_DEFAULT`, also shown at `/version` and in the app footer)

---

## 📋 Table of Contents

1. [🎯 Introduction](#-introduction)
2. [📥 Installation and Configuration](#-installation-and-configuration)
3. [🔐 Authentication](#-authentication)
4. [🏠 User Interface](#-user-interface)
5. [👥 User Management](#-user-management)
6. [🏢 Group Management](#-group-management)
7. [⚙️ Shift Type Management](#️-shift-type-management)
8. [📅 Shift Management](#-shift-management)
9. [🚨 On-Call Management](#-on-call-management)
10. [🏖️ Leave Management](#-leave-management)
11. [📤 ICS Export and Calendar Integration](#-ics-export-and-calendar-integration)
12. [⚡ Advanced Automation](#-advanced-automation)
13. [📊 Administrator Dashboard](#-administrator-dashboard)
14. [❓ FAQ and Troubleshooting](#-faq-and-troubleshooting)
15. [📞 Support and Contact](#-support-and-contact)

---

## 🎯 Introduction

### What is Kairos?

**Kairos** is a complete web application for managing schedules, on-call rotations, and leave, designed for teams and organizations. It allows you to:

- ✅ **Manage users**: Creation, modification, and organization into groups
- ✅ **Plan shifts**: Assignment of work schedules to team members
- ✅ **Organize on-call rotations**: Planning of on-call rotations
- ✅ **Manage leave**: Entry and visualization of absence periods
- ✅ **Export data**: Integration with Google Calendar, Outlook, etc.
- ✅ **Automate**: Automatic schedule generation based on business rules

### Target Audience

- **Administrators**: Full management of the application, users, and configurations
- **Team leads**: Scheduling shifts and on-call rotations
- **Standard users**: Viewing their schedule, managing their leave

### Technical Requirements

| Element | Requirement |
|---------|-------------|
| **Browser** | Chrome, Firefox, Edge, Safari (recent versions) |
| **JavaScript** | Enabled |
| **Cookies** | Enabled |
| **Resolution** | 1280x720 minimum (recommended) |

---

## 📥 Installation and Configuration

### Local Installation (For Developers)

#### 1. Clone the repository

```bash
git clone https://github.com/FoxOps/leviia-schedule.git
cd leviia-schedule
```

#### 2. Create a virtual environment

```bash
# On Linux/macOS
python -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure the application

Copy the example file, which already contains working development values
(including `DEFAULT_ADMIN_PASSWORD=admin123`, without which a random,
unshown admin password would be generated) - but see the important
warning in step 5 below: this file must actually be *loaded* into the
process environment, which a plain `python run.py` does not do on its
own:

```bash
cp .env.example .env
```

Variables to know about for a first installation (all already present in
`.env.example`, adjust as needed):

```bash
# Secret key (generate a new one for each installation)
SECRET_KEY=your-secret-key-here

# Database configuration (SQLite by default)
DATABASE_URL=sqlite:///app.db

# Disable authentication (development ONLY)
LOGIN_DISABLED=false
```

To generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Full list of variables: see
[`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md).

#### 5. Start the application

> ⚠️ **`.env` is not loaded automatically by `python run.py`**: there is
> no `load_dotenv()` call anywhere in this app, so a plain `python run.py`
> silently ignores everything in `.env` (confirmed by testing: values
> placed in `.env` are not seen by `Config`). Use the `dotenv` CLI that
> ships with the `python-dotenv` dependency already in `requirements.txt`,
> or export the variables into your shell yourself.

```bash
dotenv run -- python run.py
# or: set -a && source .env && set +a && python run.py
```

> **Note**: The first run will automatically create (see
> `run.py::create_default_data`):
> - A default administrator user
>   (email `DEFAULT_ADMIN_EMAIL`, password `DEFAULT_ADMIN_PASSWORD` —
>   `admin@kairos.local` / `admin123` with the values from `.env.example`,
>   **only if `.env` was actually loaded** as described above - otherwise
>   both fall back to a freshly-generated random value, with the password
>   never displayed anywhere)
> - A default group
> - Default shift types (see "Shift Type Management" below for their real
>   names/hours)

The application will be accessible at: **http://localhost:5000**

### Advanced Configuration

#### Using PostgreSQL

1. Install PostgreSQL and create a database:
   ```bash
   sudo apt-get install postgresql postgresql-contrib
   sudo -u postgres createdb kairos
   sudo -u postgres createuser kairos_user
   ```

2. Edit the configuration in `.env`:
   ```bash
   DATABASE_URL=postgresql://kairos_user:password@localhost/kairos
   ```

3. The PostgreSQL driver (`psycopg[binary]`, psycopg 3) is already included in
   `requirements.txt` - no separate install step is needed if you followed
   step 3 of the installation above.

See also [`deployment/DEPLOYMENT_ADVANCED.md`](../deployment/DEPLOYMENT_ADVANCED.md)
for a complete production PostgreSQL configuration.

#### Environment variables

| Variable | Description | Default value |
|----------|-------------|------------------|
| `SECRET_KEY` | Secret key for security | Randomly generated if absent |
| `DATABASE_URL` | Database URI | `sqlite:///app.db` |
| `LOGIN_DISABLED` | Disables authentication (dev only) | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

Full list: [`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md).

---

## 🔐 Authentication

### First Login

1. Access the application via your browser: **http://localhost:5000**
2. Log in with the default credentials:
   - **Email**: `admin@kairos.local`
   - **Password**: `admin123`

> ⚠️ **IMPORTANT**: Change the password immediately after the first login.

### Login

1. Click the **"Login"** link or go directly to `/login`
2. Enter your email and password
3. Click **"Log in"**
4. Check **"Remember me"** to stay logged in (optional)

### Logout

1. Click your username in the navigation menu
2. Select **"Logout"**

### Forgotten password

> ⚠️ **Feature not implemented**: Contact your administrator to reset your password.

### Profile Management

#### Viewing your profile

1. Click your username in the menu
2. Select **"Profile"**
3. You will see your personal information:
   - Name
   - Email
   - Group
   - Role (Administrator/User)

#### Updating your profile

1. Go to **"Profile"** > **"Edit profile"**
2. Edit the fields you want:
   - **Name**: Your full name
   - **Email**: Your email address
   - **Current password**: Required to change your password
   - **New password**: New password (optional)
   - **Confirm password**: Confirmation of the new password
3. Click **"Save"**

#### Generating an ICS Token

To export your schedule to an external calendar:

1. Go to **"Profile"** > **"ICS Token"**
2. Click **"Generate a token"**
3. Copy the generated token
4. Use it in the export URL: `/export/shifts?scope=my&token=YOUR_TOKEN`

> 💡 **Tip**: Keep your token secret. It grants access to your schedule data.

---

## 🏠 User Interface

### Interface structure

```
┌─────────────────────────────────────────────────────────────┐
│  🔹 Kairos    [Home] [Schedule] [On-Call] [Leave] │
├─────────────────────────────────────────────────────────────┤
│  🏠 Home │ 📅 Schedule │ 🚨 On-Call │ 🏖️ Leave          │
├─────────────────────────────────────────────────────────────┤
│                                                                 │
│                    MAIN CONTENT                           │
│                                                                 │
├─────────────────────────────────────────────────────────────┤
│  © 2026 FoxOps | User: Jean Dupont [Logout]│
└─────────────────────────────────────────────────────────────┘
```

### Navigation Menu

| Element | Description | Access |
|---------|-------------|-------|
| **Home** | Dashboard with calendar | All |
| **Schedule** | List and management of shifts | All |
| **On-Call** | List and management of on-call periods | All |
| **Leave** | List and management of leave | All |
| **Admin** | Administrator dashboard | Admin only |

### Toolbar

- **Notifications**: Displays messages and alerts
- **Profile**: Access to your user profile
- **Logout**: Exit the application

---

## 👥 User Management

> ⚠️ **Administrators only**

### Listing users

1. Go to **Admin** > **Users**
2. You will see the list of all users with:
   - Name
   - Email
   - Group
   - Role (Admin/User)
   - Number of shifts, on-call periods, and leave
3. Use the search bar to filter users

### Adding a user

1. Go to **Admin** > **Users** > **Add**
2. Fill in the form:
   - **Name** (required): The user's full name
   - **Email** (required): Unique email address
   - **Group** (required): Select an existing group
   - **Password** (optional): Leave blank for a default password (`password123`)
   - **Administrator**: Check to grant admin rights
3. Click **"Save"**

> 💡 **Tip**: If you don't specify a password, the user is created with the default password `password123` - there is no forced password-change prompt on first login, so communicate this password to the user and ask them to change it manually from their profile.

### Editing a user

1. Go to **Admin** > **Users**
2. Click the **✏️ Edit** icon next to the user
3. Edit the fields you want
4. Click **"Save"**

### Deleting a user

1. Go to **Admin** > **Users**
2. Click the **🗑️ Delete** icon next to the user
3. Confirm the deletion

> ⚠️ **Warning**: You cannot delete a user who has associated shifts, on-call periods, or leave. Delete their data first.

---

## 🏢 Group Management

> ⚠️ **Administrators only**

### What are groups for?

Groups allow you to:
- Organize users by team or department
- Apply specific rules to certain groups
- Control which users participate in shifts and on-call rotations

### Listing groups

1. Go to **Admin** > **Groups**
2. You will see the list of all groups with:
   - Name
   - Schedule participation (Shifts)
   - On-call participation
   - Number of users

### Adding a group

1. Go to **Admin** > **Groups** > **Add**
2. Fill in the form:
   - **Name** (required): Group name
   - **Participates in schedule**: Check if members can have shifts
   - **Participates in on-call**: Check if members can be on call
3. Click **"Save"**

### Editing a group

1. Go to **Admin** > **Groups**
2. Click the **✏️ Edit** icon next to the group
3. Edit the fields you want
4. Click **"Save"**

### Deleting a group

1. Go to **Admin** > **Groups**
2. Click the **🗑️ Delete** icon next to the group
3. Confirm the deletion

> ⚠️ **Warning**: You cannot delete a group that contains users. First move the users to another group.

---

## ⚙️ Shift Type Management

> ⚠️ **Administrators only**

### What is a shift type?

A shift type defines:
- A unique name (e.g. `morning`, `afternoon`, `evening`)
- A displayed label (e.g. "Morning", "Afternoon", "Evening")
- A start time (e.g. 8 for 8:00 AM)
- An end time (e.g. 12 for 12:00 PM)

### Default shift types

The application automatically creates 3 shift types:

| Name | Label | Start time | End time |
|-----|---------|----------------|--------------|
| `morning` | `07h-15h` | 7:00 AM | 3:00 PM |
| `afternoon` | `09h-17h` | 9:00 AM | 5:00 PM |
| `evening` | `13h-21h` | 1:00 PM | 9:00 PM |

### Listing shift types

1. Go to **Admin** > **Shift Types**
2. You will see the list of all configured shift types

### Adding a shift type

1. Go to **Admin** > **Shift Types** > **Add**
2. Fill in the form:
   - **Name** (required): Unique identifier (no spaces, e.g. `night`)
   - **Label** (required): Displayed name (e.g. "Night")
   - **Start time** (required): Hour between 0 and 23
   - **End time** (required): Hour between 0 and 23, must be > start time
3. Click **"Save"**

### Editing a shift type

1. Go to **Admin** > **Shift Types**
2. Click the **✏️ Edit** icon next to the shift type
3. Edit the fields you want
4. Click **"Save"**

### Deleting a shift type

1. Go to **Admin** > **Shift Types**
2. Click the **🗑️ Delete** icon next to the shift type
3. Confirm the deletion

> ⚠️ **Warning**: You cannot delete a shift type that is used in existing shifts. Delete the shifts using it first.

---

## 📅 Shift Management

### What is a shift?

A shift represents a work period assigned to a user for a specific day. It contains:
- A user
- A shift type (morning, afternoon, evening)
- A date
- A start time and end time

### Viewing the schedule

#### Method 1: Interactive calendar (Home page)

1. Go to the **Home** page
2. You will see a calendar with:
   - **Shifts**: Displayed in purple (theme primary color)
   - **On-Call**: Displayed in cyan (theme info color)
   - **Leave**: Displayed in red (theme error/danger color)
3. Navigate between months using the arrows
4. Click an event for more details

#### Method 2: List of shifts

1. Go to **Schedule**
2. You will see the list of all shifts with:
   - Date
   - User
   - Shift type
   - Start and end time
3. Use pagination to navigate
4. Use the search filter to find specific shifts

### Adding a shift (Administrator)

1. Go to **Schedule** > **Add a shift**
2. Fill in the form:
   - **User** (required): Select an eligible user
   - **Shift type** (required): Select a shift type
   - **Start date** (required): Start date of the period
   - **End date** (required): End date of the period
3. Click **"Save"**

> 💡 **Tip**: You can add shifts for a multi-day period. The application will automatically create a shift for each business day (Monday-Friday) within the period.

### Adding a shift for a single day

1. Go to **Schedule** > **Add a shift**
2. Select the same date for the start and end
3. Choose the user and shift type
4. Click **"Save"**

### Editing a shift

**Administrator only.** On the home page calendar, enable **edit mode**,
then drag and drop the shift to its new date/time, or resize it to
change its duration. The change is saved immediately (no separate
"Save" button).

There is no dedicated editing form (no "Edit this shift" page) — only
drag-and-drop on the calendar allows direct modification. Otherwise,
delete the shift and create a new one via **Schedule > Add a shift**.

### Deleting a shift

1. Go to **Schedule**
2. Find the shift to delete
3. Click the **🗑️ Delete** icon
4. Confirm the deletion

### Deleting multiple shifts

#### Deleting all shifts for a user

1. Go to **Schedule**
2. Click **"Delete all shifts for [Name]"**
3. Confirm the deletion

#### Deleting all shifts for a day

1. Go to **Schedule**
2. Click **"Delete all shifts for [Date]"**
3. Confirm the deletion

#### Deleting all shifts for a week

1. Go to **Schedule**
2. Click **"Delete all shifts for the week of [Date]"**
3. Confirm the deletion

#### Deleting ALL shifts

1. Go to **Schedule**
2. Click **"Delete all shifts"**
3. Confirm the deletion

> ⚠️ **Warning**: This action is irreversible!

---

## 🚨 On-Call Management

### What is an on-call period?

An on-call period is a time during which a user is responsible and reachable outside normal working hours. In Kairos:

- On-call periods start **on Friday at 9:00 PM**
- On-call periods end **the following Friday at 7:00 AM** (i.e. 7 days minus 14 hours)
- Every eligible user can be on call

### Viewing on-call periods

#### Method 1: Interactive calendar (Home page)

1. Go to the **Home** page
2. On-call periods are displayed in **cyan** in the calendar
3. Hover over an on-call period to see the details

#### Method 2: List of on-call periods

1. Go to **On-Call**
2. You will see the list of all on-call periods with:
   - Period (start date to end date)
   - Responsible user
   - Duration
3. Use pagination to navigate

### Adding an on-call period (Administrator)

1. Go to **On-Call** > **Add an on-call period**
2. Fill in the form:
   - **User** (required): Select an eligible user (member of a group participating in on-call)
   - **Start date** (required): **Must be a Friday** (the application checks this)
3. Click **"Save"**

> 💡 **Tip**: The application automatically calculates the end date (7 days after Friday 9:00 PM, i.e. the following Friday at 7:00 AM).

### Editing an on-call period

**Administrator only.** Same as for shifts: enable edit mode on the
home page calendar, then drag and drop the on-call period. No dedicated
editing form — otherwise, delete it and recreate it via
**On-Call > Add an on-call period**.

### Deleting an on-call period

1. Go to **On-Call**
2. Find the on-call period to delete
3. Click the **🗑️ Delete** icon
4. Confirm the deletion

### Deleting multiple on-call periods

#### Deleting all on-call periods for a user

1. Go to **On-Call**
2. Click **"Delete all on-call periods for [Name]"**
3. Confirm the deletion

#### Deleting ALL on-call periods

1. Go to **On-Call**
2. Click **"Delete all on-call periods"**
3. Confirm the deletion

> ⚠️ **Warning**: This action is irreversible!

---

## 🏖️ Leave Management

### What is a leave period?

A leave period represents a period of absence for a user. It can be:
- Paid leave
- Sick leave
- RTT (compensatory time off)
- Other types of absence

### Viewing leave

#### Method 1: Interactive calendar (Home page)

1. Go to the **Home** page
2. Leave periods are displayed in **red** in the calendar
3. Hover over a leave period to see the details

#### Method 2: List of leave periods

1. Go to **Leave**
2. You will see the list of all leave periods with:
   - Period (start date to end date)
   - User
   - Duration
3. Use pagination to navigate

### Adding a leave period

#### For yourself (All users)

1. Go to **Leave** > **Add a leave period**
2. Fill in the form:
   - **User**: Your name (pre-selected)
   - **Start date** (required): First day of leave
   - **End date** (required): Last day of leave
3. Click **"Save"**

#### For another user (Administrator)

1. Go to **Leave** > **Add a leave period**
2. Select the relevant user
3. Fill in the start and end dates
4. Click **"Save"**

> ⚠️ **Restriction**: Non-administrator users can only add leave for themselves.

### Leave validation rules

The application automatically checks:
- ✅ The start date must be earlier than or equal to the end date
- ❌ It is not possible to add a leave period that overlaps **another existing leave period**
  for the same user

No other restriction is enforced by the application: leave periods in
the past are accepted, and a leave period can perfectly well overlap
an already scheduled shift or on-call period.

> 💡 **Important**: if a leave period overlaps existing shifts, the
> application **automatically rebalances the schedule** (the affected
> shifts are recalculated/reassigned) rather than blocking the creation
> of the leave period. A message indicates the number of shifts
> recalculated after the addition.

### Editing a leave period

Drag-and-drop on the calendar (edit mode) is only enabled for
administrators, including for a regular user's leave periods. There is
no dedicated editing form: to change the dates of a leave period,
delete it and create a new one via **Leave > Add a leave period**.

### Deleting a leave period

1. Go to **Leave**
2. Find the leave period to delete
3. Click the **🗑️ Delete** icon
4. Confirm the deletion

> ⚠️ **Restriction**: You can only delete your own leave periods, unless you are an administrator.

---

## 📤 ICS Export and Calendar Integration

### What is ICS export?

The **iCalendar (ICS)** format is a standard for exchanging calendar information. It allows you to import your Kairos schedules into:
- Google Calendar
- Microsoft Outlook
- Apple Calendar
- Mozilla Thunderbird
- And many others...

### Exporting your personal schedule

#### Step 1: Generate an ICS token

1. Log in to Kairos
2. Go to **Profile** > **ICS Token**
3. Click **"Generate a token"**
4. Copy the generated token

#### Step 2: Get the export URL

Your personal export URL is:
```
http://your-server:5000/export/shifts?scope=my&token=YOUR_TOKEN
```

Replace:
- `your-server`: The address of your Kairos instance
- `YOUR_TOKEN`: The token you generated

### Exporting other data

Kairos also allows you to export:

#### Exporting on-call periods
```
http://your-server:5000/export/oncall?scope=my&token=YOUR_TOKEN
```

#### Exporting leave
```
http://your-server:5000/export/leaves?scope=my&token=YOUR_TOKEN
```

#### Exporting everything (any user, not admin-restricted)
```
# All shifts
http://your-server:5000/export/shifts?scope=all&token=YOUR_TOKEN

# All on-call periods
http://your-server:5000/export/oncall?scope=all&token=YOUR_TOKEN

# All leave
http://your-server:5000/export/leaves?scope=all&token=YOUR_TOKEN
```

#### Step 3: Import into your calendar

##### Google Calendar

1. Open Google Calendar
2. Click the **⚙️ Settings** icon (top right)
3. Select **"Settings"**
4. Go to **"Calendars"** > **"Add calendar"** > **"From URL"**
5. Paste your Kairos export URL
6. Click **"Add calendar"**

> 💡 **Tip**: Updates to your Kairos schedule will be automatically synced with Google Calendar (every 12 hours by default).

##### Microsoft Outlook

1. Open Outlook
2. Go to **File** > **Account Settings** > **Account Settings**
3. Click **"New"** > **"Internet Calendar"**
4. Paste your Kairos export URL
5. Click **"Next"** and follow the instructions

##### Apple Calendar (macOS)

1. Open the Calendar app
2. Go to **File** > **New Calendar Subscription**
3. Paste your Kairos export URL
4. Click **"Subscribe"**

### Exporting all schedules

Any user, not just administrators, can export the schedules of all
users - `scope=all` is not restricted by role in the current version:

```
http://your-server:5000/export/shifts?scope=all&token=YOUR_TOKEN
```

> ⚠️ **Warning**: This URL grants access to ALL schedules, and any valid
> ICS token (not only an administrator's) can be used to request it.
> Keep it secret!

### Automatic updates

ICS files are generated dynamically on every request. This means that:
- ✅ Changes are immediately visible
- ✅ No need to manually regenerate the file
- ✅ Your external calendar always stays up to date

### Common issues

| Issue | Solution |
|----------|----------|
| The calendar doesn't update | Wait 12-24h or force synchronization in your calendar application |
| The URL doesn't work | Check that your token is correct and that you are logged in |
| Authentication error | Regenerate your ICS token |
| No events appear | Check that you have shifts, on-call periods, or leave scheduled |

---

## ⚡ Advanced Automation

> ⚠️ **Administrators only**

### Introduction to automation

Kairos offers a powerful automation system to automatically generate:
- **On-call periods**: According to a customizable rotation order
- **Shifts**: According to configurable business rules

### Automation dashboard

1. Go to **Admin** > **Automation**
2. You will see:
   - The current automation status
   - The number of shifts and on-call periods generated
   - Eligible users
   - The current rules

### Automatic on-call generation

#### Configuring the rotation order

1. Go to **Admin** > **Automation** > **Full generation**
2. You will see the list of users eligible for on-call
3. For each user:
   - **Include in rotation**: Check to include the user
   - **Order**: Drag and drop the user up/down in the list to set their
     rotation position
4. Click **"Save order"** to save

#### Automatically generating on-call periods and shifts

There is no separate "Shifts" automation page - shift generation is not
independently configurable (no per-day/per-shift-type headcount
setting). A single **Full generation** screen generates both the
on-call rotation and the shifts that follow from it in one operation:

1. Go to **Admin** > **Automation** > **Full generation**
2. Configure the on-call rotation order (see above)
3. Select the period:
   - **Start date**: First Friday of the period
   - **End date**: Last day of the period
4. Click **"Preview (Dry Run)"** to see a preview without saving anything
5. Check that the result suits you
6. Click **"Generate"** to create the on-call periods and the shifts

> 💡 **Tip**: Always use **"Preview (Dry Run)"** mode before generating to verify the configuration is correct.

### Refreshing existing shifts

If you have manually modified on-call periods and want to recalculate shifts:

1. Go to **Admin** > **Automation** > **Refresh shifts**
2. Select the period to recalculate
3. Click **"Refresh"**
4. The application will delete existing shifts for the period and recreate them

> ⚠️ **Warning**: This action will delete all existing shifts for the selected period!

### Default business rules

Kairos uses the following rules by default:

#### For on-call periods:
- Rotation in the order of the list of eligible users
- Each on-call period lasts 7 days (from Friday 9:00 PM to the following Friday 7:00 AM)
- Minimum 2-week gap required between two on-calls for the same user
  (stronger than "not two weeks in a row": after finishing an on-call, a
  user is skipped for the next rotation too and can only return on the
  third one)

#### For shifts (fixed rules, not configurable through the UI):
- The 1pm-9pm slot is reserved for that week's on-call person, if they
  belong to a schedule group
- Slot rotation: whoever was on the 1pm-9pm slot one week must be on the
  7am-3pm slot the following week
- Everyone else defaults to the 9am-5pm slot (several people can share it)
- If only 2 people are available on a given day, the one who is *not*
  on-call is put on the 7am-3pm slot
- Monday to Friday only
- Respects leave and on-call periods (no shift is generated for a user on
  leave that day)

---

## 📊 Administrator Dashboard

> ⚠️ **Administrators only**

### Accessing the dashboard

1. Log in with an administrator account
2. Click **Admin** in the navigation menu

### Overview

The dashboard displays:
- **Number of users**: Total registered users
- **Number of groups**: Total groups created
- **Number of shifts**: Total shifts scheduled
- **Number of on-call periods**: Total on-call periods scheduled
- **Number of leave periods**: Total leave periods recorded
- **Pending swap requests**: Number of shift swap requests awaiting admin
  review

### Advanced statistics

> 📌 **Coming soon**: Detailed charts and statistics will be added in future versions.

### Quick management

From the dashboard, you can quickly access:
- **Users**: Manage user accounts
- **Groups**: Manage user groups
- **Schedule**: View/manage shifts
- **Shift Types**: Configure shift types
- **On-Call**: View/manage on-call periods
- **Leave**: View/manage leave periods
- **Swaps**: Review pending shift swap requests
- **Automation**: Configure and run automation
- **Backups**: Trigger/download database backups
- **Audit log**: Consult the who-did-what-when trail
- **Notification targets**: Manage external (Slack/Discord/webhook...) notification destinations
- **Service accounts**: Manage API keys for the public JSON API
- **Settings**: Org-wide runtime settings (timezone, language, pagination, retention, etc.)

---

## ❓ FAQ and Troubleshooting

Moved to a dedicated document: [`FAQ.md`](FAQ.md) (frequently asked
questions, common error messages, technical issues).

---

## 📞 Support and Contact

### Getting help

1. **Check this guide**: Most questions are answered here
2. **Check the FAQ**: Section dedicated to frequently asked questions
3. **Contact your administrator**: For issues specific to your instance

### Reporting a bug

To report a bug:

1. **Check that it hasn't already been reported**: See the [GitHub Issues](https://github.com/FoxOps/leviia-schedule/issues)
2. **Prepare the following information**:
   - Application version
   - Steps to reproduce the bug
   - Expected behavior
   - Actual behavior
   - Screenshots (if applicable)
   - Error logs (if applicable)
3. **Open an Issue**: [Create a new Issue](https://github.com/FoxOps/leviia-schedule/issues/new)

### Requesting a feature

To request a new feature:

1. **Check that it isn't already planned**: See the [Roadmap](../../ROADMAP.md)
2. **Open a Discussion**: [Create a new Discussion](https://github.com/FoxOps/leviia-schedule/discussions/new)
3. **Describe your need**: Explain in detail the desired feature and its usefulness

### Contributing to the project

Contributions are welcome! See the "Contribution" section of the
[README](../../README.md#contributing) for the process to follow (fork,
branch, commit, Pull Request).

---

## 📚 Additional Resources

- [README.md](../../README.md) - Technical documentation and installation
- [ROADMAP.md](../../ROADMAP.md) - Development roadmap
- [LICENSE](../../LICENSE) - CeCILL v2.1 License
- [GitHub Repository](https://github.com/FoxOps/leviia-schedule) - Source code and issues

---

## 📝 Version History

| Version | Date | Author | Changes |
|---------|------|--------|-------------|
| 1.0.0 | June 2026 | Vibe Code | Initial creation of the user guide |

---

> **⚠️ Reminder: Development version**
> This software is provided "as is", without warranty of any kind.
> **Use it at your own risk.**

---

*Document generated for Kairos - All rights reserved under the CeCILL v2.1 license*
