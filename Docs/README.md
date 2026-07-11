# Documentation Leviia Schedule

> Réorganisée en Phase 5 (2026-07) : `docs/` → `Docs/`, éclaté en
> sous-dossiers par type. `SUMMARY.md` supprimé (redondant avec ce
> fichier + `architecture/ARCHITECTURE.md` + `api/API.md`, aucun contenu
> unique — voir `report/Phase 5: DOCUMENTATION.md`).

## Par où commencer selon votre rôle

| Rôle | Commencez ici |
|---|---|
| 👥 Utilisateur | [`guides/QUICK_START.md`](guides/QUICK_START.md) puis [`guides/USER_GUIDE.md`](guides/USER_GUIDE.md) |
| 🛡️ Administrateur | [`guides/ADMIN_GUIDE.md`](guides/ADMIN_GUIDE.md) |
| 💻 Développeur | [`architecture/ARCHITECTURE.md`](architecture/ARCHITECTURE.md) puis [`api/API.md`](api/API.md) |
| ❓ Une question précise | [`guides/FAQ.md`](guides/FAQ.md) |

## guides/ — Documentation utilisateur

| Document | Contenu |
|---|---|
| [`QUICK_START.md`](guides/QUICK_START.md) | Installation et prise en main en 5 minutes |
| [`USER_GUIDE.md`](guides/USER_GUIDE.md) | Guide complet : installation détaillée, authentification, shifts, astreintes, congés, export ICS |
| [`ADMIN_GUIDE.md`](guides/ADMIN_GUIDE.md) | Sécurité, gestion des utilisateurs/groupes, SSO/OIDC, automatisation, configuration technique, maintenance |
| [`FAQ.md`](guides/FAQ.md) | Questions fréquentes, messages d'erreur courants |

## architecture/ — Documentation technique

| Document | Contenu |
|---|---|
| [`ARCHITECTURE.md`](architecture/ARCHITECTURE.md) | Vue d'ensemble, structure des dossiers, couches routes/services/repositories, sécurité |
| [`ERD.md`](architecture/ERD.md) | Schéma entité-relation (Mermaid) |
| [`SEQUENCE_DIAGRAMS.md`](architecture/SEQUENCE_DIAGRAMS.md) | Diagrammes de séquence (Mermaid) : connexion basique/OIDC, ajout de congé avec rééquilibrage, API drag & drop, export ICS |

## api/ — Documentation API

| Document | Contenu |
|---|---|
| [`API.md`](api/API.md) | Endpoints JSON réels, authentification (session/CSRF/token ICS), formats de réponse |
| [`openapi.yaml`](api/openapi.yaml) | Spec OpenAPI 3.0 machine-lisible (Swagger UI, Postman, etc.) |

## deployment/ — Déploiement et exploitation

| Document | Contenu |
|---|---|
| [`DEPLOYMENT_GUIDE.md`](deployment/DEPLOYMENT_GUIDE.md) | Prérequis, Gunicorn/uWSGI, base de données, sécurité en production |
| [`DEPLOYMENT_ADVANCED.md`](deployment/DEPLOYMENT_ADVANCED.md) | Docker, PostgreSQL, Redis, Nginx |
| [`docker.md`](deployment/docker.md) | Démarrage rapide avec Docker |
| [`BACKUP_GUIDE.md`](deployment/BACKUP_GUIDE.md) | Sauvegarde et restauration de la base de données |

## reference/ — Référence technique

| Document | Contenu |
|---|---|
| [`ENVIRONMENT_VARIABLES.md`](reference/ENVIRONMENT_VARIABLES.md) | Toutes les variables d'environnement effectivement lues par l'application |
| [`ERROR_HANDLING.md`](reference/ERROR_HANDLING.md) | Pages d'erreur, gestionnaires HTTP, système de logging |
| [`PERFORMANCE_OPTIMIZATION.md`](reference/PERFORMANCE_OPTIMIZATION.md) | Cache, `eager_load`, index de base de données |
| [`vendor-assets.md`](reference/vendor-assets.md) | Bulma/Font Awesome/FullCalendar servis localement |

## Contribuer à la documentation

1. Signaler une erreur : [Issue GitHub](https://github.com/FoxOps/leviia-schedule/issues)
2. Proposer une amélioration : [Discussion GitHub](https://github.com/FoxOps/leviia-schedule/discussions)
3. Soumettre une modification : fork, branche, modification, Pull Request

Règle principale : **vérifiez contre le code réel avant d'écrire**, pas
contre la documentation existante — la plupart des inexactitudes
corrigées en Phase 5 venaient de documentation copiée/étendue sans
revérifier après un refactor. Voir `report/Phase 5: DOCUMENTATION.md`
pour le détail de ce qui a été trouvé et corrigé.

## Support

- Questions : [`guides/FAQ.md`](guides/FAQ.md), puis votre administrateur
- Bugs : [Issues GitHub](https://github.com/FoxOps/leviia-schedule/issues)
- Nouvelles fonctionnalités : [`../ROADMAP.md`](../ROADMAP.md), puis [Discussions GitHub](https://github.com/FoxOps/leviia-schedule/discussions)

---

*© 2026 Leviia Schedule — Licence [CeCILL v2.1](../LICENSE)*
