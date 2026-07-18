# 🚀 Quick Start Guide - Kairos

> **Version**: 1.0.0 | **Last updated**: June 2026

---

## 🎯 In 5 Minutes

### 1️⃣ Installation (recommended method: Docker Compose)

No need to clone the repository - two files are enough:

```bash
mkdir kairos && cd kairos
curl -o docker-compose.yml https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker/docker-compose.example.yml
curl -o .env https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker/.env.example

nano .env  # KAIROS_IMAGE=harbor.leviia.com/<HARBOR_PROJECT>/kairos:latest, SECRET_KEY, DEFAULT_ADMIN_PASSWORD

docker compose up -d
```

**Access**: http://localhost:5000

> ⚠️ **The `nano .env` step** (at least `SECRET_KEY`/`DEFAULT_ADMIN_PASSWORD`)
> is required: without `DEFAULT_ADMIN_PASSWORD`, the application generates
> a random admin password on first startup (never displayed
> anywhere) instead of the default `admin123` below.

> **📖 Full details** (registry, volumes, variables):
> [`deployment/docker.md`](../deployment/docker.md)

### Alternative: local installation (development / special cases)

Reserved for developing on the code or for cases where Docker is not
available - the Docker image above remains the primary method.

```bash
git clone https://github.com/FoxOps/leviia-schedule.git
cd leviia-schedule
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Copy the default configuration
cp .env.example .env

# Start
python run.py
```

**Access**: http://localhost:5000

> ⚠️ **The `cp .env.example .env` step is required**: without it,
> `DEFAULT_ADMIN_PASSWORD` is not set and the application generates a
> random admin password on first startup (never displayed anywhere)
> instead of the default `admin123` below.

---

### 2️⃣ First Login

- **Email**: `admin@kairos.local`
- **Password**: `admin123`

> ⚠️ **Change the password immediately!**

---

### 2️⃣ SSO/OIDC Authentication (Optional)

If you use **Keycloak**, **Okta**, **Auth0** or another OIDC provider:

1. Configure your OIDC provider with the callback URL: `http://localhost:5000/oidc/callback`
2. Add the environment variables to your `.env` file:
   ```bash
   OIDC_ENABLED=true
   OIDC_ISSUER=https://votre-fournisseur.com/realms/votre-realm
   OIDC_CLIENT_ID=votre-client-id
   OIDC_CLIENT_SECRET=votre-client-secret
   OIDC_REDIRECT_URI=http://localhost:5000/oidc/callback
   ```
3. Restart the application: `python run.py`
4. Log in via the **Log in with SSO** button

> ⚠️ **Info**: See the [Administrator Guide](ADMIN_GUIDE.md) for complete SSO/OIDC configuration.

---

### 3️⃣ Basic Configuration

#### Create a group
1. **Admin** > **Groups** > **Add**
2. Name: `Technical Team`
3. ✅ Participates in scheduling
4. ✅ Participates in on-call rotations

#### Add a user
1. **Admin** > **Users** > **Add**
2. Name: `Jean Dupont`
3. Email: `jean@company.com`
4. Group: `Technical Team`
5. Password: `mypassword123`

---

## 📅 Daily Usage

### For Administrators

#### 🔹 Add a shift
1. **Schedule** > **Add a shift**
2. Select: User + Shift type + Date
3. **Save**

#### 🔹 Schedule an on-call rotation
1. **On-call** > **Add an on-call**
2. Select: User + **Friday** as the start date
3. **Save**

#### 🔹 Configure automation
1. **Admin** > **Automation** > **Full generation**
2. Configure the rotation order
3. Select the period
4. **Simulate** → **Generate**

---

### For Users

#### 🔹 View your schedule
- **Home**: Interactive calendar
- **Schedule**: List of all your shifts

#### 🔹 Request leave
1. **Leave** > **Add leave**
2. Select: Start date + End date
3. **Save**

#### 🔹 Export to Google Calendar
1. **Profile** > **ICS Token**
2. **Generate a new token**
3. Copy the URL: `http://localhost:5000/export/shifts?scope=my&token=YOUR_TOKEN`
4. In Google Calendar: **Settings** > **Add calendar** > **From URL**

---

## ⚡ Quick Tips

### Shortcuts

| Action | Path |
|--------|--------|
| Dashboard | `/` or `/index` |
| Schedule | `/schedule` |
| On-call | `/oncall` |
| Leave | `/leave` |
| Admin | `/admin` |
| Profile | `/profile` |

### Useful Commands

```bash
# Run the tests
make test

# Check code quality
make lint

# Format the code
make format-fix

# All at once
make all
```

---

## 🆘 Quick Troubleshooting

| Problem | Solution |
|----------|----------|
| **404 Error** | Check the URL and your permissions |
| **Login failed** | Check your email/password |
| **Shifts not visible** | Check the period in the calendar |
| **ICS export not working** | Regenerate your token |
| **Missing database** | `mkdir -p instance` then restart |

---

## 📚 Full Documentation

- [📖 Complete User Guide](USER_GUIDE.md)
- [🛡️ Administrator Guide](ADMIN_GUIDE.md)
- [❓ FAQ](FAQ.md)
- [🗺️ Roadmap](../../ROADMAP.md)
- [📋 Technical README](../../README.md)

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/FoxOps/leviia-schedule/issues)
- **Discussions**: [GitHub Discussions](https://github.com/FoxOps/leviia-schedule/discussions)
- **License**: CeCILL v2.1

---

*© 2026 FoxOps - All rights reserved*
