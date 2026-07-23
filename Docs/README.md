# Kairos Documentation

## Where to start based on your role

| Role | Start here |
|---|---|
| 👥 User | [`guides/QUICK_START.md`](guides/QUICK_START.md) then [`guides/USER_GUIDE.md`](guides/USER_GUIDE.md) |
| 🛡️ Administrator | [`guides/ADMIN_GUIDE.md`](guides/ADMIN_GUIDE.md) |
| 💻 Developer | [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md) then [`api/API.md`](api/API.md) |
| ❓ A specific question | [`guides/FAQ.md`](guides/FAQ.md) |

## guides/ — User documentation

| Document | Content |
|---|---|
| [`QUICK_START.md`](guides/QUICK_START.md) | Installation and 5-minute hands-on start |
| [`USER_GUIDE.md`](guides/USER_GUIDE.md) | Full guide: detailed installation, authentication, shifts, on-call, leave, ICS export |
| [`ADMIN_GUIDE.md`](guides/ADMIN_GUIDE.md) | Security, user/group management, SSO/OIDC, automation, technical configuration, maintenance |
| [`FAQ.md`](guides/FAQ.md) | Frequently asked questions, common error messages |

## architecture/ — Technical documentation

| Document | Content |
|---|---|
| [`ARCHITECTURE.md`](architecture/ARCHITECTURE.md) | Overview, folder structure, routes/services/repositories layers, security |
| [`ERD.md`](architecture/ERD.md) | Entity-relationship diagram (Mermaid) |
| [`SEQUENCE_DIAGRAMS.md`](architecture/SEQUENCE_DIAGRAMS.md) | Sequence diagrams (Mermaid): basic/OIDC login, adding leave with rebalancing, drag & drop API, ICS export |

## api/ — API documentation

| Document | Content |
|---|---|
| [`API.md`](api/API.md) | Real JSON endpoints, authentication (session/CSRF/ICS token), response formats |
| [`openapi.yaml`](api/openapi.yaml) | Machine-readable OpenAPI 3.0 spec (Swagger UI, Postman, etc.) |

## deployment/ — Deployment and operations

| Document | Content |
|---|---|
| [`docker.md`](deployment/docker.md) | **Recommended method**: running the image published on the registry (Docker) |
| [`DEPLOYMENT_ADVANCED.md`](deployment/DEPLOYMENT_ADVANCED.md) | Advanced Docker: PostgreSQL, MySQL/MariaDB, Nginx |
| [`DEPLOYMENT_GUIDE.md`](deployment/DEPLOYMENT_GUIDE.md) | Non-Docker alternative: bare-metal Gunicorn/uWSGI, database, production security |
| [`BACKUP_GUIDE.md`](deployment/BACKUP_GUIDE.md) | Database backup and restore |

## reference/ — Technical reference

| Document | Content |
|---|---|
| [`ENVIRONMENT_VARIABLES.md`](reference/ENVIRONMENT_VARIABLES.md) | Every environment variable actually read by the application |
| [`ERROR_HANDLING.md`](reference/ERROR_HANDLING.md) | Error pages, HTTP handlers, logging system |
| [`PERFORMANCE_OPTIMIZATION.md`](reference/PERFORMANCE_OPTIMIZATION.md) | Cache, `eager_load`, database indexes |
| [`VERSIONING.md`](reference/VERSIONING.md) | SemVer policy, `make bump-version`/`check-version`, Docker image tagging |

## Contributing to the documentation

1. Report an error: [GitHub Issue](https://github.com/FoxOps/kairos/issues)
2. Suggest an improvement: [GitHub Discussion](https://github.com/FoxOps/kairos/discussions)
3. Submit a change: fork, branch, edit, Pull Request

Main rule: **verify against the real code before writing**, not
against the existing documentation - copying or extending existing
text without re-checking it against the current code is the most
common source of inaccuracies.

## Support

- Questions: [`guides/FAQ.md`](guides/FAQ.md), then your administrator
- Bugs: [GitHub Issues](https://github.com/FoxOps/kairos/issues)
- New features: [`../ROADMAP.md`](../ROADMAP.md), then [GitHub Discussions](https://github.com/FoxOps/kairos/discussions)

---

*© 2026 FoxOps — Licensed under [CeCILL v2.1](../LICENSE)*
