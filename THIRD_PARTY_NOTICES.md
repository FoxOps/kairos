# Third-Party Notices

Kairos is built on top of the open-source ecosystem. This file lists every
library the running application actually depends on - backend (installed via
`pip`) and frontend (loaded from CDN, no bundler/`package.json` in this
project - see `CLAUDE.md`'s "Frontend" section) - plus the development/testing
tools used to build and verify it. License and license text always come from
the project's own published metadata (PyPI/npm), not guessed.

None of these licenses require attribution beyond what's listed here for a
web application (no bundled binaries, no static linking of GPL/LGPL code).
`psycopg` (LGPL-3.0) is used as-is via its published Python API, not modified
or statically linked, which keeps it clear of source-disclosure obligations.

## Backend (Python, `requirements.txt`)

| Library | License | Source |
|---|---|---|
| Flask | BSD-3-Clause | [pallets/flask](https://github.com/pallets/flask) |
| Flask-SQLAlchemy | BSD-3-Clause | [pallets-eco/flask-sqlalchemy](https://github.com/pallets-eco/flask-sqlalchemy) |
| Flask-Login | MIT | [maxcountryman/flask-login](https://github.com/maxcountryman/flask-login) |
| Flask-WTF | BSD-3-Clause | [pallets-eco/flask-wtf](https://github.com/pallets-eco/flask-wtf) |
| Werkzeug | BSD-3-Clause | [pallets/werkzeug](https://github.com/pallets/werkzeug) |
| Flask-Babel | BSD-3-Clause | [python-babel/flask-babel](https://github.com/python-babel/flask-babel) |
| SQLAlchemy | MIT | [sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) |
| Flask-Migrate | MIT | [miguelgrinberg/flask-migrate](https://github.com/miguelgrinberg/flask-migrate) |
| Alembic | MIT | [sqlalchemy/alembic](https://github.com/sqlalchemy/alembic) |
| icalendar | BSD-2-Clause | [collective/icalendar](https://github.com/collective/icalendar) |
| python-dateutil | BSD-3-Clause / Apache-2.0 (dual) | [dateutil/dateutil](https://github.com/dateutil/dateutil) |
| tzdata | Apache-2.0 | [python/tzdata](https://github.com/python/tzdata) |
| python-dotenv | BSD-3-Clause | [theskumar/python-dotenv](https://github.com/theskumar/python-dotenv) |
| Flask-Limiter | MIT | [alisaifee/flask-limiter](https://github.com/alisaifee/flask-limiter) |
| Flask-CORS | MIT | [corydolphin/flask-cors](https://github.com/corydolphin/flask-cors) |
| cryptography | Apache-2.0 OR BSD-3-Clause | [pyca/cryptography](https://github.com/pyca/cryptography) |
| Flask-Compress | MIT | [colour-science/flask-compress](https://github.com/colour-science/flask-compress) |
| psycopg (binary) | LGPL-3.0-only | [psycopg/psycopg](https://github.com/psycopg/psycopg) |
| PyMySQL | MIT | [PyMySQL/PyMySQL](https://github.com/PyMySQL/PyMySQL) |
| Authlib | BSD-3-Clause | [lepture/authlib](https://github.com/lepture/authlib) |
| requests | Apache-2.0 | [psf/requests](https://github.com/psf/requests) |
| flask-talisman | Apache-2.0 | [wntrblm/flask-talisman](https://github.com/wntrblm/flask-talisman) |
| prometheus-client | Apache-2.0 / BSD-2-Clause | [prometheus/client_python](https://github.com/prometheus/client_python) |
| psutil | BSD-3-Clause | [giampaolo/psutil](https://github.com/giampaolo/psutil) |
| Apprise | BSD-2-Clause | [caronc/apprise](https://github.com/caronc/apprise) |
| flask-smorest | MIT | [marshmallow-code/flask-smorest](https://github.com/marshmallow-code/flask-smorest) |
| marshmallow | MIT | [marshmallow-code/marshmallow](https://github.com/marshmallow-code/marshmallow) |
| polib | MIT | [izimobil/polib](https://github.com/izimobil/polib) |

## Frontend (CDN, no bundler - see `app/templates/base.html`)

| Library | License | Source |
|---|---|---|
| Tailwind CSS | MIT | [tailwindlabs/tailwindcss](https://github.com/tailwindlabs/tailwindcss) |
| daisyUI | MIT | [saadeghi/daisyui](https://github.com/saadeghi/daisyui) |
| Font Awesome (Free) | MIT (code) / OFL-1.1 (icons & fonts) | [FortAwesome/Font-Awesome](https://github.com/FortAwesome/Font-Awesome) |
| FullCalendar | MIT | [fullcalendar/fullcalendar](https://github.com/fullcalendar/fullcalendar) |
| Vanilla Calendar Pro | MIT | [uvarov-frontend/vanilla-calendar-pro](https://github.com/uvarov-frontend/vanilla-calendar-pro) |

## Design (color palette, not a code dependency)

`app/static/css/theme-colors.css` sources its dark/light palette 1:1 from the
official Dracula/Alucard spec (see `CLAUDE.md`'s "Frontend" section) - no
invented or computed hues.

| Asset | License | Source |
|---|---|---|
| Dracula Theme (color spec) | MIT | [dracula/dracula-theme](https://github.com/dracula/dracula-theme) |

## Development & testing tools (not shipped in the running app)

| Tool | License | Source |
|---|---|---|
| pytest | MIT | [pytest-dev/pytest](https://github.com/pytest-dev/pytest) |
| pytest-flask | MIT | [pytest-dev/pytest-flask](https://github.com/pytest-dev/pytest-flask) |
| pytest-cov | MIT | [pytest-dev/pytest-cov](https://github.com/pytest-dev/pytest-cov) |
| Ruff | MIT | [astral-sh/ruff](https://github.com/astral-sh/ruff) |
| mypy | MIT | [python/mypy](https://github.com/python/mypy) |
| Black | MIT | [psf/black](https://github.com/psf/black) |
| Bandit | Apache-2.0 | [PyCQA/bandit](https://github.com/PyCQA/bandit) |
| pip-audit | Apache-2.0 | [pypa/pip-audit](https://github.com/pypa/pip-audit) |
| Playwright (Python) | Apache-2.0 | [microsoft/playwright-python](https://github.com/microsoft/playwright-python) |
| pytest-playwright | Apache-2.0 | [microsoft/playwright-pytest](https://github.com/microsoft/playwright-pytest) |
| djLint | GPL-3.0-or-later | [djlint/djLint](https://github.com/djlint/djLint) |

---

*This file is maintained by hand alongside `requirements.txt` and the CDN
`<script>`/`<link>` tags in `app/templates/base.html` - if you add, remove, or
bump a dependency, update the corresponding row here too.*
