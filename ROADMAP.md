# 🗺️ Feuille de Route - Leviia Schedule

> **Version** : 5.7.0 - Refonte visuelle Dracula/Alucard (PR #110)
> **Version app** : 0.7.6 (`/version`) - Identité visuelle complète sur la
> base Tailwind/daisyUI (PR #108) : palette officielle Dracula (thème
> sombre) / Alucard (thème clair), drawer mobile natif, composants daisyUI
> (stats, breadcrumbs, avatar, tooltip, collapse, hero, swap), modale de
> création de shift en `<dialog>` natif
> **Dernière mise à jour** : Juillet 2026
> **Statut** : Développement actif - **933 tests passent** ✅ (dont 23 E2E navigateur réel)
> **Commit actuel** : branche feature/dracula-redesign (PR #110)
>
> ℹ️ Ne pas confondre avec les « Phases » de refonte (`report/Phase 1` à
> `report/Phase 6`, un chantier qualité/infra achevé) et les « Phases » de
> cette feuille de route ci-dessous (roadmap fonctionnelle v0.1 → v3.0,
> numérotation indépendante).

---

## 📌 Vue d'ensemble

Cette feuille de route présente les étapes clés, l'état actuel et les priorités de développement pour **Leviia Schedule**, une application web complète de gestion des plannings, des astreintes et des congés.

## 🎯 Objectifs principaux

- ✅ **Fonctionnalités de base** : Implémentation complète de toutes les fonctionnalités principales
- ✅ **Tests complets** : **773 tests**, 0 échec, couverture ~82%
- ✅ **Automatisation avancée** : Règles métiers complexes implémentées
- ✅ **Documentation complète** : Documentation technique, API et utilisateur
- ✅ **Stabilisation** : Refonte Phases 1-6 terminée (architecture, sécurité, DevOps)
- 📈 **Améliorations** : Fonctionnalités avancées et intégrations (Phase 5/7 roadmap, à venir)
- 🚀 **Production Ready** : Support multi-DB et tests de charge restants avant v1.0

---

## 📊 État actuel du projet

### ✅ **Fonctionnalités implémentées et testées**

| Catégorie | Élément | Statut | Détails |
|----------|---------|--------|---------|
| **Cœur** | Gestion des utilisateurs | ✅ | CRUD complet + authentification + rôles |
| **Cœur** | Gestion des groupes | ✅ | Avec permissions schedule/oncall |
| **Cœur** | Gestion des types de shifts | ✅ | Configuration des horaires personnalisables |
| **Cœur** | Gestion des shifts | ✅ | Attribution et visualisation jour/semaine/mois |
| **Cœur** | Gestion des astreintes (On-Call) | ✅ | Rotations automatiques (Vendredi 21h, 7 jours) |
| **Cœur** | Gestion des congés | ✅ | Avec gestion des conflits et visualisation |
| **Export** | Export ICS (shifts) | ✅ | Format iCalendar pour intégration externe |
| **Export** | Export ICS (astreintes) | ✅ | Format iCalendar |
| **Export** | Export ICS (congés) | ✅ | Format iCalendar |
| **Export** | Authentification par token | ✅ | Accès sans session pour l'export |
| **Sécurité** | Authentification Flask-Login | ✅ | Avec "remember me" et gestion de session |
| **Sécurité** | Authentification OIDC/SSO | ✅ | Authlib, Keycloak/Okta/Auth0-compatible |
| **Sécurité** | Gestion des permissions | ✅ | Décorateurs (admin_required, role_required, etc.) |
| **Sécurité** | Gestion des erreurs | ✅ | Pages personnalisées 400-504 |
| **Sécurité** | Logging complet | ✅ | Rotation, syslog, filtrage des données sensibles |
| **Sécurité** | CSP + security headers | ✅ | Talisman toujours actif (Phase 6), CSP stricte |
| **Sécurité** | Audit de sécurité | ✅ | Rapport complet (report/SECURITY_AUDIT_REPORT.md) |
| **Automatisation** | Règles métiers shifts | ✅ | **5 règles complexes** implémentées |
| **Automatisation** | Rotation astreintes | ✅ | Algorithme automatique avec contraintes |
| **Automatisation** | Gestion des conflits | ✅ | Congés vs shifts vs astreintes |
| **Automatisation** | Module advanced_shift_automation | ✅ | Logique avancée de rotation |
| **Architecture** | Couche Repositories | ✅ | Accès aux données isolé (app/repositories/) |
| **Architecture** | Couche Services | ✅ | Logique métier isolée (app/services/) |
| **Performance** | Optimisation des requêtes SQL | ✅ | Index composites, joinedload (eager_load) |
| **Performance** | Cache | ✅ | Système de cache implémenté |
| **Performance** | Pagination | ✅ | Pagination complète |
| **Performance** | Compression Gzip/Brotli/Zstd | ✅ | flask-compress, activé Phase 6 |
| **Tests** | Tests unitaires + intégration | ✅ | **773 tests passent**, couverture ~82% |
| **Tests** | Tests d'intégration | ✅ | Scénarios utilisateurs complets (e2e/) |
| **Tests** | Tests des gestionnaires d'erreurs | ✅ | Toutes les erreurs HTTP (400-504) |
| **Tests** | Tests d'export | ✅ | ICS, routes d'export |
| **Tests** | Tests d'automatisation | ✅ | Règles métiers et rotations |
| **Tests** | Tests des décorateurs | ✅ | Permissions et accès |
| **Tests** | Tests du thème sombre | ✅ | Tests dédiés |
| **Tests** | Tests de sécurité | ✅ | CSP, CSRF, Talisman, contrôle d'accès |
| **Tests** | Tests de performance | ✅ | Temps de réponse, N+1, compression |
| **Qualité** | Linting (Ruff) | ✅ | Configuration .ruff.toml |
| **Qualité** | Vérification types (mypy) | ✅ | Configuration complète |
| **Qualité** | Formatage (Black) | ✅ | Configuration complète |
| **Qualité** | Analyse sécurité (Bandit) | ✅ | Configuration complète |
| **Qualité** | Scan vulnérabilités (Safety) | ✅ | Configuration complète |
| **Infrastructure** | Configuration flexible | ✅ | app/config/ (base/dev/prod/testing) |
| **Infrastructure** | Support SQLite | ✅ | Par défaut, fonctionnel |
| **Infrastructure** | Support PostgreSQL | ⚠️ | Configuration possible (psycopg), non testé en CI |
| **Infrastructure** | Makefile | ✅ | test, lint, format, security, all, backup-* |
| **Infrastructure** | Scripts de backup | ✅ | backup_database.py, backup_config.py |
| **Infrastructure** | Dockerisation | ✅ | Build multi-stage optimisé (Phase 6, 415 Mo) |
| **Infrastructure** | CI/CD Pipeline | ✅ | GitLab CI (.gitlab-ci/.gitlab-ci.yml), futur dépôt |
| **Infrastructure** | Kubernetes ready | ✅ | Manifests complets (k8s/), probes /health /ready |
| **Infrastructure** | Monitoring (Prometheus/Grafana) | ✅ | /metrics + dashboard importable (grafana/) |
| **Documentation** | README.md | ✅ | Complète et à jour |
| **Documentation** | ROADMAP.md | ✅ | Feuille de route détaillée |
| **Documentation** | Docs/architecture/ARCHITECTURE.md | ✅ | Architecture technique + diagrammes Mermaid |
| **Documentation** | Docs/api/API.md + openapi.yaml | ✅ | Documentation API + spec OpenAPI |
| **Documentation** | Docs/guides/ADMIN_GUIDE.md | ✅ | Guide administrateur |
| **Documentation** | Docs/guides/USER_GUIDE.md | ✅ | Guide utilisateur |
| **Documentation** | Docs/guides/QUICK_START.md | ✅ | Guide de démarrage rapide |
| **Documentation** | Docs/guides/FAQ.md | ✅ | Foire aux questions |
| **Documentation** | Docs/reference/ERROR_HANDLING.md | ✅ | Gestion des erreurs |
| **Documentation** | Docs/reference/PERFORMANCE_OPTIMIZATION.md | ✅ | Optimisations |
| **Documentation** | Docs/deployment/BACKUP_GUIDE.md | ✅ | Guide de sauvegarde |
| **Documentation** | Docs/reference/ENVIRONMENT_VARIABLES.md | ✅ | Variables d'environnement |
| **UI/UX** | Thème sombre | ✅ | CSS complet + accessibilité |
| **UI/UX** | Templates Jinja2 | ✅ | 30+ templates |
| **UI/UX** | Skip link | ✅ | Accessibilité WCAG |
| **UI/UX** | Calendrier interactif | ✅ | FullCalendar, drag & drop (module ES6 externalisé) |

---

## 📅 Phases de développement

### Phase 1 : ✅ Fondations (Terminé - v0.1-v0.3)

**Objectif** : Mise en place de l'architecture de base et des fonctionnalités principales

| Élément | Statut | Priorité | Livraison | Détails |
|---------|--------|----------|-----------|---------|
| Architecture Flask + SQLAlchemy | ✅ | Haute | v0.1 | Structure du projet et configuration |
| Modèles de données (6 modèles) | ✅ | Haute | v0.1 | User, Group, ShiftType, Shift, OnCall, Leave |
| Système d'authentification | ✅ | Haute | v0.1 | Flask-Login avec rôles admin/utilisateur |
| Gestion des types de shifts | ✅ | Haute | v0.1 | Configuration des horaires |
| Planning des shifts | ✅ | Haute | v0.2 | Attribution et visualisation |
| Gestion des astreintes (On-Call) | ✅ | Haute | v0.2 | Rotations et notifications |
| Gestion des congés | ✅ | Haute | v0.2 | Saisie et visualisation |
| Export ICS | ✅ | Moyenne | v0.3 | Intégration calendrier externe |
| Système de logging avancé | ✅ | Haute | v0.3 | Rotation, syslog, filtrage |
| Gestion des erreurs personnalisées | ✅ | Haute | v0.3 | Pages 400-504 |

### Phase 2 : ✅ Tests et Qualité (Terminé - v0.4)

**Objectif** : Assurer la qualité du code et la couverture des tests

| Élément | Statut | Priorité | Livraison | Détails |
|---------|--------|----------|-----------|---------|
| **Tests unitaires complets** | ⚠️ | **Haute** | v0.4 | **515 tests** - Couverture ~66%, 2 échecs à corriger |
| **Tests d'intégration** | ✅ | Haute | v0.4 | Scénarios utilisateurs complets |
| **Tests des gestionnaires d'erreurs** | ✅ | Moyenne | v0.4 | Toutes les erreurs HTTP |
| **Tests de l'export ICS** | ✅ | Moyenne | v0.4 | Shifts, astreintes, congés |
| **Tests de l'automatisation** | ✅ | Moyenne | v0.4 | Règles métiers complexes |
| **Tests des décorateurs** | ✅ | Moyenne | v0.4 | Permissions et accès (2 fichiers de tests) |
| **Tests du thème sombre** | ✅ | Moyenne | v0.4 | 11 tests dédiés |
| Optimisation des requêtes SQL | ✅ | Moyenne | v0.4 | Index composites, joinedload |
| Gestion des erreurs améliorée | ✅ | Moyenne | v0.4 | Pages d'erreur personnalisées |
| Journalisation (Logging) | ✅ | Moyenne | v0.4 | Configuration complète |

### Phase 3 : ✅ Automatisation Avancée (Terminé - v0.5)

**Objectif** : Implémentation des règles métiers complexes

| Élément | Statut | Priorité | Livraison | Détails |
|---------|--------|----------|-----------|---------|
| **Règles métiers shifts** | ✅ | **Haute** | v0.5 | 5 règles complexes |
| **Automatisation des astreintes** | ✅ | **Haute** | v0.5 | Rotation automatique |
| **Gestion des conflits** | ✅ | **Haute** | v0.5 | Congés vs shifts vs astreintes |
| **Module advanced_shift_automation** | ✅ | **Haute** | v0.5 | Règles spécifiques |
| **Contrainte légale** | ✅ | **Haute** | v0.5 | Pas 2 astreintes de suite |

**Règles métiers implémentées dans `advanced_shift_automation.py` :**
1. ✅ Créneau 13h-21h : Réservé à la personne d'astreinte SI elle fait partie d'un groupe schedule
2. ✅ Rotation des créneaux : Si une personne était sur 13h-21h une semaine, elle doit être sur 07h-15h la semaine suivante
3. ✅ Créneau par défaut : 09h-17h pour tous les autres cas (plusieurs personnes peuvent être sur ce créneau)
4. ✅ Cas des congés : Si seulement 2 personnes disponibles, la personne NON d'astreinte doit être sur 07h-15h
5. ✅ Contrainte légale : Pas 2 astreintes de suite - minimum 2 semaines sans astreinte entre deux astreintes

**Modules d'automatisation :**
- `automation.py` (991 lignes) : Logique principale de rotation
- `advanced_shift_automation.py` (19,242 lignes) : Règles métiers complexes
- `cache.py` (19,242 lignes) : Système de cache
- `lazy_loading.py` (26,729 lignes) : Chargement paresseux
- `optimizations.py` (28,152 lignes) : Optimisations des performances
- `pagination.py` (734 lignes) : Pagination
- `performance_monitor.py` (875 lignes) : Monitoring des performances

### Phase 4 : ✅ Stabilisation et Pré-production (Terminé - v0.6)

**Objectif** : Préparation pour le déploiement en production

| Élément | Statut | Priorité | Livraison | Détails |
|---------|--------|----------|-----------|---------|
| **Correction des bugs critiques** | ✅ | **Haute** | v0.6 | Refonte Phases 1-6 (voir report/) - **773 tests passent** |
| **Support PostgreSQL complet** | ⚠️ | **Haute** | v0.6 | Configuration possible (psycopg), tests CI toujours à ajouter |
| **Dockerisation** | ✅ | **Haute** | v0.6 | Build multi-stage optimisé (report/Phase 6, 415 Mo) |
| **CI/CD Pipeline** | ✅ | **Haute** | v0.6 | GitLab CI (`.gitlab-ci/.gitlab-ci.yml`, futur dépôt du projet) |
| **Configuration via environnement** | ✅ | Haute | v0.5 | Variables d'environnement complètes (ENVIRONMENT_VARIABLES.md) |
| **Documentation technique** | ✅ | Moyenne | v0.6 | Docs/architecture/, Docs/api/ |
| **Documentation utilisateur** | ✅ | Moyenne | v0.6 | Docs/guides/USER_GUIDE.md, Docs/guides/ADMIN_GUIDE.md |
| **Optimisation des performances** | ✅ | Moyenne | v0.6 | Cache, pagination, eager loading, compression Gzip/Brotli/Zstd |
| **Audit de sécurité** | ✅ | **Haute** | v0.5 | report/SECURITY_AUDIT_REPORT.md + CSP stricte (Phase 6) |
| **Backup automatique** | ✅ | Moyenne | v0.6 | Scripts backup_database.py et backup_config.py |
| **Refonte des assets statiques** | ✅ | Moyenne | v0.6 | CSS/FullCalendar + externalisation JS (CSP, Phase 6) |
| **Architecture en couches** | ✅ | Haute | v0.6 | repositories/ + services/ (report/Phase 2) |
| **Kubernetes ready** | ✅ | Moyenne | v0.6 | Manifests k8s/ complets (report/Phase 6) |
| **Monitoring Prometheus/Grafana** | ✅ | Moyenne | v0.6 | /metrics + dashboard importable (report/Phase 6) |

### Phase 5 : 📈 Améliorations majeures (Prévu - v0.7-v0.8)

**Objectif** : Ajout de fonctionnalités avancées et amélioration de l'expérience utilisateur

#### 5.1 Interface et Expérience Utilisateur

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Refonte de l'UI/UX** | ✅ | Haute | v0.7 | Design moderne et responsive (PR #103) : palette, burger mobile, composants, audit responsive |
| **Calendrier interactif** | ✅ | Haute | v0.7 | Drag & drop pour les shifts (FullCalendar, Phase 6) |
| **Tableau de bord utilisateur** | ✅ | Moyenne | v0.7 | Existe déjà (dashboard.html), rafraîchi visuellement en PR #103 |
| **Thème sombre/clair** | ✅ | Basse | v0.5 | **Déjà implémenté** (dark-theme.css) |
| **Accessibilité (WCAG)** | ⚠️ | Moyenne | v0.8 | Partiellement implémenté (skip link) |

#### 5.2 Fonctionnalités avancées

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Notifications par email** | ✅ | **Haute** | v0.7 | Rappels hebdomadaires shifts (dimanche) et astreinte (jeudi), SMTP via variables d'environnement, scripts cron autonomes (PR #106) |
| **Échanges de shifts entre utilisateurs** | ❌ | Moyenne | v0.8 | Système de demande et validation |
| **Multi-langues (i18n)** | ❌ | Moyenne | v0.8 | Français, Anglais, Espagnol |
| **Gestion des fuseaux horaires** | ❌ | Moyenne | v0.8 | Support multi-timezone |
| **Historique des modifications** | ❌ | Basse | v0.9 | Audit trail des changements |

#### 5.3 Intégrations externes

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Webhooks** | ❌ | Basse | v0.9 | Notifications vers des services externes |
| **API REST publique** | ❌ | Moyenne | v0.9 | Pour intégrations tierces |

### Phase 6 : 🚀 Production Ready (Prévu - v1.0)

**Objectif** : Préparation finale pour le déploiement en production

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Support MySQL/MariaDB** | ❌ | Moyenne | v1.0 | Alternative à PostgreSQL |
| **Scalabilité horizontale** | ❌ | Basse | v1.0 | Support multi-instances (replicas k8s déjà à 2) |
| **Monitoring et métriques** | ✅ | Moyenne | v0.6 | Prometheus (/metrics) + dashboard Grafana (report/Phase 6) |
| **Documentation finale** | ✅ | Moyenne | v0.6 | Docs/ complet (report/Phase 5) |
| **Version stable** | ❌ | **Haute** | v1.0 | Version recommandée pour la production |
| **Tests de charge** | ❌ | Moyenne | v1.0 | Benchmark et optimisation |

### Phase 7 : 🌟 Fonctionnalités futures (Prévu - v1.5-v3.0)

**Objectif** : Innovations et extensions du produit

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Application mobile** | ❌ | Basse | v2.0 | React Native ou Flutter |
| **Module de reporting** | ❌ | Moyenne | v1.5 | Statistiques et analytics |
| **API GraphQL** | ❌ | Basse | v1.5 | Alternative à l'API REST |

---

## 📊 Priorités par version

### Version 0.5 (Automatisation - **Terminé**)
- ✅ Tests unitaires complets (515 tests)
- ✅ Automatisation avancée (règles métiers)
- ✅ Gestion des conflits
- ✅ Contrainte légale (pas 2 astreintes de suite)
- ✅ Module advanced_shift_automation

### Version 0.6 (Stabilisation - **Terminé**)
- ✅ Configuration avancée (variables d'environnement)
- ✅ Documentation technique complète
- ✅ Audit de sécurité + CSP stricte
- ✅ Scripts de backup
- ✅ Refonte des assets statiques + externalisation JS
- ✅ Architecture en couches (repositories/services)
- ✅ Dockerisation (build multi-stage optimisé)
- ✅ CI/CD Pipeline (GitLab CI)
- ✅ Kubernetes ready (manifests k8s/)
- ✅ Monitoring (Prometheus + dashboard Grafana)
- ✅ 773 tests passent, couverture ~82%
- ⚠️ Support PostgreSQL (configuration possible, tests CI à ajouter)

### Version 0.7 (Fonctionnalités avancées - **items Haute priorité terminés**)
- ✅ Refonte UI/UX (PR #103 : palette, burger mobile, composants, dashboard, audit responsive)
- ✅ Calendrier interactif (drag & drop, FullCalendar)
- ✅ Notifications par email (PR #106)
- ❌ Multi-langues (i18n)

### Version 0.8 (Intégrations)
- ❌ Échanges de shifts entre utilisateurs
- ❌ Accessibilité WCAG complète
- ❌ API REST publique

### Version 0.9 (Pré-lancement)
- ❌ Webhooks
- ❌ Support MySQL/MariaDB
- ❌ Monitoring et métriques
- ❌ Tests de charge
- ❌ Documentation finale

### Version 1.0 (Lancement)
- ❌ Version stable pour la production
- ❌ Support complet de toutes les bases de données
- ❌ Documentation utilisateur finale
- ❌ Tous les tests passent (objectif : 500+ tests)
- ❌ Audit de sécurité validé
- ❌ Couverture des tests ≥ 80%

---

## 🔍 Analyse du dépôt (Juillet 2026)

### Statistiques du projet

| Métrique | Valeur | Détails |
|----------|--------|---------|
| **Tests** | **773 passent** | 0 échec (voir `python -m pytest tests/ -v`) |
| **Couverture de code** | **~82%** | `--cov=app --cov=config`, objectif ≥80% atteint |
| **Modèles de données** | 6 | User, Group, ShiftType, Shift, OnCall, Leave (app/models/, package) |
| **Architecture** | 3 couches | routes/ → services/ → repositories/ (report/Phase 2) |
| **Modules de routes** | Multiples fichiers/blueprint | main, admin, auth, export - chacun splité en plusieurs fichiers (ex: shift_routes.py, admin_user_routes.py) |
| **Modules utilitaires** | app/utils/, par sous-package | automation/, cache/, export/, security/, logging/, optimizations/, helpers/, health.py, prometheus_metrics.py |
| **Gestionnaires d'erreurs** | 9 | 400, 401, 403, 404, 405, 500, 502, 503, 504 + ValueError/TypeError |
| **Templates** | 30+ | Jinja2 templates (app/templates/) |
| **Fichiers de configuration** | app/config/ (package) | base.py, development.py, production.py, testing.py + config_oidc.py, config_performance.py |
| **Scripts** | scripts/ | backup_database.py, backup_config.py, validate_config.py, bug_hunt.sh, download_vendor_assets.py |
| **Infrastructure** | docker/, k8s/, grafana/, .gitlab-ci/ | build multi-stage, manifests k8s complets, dashboard Grafana, pipeline GitLab CI |

### Structure du projet

```
leviia-schedule/
├── app/
│   ├── __init__.py              # Factory create_app() + instance globale
│   ├── auth/                    # decorators.py, user_manager.py, oidc_auth.py
│   ├── config/                  # base.py, development.py, production.py, testing.py
│   ├── models/                  # base.py (BaseModel) + user, shift, oncall,
│   │                             # leave, automation_config
│   ├── repositories/            # UserRepository, GroupRepository,
│   │                             # ShiftRepository, ShiftTypeRepository,
│   │                             # OnCallRepository, LeaveRepository
│   ├── services/                # UserService, GroupService, ShiftService,
│   │                             # ShiftTypeService, OnCallService, LeaveService,
│   │                             # ExportService, ScheduleService,
│   │                             # AutomationAdminService
│   ├── routes/                  # blueprints auth/main/admin/export, chacun
│   │                             # splité en plusieurs fichiers (shift_routes.py,
│   │                             # admin_user_routes.py, etc.)
│   ├── utils/
│   │   ├── automation/          # OnCallAutomation, ShiftAutomation,
│   │   │                         # AdvancedShiftAutomation
│   │   ├── cache/, export/ (ics_exporter.py), security/ (token_manager.py),
│   │   │   logging/, optimizations/ (eager_load), helpers/
│   │   ├── health.py            # endpoints k8s /health /ready
│   │   └── prometheus_metrics.py
│   ├── static/                  # css/, js/ (modules ES6), vendor/ (local, no CDN)
│   └── templates/                # 30+ templates Jinja2
├── config_oidc.py, config_performance.py  # config standalone chargées directement
├── run.py                       # Point d'entrée (setup DB + app.run)
├── requirements.txt
├── tests/                       # unit/, integration/, e2e/ - 773 tests
├── Docs/                        # architecture/, api/, guides/, reference/, deployment/
├── report/                      # rapports d'audit + refonte Phases 1-6
├── docker/                      # Dockerfile (multi-stage), docker-compose.yml, Makefile
├── k8s/                         # deployment, service, ingress, configmap, secret,
│                                 # pvc, hpa, pdb, namespace
├── grafana/                     # dashboard JSON importable
├── .gitlab-ci/.gitlab-ci.yml    # pipeline CI/CD (futur dépôt GitLab)
└── scripts/                     # backup_database.py, backup_config.py,
                                  # validate_config.py, bug_hunt.sh
```

### Derniers changements (Commit 6e25cc2)

- **Merge PR #102** : Phase 6 - Optimisations supplémentaires (dernière d'une
  refonte en 6 phases, voir `report/Phase 1` à `report/Phase 6`)
- **Contexte** : CSP stricte + bug Talisman corrigé (en-têtes de sécurité
  silencieusement absents dès que `TALISMAN_FORCE_HTTPS=false`), compression
  Gzip/Brotli/Zstd activée (dépendance déclarée mais jamais branchée), CI/CD
  GitLab corrigée (double install, junit/coverage cassés, namespace k8s
  invalide), Dockerfile multi-stage réparé et promu (415 Mo vs 926 Mo),
  dashboard Grafana créé
- **Impact** : architecture en couches (repositories/services), 773 tests
  passent (couverture ~82%), infra Docker/k8s/CI/monitoring fonctionnelle
  et vérifiée en réel (pas seulement en théorie)

---

## 🔍 Suivi des dépendances

### Dépendances actuelles (requirements.txt)

| Dépendance | Version | Statut | Priorité |
|------------|---------|--------|----------|
| Flask | 3.1.3 | ✅ Stable | Basse |
| SQLAlchemy | 2.0.51 | ✅ Stable | Basse |
| Flask-SQLAlchemy | 3.1.1 | ✅ Stable | Basse |
| Flask-Login | 0.6.3 | ✅ Stable | Basse |
| Flask-WTF | 1.3.0 | ✅ Stable | Basse |
| Flask-Talisman | 1.1.0 | ✅ Stable | Basse |
| flask-compress | 1.24 | ✅ Activé Phase 6 | Basse |
| flask-limiter | 4.1.1 | ✅ Stable | Basse |
| flask-cors | 6.0.5 | ✅ Stable | Basse |
| Authlib | 1.7.2 | ✅ Stable (OIDC/SSO) | Basse |
| icalendar | 7.2.0 | ✅ Stable | Basse |
| python-dateutil | 2.9.0.post0 | ✅ Stable | Basse |
| pytz | 2026.2 | ✅ Stable | Basse |
| psycopg[binary] | ≥3.3.4 | ✅ Présent (PostgreSQL optionnel) | Basse |
| redis | 5.0.1 | ✅ Présent (cache optionnel) | Basse |

### Dépendances de développement

| Dépendance | Version | Statut | Priorité |
|------------|---------|--------|----------|
| pytest | 9.1.1 | ✅ Stable | Basse |
| pytest-flask | 1.3.0 | ✅ Stable | Basse |
| pytest-cov | 7.1.0 | ✅ Stable | Basse |
| Ruff | 0.15.20 | ✅ Stable | Basse |
| mypy | 2.1.0 | ✅ Stable | Basse |
| Black | 26.5.1 | ✅ Stable | Basse |
| Bandit | 1.9.4 | ✅ Stable | Basse |
| Safety | 3.8.1 | ✅ Stable | Basse |

### Dépendances docker/requirements.txt (production, en plus de ce qui précède)

| Dépendance | Version | Rôle |
|------------|---------|------|
| gunicorn | 26.0.0 | Serveur WSGI de production |
| requests | 2.34.2 | Requis par Authlib/OIDC |

---

## 📝 Méthodologie

### Processus de développement

1. **Planification** : Les fonctionnalités sont priorisées selon leur impact et leur complexité
2. **Développement** : Branches de fonctionnalités (`feature/*`) avec revues de code
3. **Tests** : Tests unitaires et d'intégration obligatoires pour chaque PR
4. **Revue** : Revue par au moins un autre contributeur avant merge
5. **Documentation** : Mise à jour de la documentation pour chaque nouvelle fonctionnalité
6. **Validation** : Tous les tests doivent passer avant merge (`make test`)

### Critères d'acceptation

- [x] Code respectant les standards PEP 8 (vérifié par Ruff)
- [x] Tests unitaires avec couverture ≥ 80% (actuellement **773 tests passent, couverture ~82%**)
- [x] Documentation mise à jour
- [x] Pas de régression sur les fonctionnalités existantes
- [x] Revue de sécurité pour les changements critiques
- [x] Audit de sécurité complet (report/SECURITY_AUDIT_REPORT.md) + CSP stricte
- [x] Couverture des tests ≥ 80% (atteint, Phase 6)
- [x] Documentation utilisateur complète (report/Phase 5)
- [x] CI/CD Pipeline fonctionnel (GitLab CI, report/Phase 6)

### Commandes utiles

```bash
# Exécuter tous les tests
make test

# Exécuter avec couverture de code
pytest tests/ --cov=app --cov=config --cov-report=term-missing

# Linting
make lint

# Formatage
make format

# Sécurité
make security

# Tout vérifier
make all
```

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Consultez la section
[Contribution](README.md#-contribution) du README pour :

- Signaler un bug
- Proposer une nouvelle fonctionnalité
- Soumettre une Pull Request
- Participer aux discussions

### Comment contribuer à la feuille de route ?

1. **Ouvrez une Issue** pour discuter d'une nouvelle fonctionnalité
2. **Ouvrez une Discussion** pour proposer des améliorations
3. **Soumettez une Pull Request** avec vos implémentations
4. **Assurez-vous que tous les tests passent** (`make test`)
5. **Respectez les conventions de code** (`make lint`, `make format`)

### Bonnes pratiques

- Suivez les conventions de nommage existantes
- Ajoutez des tests pour chaque nouvelle fonctionnalité
- Mettez à jour la documentation
- Utilisez les décorateurs de permissions appropriés
- Respectez les principes SOLID

---

## 📞 Contact

Pour toute question concernant la feuille de route :
- Ouvrez une **Issue** sur GitHub
- Ouvrez une **Discussion** sur GitHub
- Contactez l'équipe via les canaux officiels

---

## 📄 Historique des versions de la feuille de route

| Version | Date | Auteur | Changements |
|---------|------|--------|-------------|
| 5.5.0 | Juillet 2026 | Claude Code | Refonte du système de sauvegarde (PR #107) : activation/configuration entièrement par variables d'environnement (`BACKUP_ENABLED`, opt-in comme les notifications), retrait de la scaffolding jamais consommée (`encrypt`/`encryption_key`/`frequency`), alertes email de succès/échec réutilisant le système de notifications existant (`BACKUP_NOTIFICATION_EMAIL`, soumis à `NOTIFICATIONS_ENABLED`), `BackupService` + interface d'administration (`/admin/backups` : configuration, liste local/S3, création à la demande, nettoyage, téléchargement avec protection contre la traversée de chemin), intégration Docker (crond conditionnel sur `BACKUP_ENABLED`, planning dans `docker/crontabs/appuser`, même conteneur que l'application - pas de service Docker séparé). Documentation mise à jour (ENVIRONMENT_VARIABLES.md, BACKUP_GUIDE.md, ADMIN_GUIDE.md, docker.md) et références obsolètes à `BACKUP_ENCRYPT`/`BACKUP_ENCRYPTION_KEY` corrigées au passage. Version app 0.7.3 -> 0.7.4. 916 tests |
| 5.4.0 | Juillet 2026 | Claude Code | Notifications par email (PR #106) : rappel hebdomadaire des shifts (dimanche, 24h avant le lundi) et de l'astreinte (jeudi, 24h avant le vendredi 21h), un email par semaine et par utilisateur (`NotificationLog` anti-doublon), SMTP configurable via variables d'environnement, deux scripts cron autonomes (`send_shift_notifications.py`/`send_oncall_notifications.py`, pattern `backup_database.py`), gabarits HTML + texte. Documentation mise à jour (README, CLAUDE.md, ADMIN_GUIDE.md, ARCHITECTURE.md, ERD.md, ENVIRONMENT_VARIABLES.md) et références obsolètes à `ShiftAutomation`/`business_rules.py`/`security/token_manager.py` (retirés en PR #105) corrigées au passage. Version app 0.7.2 -> 0.7.3. 891 tests |
| 5.3.0 | Juillet 2026 | Claude Code | Retouches de textes UI (PR #105) : titre calendrier index ("Calendrier interactif" -> "Calendrier"), description footer (l'app ne gère pas les "organisations"), boutons "Retour à l'admin" ajoutés sur /admin/users et /admin/automation (renommés depuis "Retour au tableau de bord" sur /admin/groups pour éviter la confusion avec le tableau de bord utilisateur), occurrences de "nouvelles règles métiers" nettoyées sur /admin/automation. Version app 0.7.1 -> 0.7.2 |
| 5.2.0 | Juillet 2026 | Claude Code | Amélioration génération automatique shifts/astreintes (PR #105) : retrait du moteur ShiftAutomation mort, dry-run "Génération complète" réparé, ordre de rotation respecté après congé, rééquilibrage après congé rendu atomique, nouvelle règle métier effectif minimum 1 personne, corrections confirmations de suppression (race condition JS), bouton "Sauvegarder l'ordre", astreintes en double sur vendredis adjacents, rechargement complet du calendrier remplacé par un rafraîchissement ciblé. Version app 0.7.0 -> 0.7.1. 862 tests (dont 27 E2E navigateur réel) |
| 5.1.0 | Juillet 2026 | Claude Code | Refonte UI/UX terminée et mergée (PR #103) : burger mobile (bug bloquant corrigé), palette teal/vert douce, composants rafraîchis, bug graphique dashboard corrigé, 3 bugs CSP trouvés et corrigés (2 pages avec script inline cassées - copie ICS, drag&drop rotation - + icônes calendrier invisibles, font-src manquant, trouvé via vérification réelle en navigateur/Playwright), audit responsive. Version app 0.6.0 -> 0.7.0. 781 tests |
| 5.0.0 | Juillet 2026 | Claude Code | Refonte Phases 1-6 terminée (report/) : architecture repositories/services, 773 tests (couverture ~82%), CSP stricte + Talisman toujours actif, compression Gzip/Brotli/Zstd, Docker multi-stage réparé et promu, CI/CD GitLab corrigée, k8s ready, dashboard Grafana. Commit 6e25cc2 (PR #102) |
| 4.0.0 | Juin 2026 | Vibe Code | Mise à jour après PR #85 : 522 tests (515 passent, 2 échouent, 7 ignorés), correction des assets statiques, commit 0adf3cc |
| 3.0.0 | Juin 2026 | Vibe Code | Analyse complète du dépôt, mise à jour des statistiques, ajout des détails techniques |
| 2.0.0 | Juin 2026 | Vibe Code | Mise à jour complète avec l'état actuel (403 tests, automatisation avancée) |
| 1.0.0 | Juin 2026 | Vibe Code | Création initiale de la feuille de route |

---

## 🎯 Prochaines étapes prioritaires

### À court terme (1-2 semaines)
1. **Finaliser le support PostgreSQL** avec tests CI (dernier point ouvert de la Phase 4/6)
2. **Migration vers GitLab** (dépôt cible du pipeline `.gitlab-ci/.gitlab-ci.yml`)
3. **Configurer un pipeline planifié** (audit dépendances indépendant des commits, voir report/Phase 6)
4. **Tester le dashboard Grafana** contre une instance réelle (créé mais non testé en environnement live)

### À moyen terme (1 mois)
1. **Implémenter les notifications par email**
2. **Améliorer l'accessibilité WCAG** (partiellement fait : skip link,
   focus-visible, aria - refonte UI/UX terminée mais audit WCAG complet
   pas encore fait)

### À long terme (3-6 mois)
1. **Support multi-langues (i18n)**
2. **API REST publique**
3. **Préparation pour la version 1.0 stable**

---

## ⚠️ Notes importantes

1. **Version de développement** : Ce projet est actuellement en phase de développement actif et **n'est pas prêt pour une utilisation en production** sans une revue complète (voir CLAUDE.md).
2. **Stabilité** : La version stable (v1.0) est prévue pour le déploiement en production.
3. **Sécurité** : Un audit de sécurité complet a été réalisé (report/SECURITY_AUDIT_REPORT.md), CSP stricte et en-têtes de sécurité toujours actifs depuis Phase 6.
4. **Tests** : **773 tests passent**, 0 échec, couverture ~82% (objectif ≥80% atteint).
5. **Documentation** : La documentation est complète pour les développeurs et administrateurs (Docs/, report/).
6. **Refonte Phases 1-6** : Un chantier qualité/infra en 6 phases (dépendances, backend, frontend, tests, documentation, optimisations) est terminé — voir `report/Phase 1` à `report/Phase 6` pour le détail de chaque bug trouvé et corrigé.

> **⚠️ Rappel** : Cette feuille de route est évolutive et peut être ajustée en fonction des priorités, des retours utilisateurs et des contraintes techniques. Les dates de livraison sont indicatives et peuvent varier.

---

*Document généré après analyse complète du dépôt - Dernière synchronisation : Juillet 2026*
*Commit analysé : b881b3da87f3336208a37ad8a278d0f63d1c5eb8 (Merge PR #103 - Refonte UI/UX)*
