# Kairos

> **✅ Version 1.0.0-rc1** — production stabilization complete: 1314 tests,
> full security audit, targeted bug hunt, load test. See `ROADMAP.md`
> ("v1.0 stability verdict") for the full detail — two operational points
> (not code defects) remain to be decided by the team deploying the app
> before a real production rollout: the GitLab CI configured in this repo
> doesn't actually run on GitHub (no equivalent GitHub Actions workflow),
> and the Safety dependency scan requires an API key not configured by
> default.

---

## 📚 Documentation

**Full documentation is available in [Docs/](Docs/)**

### 🎯 **Where to start?**

| Role | Recommended Document | Description |
|------|---------------------|-------------|
| **👥 User** | [Docs/guides/QUICK_START.md](Docs/guides/QUICK_START.md) | Quick start guide (5 min) |
| **🛡️ Administrator** | [Docs/guides/ADMIN_GUIDE.md](Docs/guides/ADMIN_GUIDE.md) | Configuration, security, maintenance |
| **💻 Developer** | [Docs/architecture/ARCHITECTURE.md](Docs/architecture/ARCHITECTURE.md) | Technical architecture, diagrams |
| **📖 Everyone** | [Docs/README.md](Docs/README.md) | **Full index** of all documentation |

> **💡 For a quick hands-on start, see the [Quick Start Guide](Docs/guides/QUICK_START.md)**

---

## 📋 Description

**Kairos** is a web application for team shift scheduling, on-call
rotations, and leave management. It lets you manage work schedules,
on-call rotations, and team members' leave.

### Main features

- ✅ **User and group management** (with permissions)
- ✅ **Shift type management** (customizable hours)
- ✅ **Shift scheduling** with day/week/month views
- ✅ **On-call management** with automatic rotations
- ✅ **Leave management** with schedule visualization
- ✅ **Email notifications**: weekly reminders for upcoming shifts and
  on-call duty (configurable SMTP, standalone cron scripts)
- ✅ **Shift swaps between users**: request (simple give-away or
  reciprocal), approve/reject/cancel by an admin, in-app notifications
  (bell icon)
- ✅ **Multi-language** (French/English) and **multi-timezone** support,
  customizable per user or organization-wide by default
  (`/admin/settings`)
- ✅ **Configurable date/time formats** (per user or by default)
- ✅ **Change history (audit trail)**: who did what, when, browsable at
  `/admin/audit-log`
- ✅ **ICS export** for integration with Google Calendar, Outlook, etc.
- ✅ **Secure authentication** (Flask-Login)
- ✅ **SSO/OIDC authentication** (Keycloak, Okta, Auth0, etc.)
- ✅ **Full logging system** with automatic rotation
- ✅ **Smart automation** with business rules

---

## 🛠 Technologies

| Component | Technology | Version |
|-----------|-------------|---------|
| **Web framework** | Flask | 3.1.3 |
| **ORM** | SQLAlchemy | 2.0.51 |
| **Database** | SQLite (default), PostgreSQL | - |
| **Authentication** | Flask-Login, Authlib (OIDC) | 0.6.3, 1.7.2 |
| **ICS export** | icalendar | 7.2.0 |
| **Internationalization** | Flask-Babel | 4.0.0 |
| **Migrations** | Flask-Migrate (Alembic) | - |

---

## 📦 Requirements

- Python 3.8 or later
- pip (Python package manager)
- Git (optional, for cloning the repo)

---

## 🐳 Installation (recommended: Docker Compose)

No need to clone the repo - two files are enough:

```bash
mkdir kairos && cd kairos
curl -o docker-compose.yml https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker/docker-compose.example.yml
curl -o .env https://raw.githubusercontent.com/FoxOps/leviia-schedule/main/docker/.env.example

nano .env  # KAIROS_IMAGE=harbor.leviia.com/<HARBOR_PROJECT>/kairos:latest, SECRET_KEY, DEFAULT_ADMIN_PASSWORD

docker compose up -d
```

The application will be available at: **http://localhost:5000**

> **📖 Detailed documentation**: [Docs/deployment/docker.md](Docs/deployment/docker.md)

### Local installation (development / special cases)

Reserved for working on the code itself, or for cases where Docker
isn't available - the Docker image above remains the primary way to
run the application.

```bash
git clone https://github.com/FoxOps/leviia-schedule.git
cd leviia-schedule
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The application will be available at: **http://localhost:5000**

> **📖 Detailed documentation**: [Docs/guides/QUICK_START.md](Docs/guides/QUICK_START.md)

---

## 🎯 Usage

### First login

1. Log in with the default credentials:
   - Email: `admin@kairos.local`
   - Password: `admin123`

2. **⚠️ Change the password immediately** after first login, via the Profile menu.

> **📖 Full documentation**:
> - [User Guide](Docs/guides/USER_GUIDE.md) - For day-to-day use
> - [Admin Guide](Docs/guides/ADMIN_GUIDE.md) - For configuration and management

---

## 📁 Project structure

```
kairos/
├── app/                    # Application source code
│   ├── __init__.py         # Flask initialization (create_app factory)
│   ├── models/              # Database models (package)
│   ├── repositories/        # Data access
│   ├── services/             # Business logic
│   ├── routes/              # Flask routes / blueprints
│   └── utils/               # Utility functions (by sub-package)
├── app/config/              # Configuration (base + testing)
├── run.py                   # Entry point
├── requirements.txt         # Python dependencies
├── Docs/                    # 📚 Full documentation
│   ├── README.md            # Documentation index
│   ├── architecture/        # Architecture, ERD, sequence diagrams
│   ├── api/                 # API documentation + OpenAPI spec
│   ├── guides/               # User/admin/quick-start/FAQ guides
│   ├── deployment/           # Deployment, Docker, backups
│   └── reference/             # Env vars, errors, performance
└── tests/                    # Tests (unit/integration/e2e/fixtures)
```

> **📖 Technical documentation**: [Docs/architecture/ARCHITECTURE.md](Docs/architecture/ARCHITECTURE.md)

---

## 🧪 Tests and Code Quality

> **✅ Status**: **1314 tests**, all passing - Coverage: ~92%

### Running the tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v --tb=short

# Run with code coverage
pytest tests/ --cov=app --cov-report=term-missing
```

### Code quality checks

```bash
# Linting with Ruff
ruff check . --config=.ruff.toml

# Type checking with mypy
mypy app/ tests/ --ignore-missing-imports --allow-untyped-decorators

# Formatting with Black
black --check . --exclude=".git|__pycache__|instance|venv"
```

> **📖 Test documentation**: [report/Phase 4: AMÉLIORATION DES TESTS.md](report/Phase%204%3A%20AM%C3%89LIORATION%20DES%20TESTS.md)

---

## 📝 Contributing

Contributions are welcome!

1. **Fork** the repo
2. Create a branch for your feature (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a **Pull Request**

> **📖 Contribution guide**: [Docs/README.md - Contributing to the documentation](Docs/README.md#contributing-to-the-documentation)

---

## 🐛 Reporting a bug

To report a bug, open an **Issue** on GitHub with the following information:

- Application version
- Steps to reproduce the bug
- Expected behavior
- Actual behavior
- Screenshots (if applicable)
- Error logs (if applicable)
- Configuration used (SQLite/PostgreSQL, etc.)

---

## 📜 License

This project is licensed under **CeCILL v2.1**. See the [LICENSE](LICENSE) file for details.

---

## 📞 Contact

For any question or suggestion, feel free to open an **Issue** or a **Discussion** on the GitHub repo.

---

## 📌 Release notes

### Version 1.0.0-rc1

- **Status**: Production stabilization complete (see `ROADMAP.md` →
  "v1.0 stability verdict" for the full detail, including the
  operational points left to the deploying team's judgment)
- **Features**: All core features are implemented
- **Tests**: 1314 tests (all passing)
- **Coverage**: ~92%
- **Security**: Full audit performed (`report/SECURITY_AUDIT_v1.0.md`),
  0 Bandit findings on `app/`
- **Performance**: Load test performed (`report/LOAD_TEST_v1.0.md`)

> **📖 Roadmap**: [ROADMAP.md](ROADMAP.md)

---

> **⚠️ Warranty**
> This software is provided "as is", without warranty of any kind.
> The author cannot be held liable for any direct, indirect, incidental,
> special, or consequential damages arising from the use of this software.
> **Use it at your own risk.**
