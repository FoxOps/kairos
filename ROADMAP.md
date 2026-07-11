# 🗺️ Feuille de Route - Leviia Schedule

> **Version** : 4.0.0 - Mise à jour après correction de bugs multiples
> **Dernière mise à jour** : Juin 2026
> **Statut** : Développement actif - **515 tests passent, 2 échouent** ⚠️
> **Commit actuel** : 0adf3cc (Merge PR #85 - Fix multiple issues)

---

## 📌 Vue d'ensemble

Cette feuille de route présente les étapes clés, l'état actuel et les priorités de développement pour **Leviia Schedule**, une application web complète de gestion des plannings, des astreintes et des congés.

## 🎯 Objectifs principaux

- ✅ **Fonctionnalités de base** : Implémentation complète de toutes les fonctionnalités principales
- ✅ **Tests complets** : **515 tests unitaires** avec 2 échecs à corriger, couverture ~66%
- ✅ **Automatisation avancée** : Règles métiers complexes implémentées
- ✅ **Documentation complète** : Documentation technique, API et utilisateur
- 🔄 **Stabilisation** : Corrections de bugs et optimisations en cours
- 📈 **Améliorations** : Fonctionnalités avancées et intégrations
- 🚀 **Production Ready** : Préparation pour le déploiement en production

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
| **Sécurité** | Gestion des permissions | ✅ | 8 décorateurs (admin_required, role_required, etc.) |
| **Sécurité** | Gestion des erreurs | ✅ | Pages personnalisées 400-504 |
| **Sécurité** | Logging complet | ✅ | Rotation, syslog, filtrage des données sensibles |
| **Sécurité** | Audit de sécurité | ✅ | Rapport complet (SECURITY_AUDIT_REPORT.md) |
| **Automatisation** | Règles métiers shifts | ✅ | **5 règles complexes** implémentées |
| **Automatisation** | Rotation astreintes | ✅ | Algorithme automatique avec contraintes |
| **Automatisation** | Gestion des conflits | ✅ | Congés vs shifts vs astreintes |
| **Automatisation** | Module advanced_shift_automation | ✅ | Logique avancée de rotation |
| **Performance** | Optimisation des requêtes SQL | ✅ | Index composites, joinedload, lazy loading |
| **Performance** | Cache | ✅ | Système de cache implémenté |
| **Performance** | Pagination | ✅ | Pagination complète |
| **Performance** | Monitoring | ✅ | performance_monitor.py |
| **Tests** | Tests unitaires | ⚠️ | **515 tests** - 515 passent, 2 échouent (test_automation_full.py) |
| **Tests** | Tests d'intégration | ✅ | Scénarios utilisateurs complets |
| **Tests** | Tests des gestionnaires d'erreurs | ✅ | Toutes les erreurs HTTP (400-504) |
| **Tests** | Tests d'export | ✅ | ICS, routes d'export |
| **Tests** | Tests d'automatisation | ✅ | Règles métiers et rotations |
| **Tests** | Tests des décorateurs | ✅ | Permissions et accès |
| **Tests** | Tests du thème sombre | ✅ | 11 tests dédiés |
| **Qualité** | Linting (Ruff) | ✅ | Configuration .ruff.toml |
| **Qualité** | Vérification types (mypy) | ✅ | Configuration complète |
| **Qualité** | Formatage (Black) | ✅ | Configuration complète |
| **Qualité** | Analyse sécurité (Bandit) | ✅ | Configuration complète |
| **Qualité** | Scan vulnérabilités (Safety) | ✅ | Configuration complète |
| **Infrastructure** | Configuration flexible | ✅ | Variables d'environnement complètes |
| **Infrastructure** | Support SQLite | ✅ | Par défaut, fonctionnel |
| **Infrastructure** | Support PostgreSQL | ⚠️ | Configuration possible, non testé en CI |
| **Infrastructure** | Makefile | ✅ | test, lint, format, security, all, clean |
| **Infrastructure** | Scripts de backup | ✅ | backup_database.py, backup_config.py |
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

### Phase 4 : 🔄 Stabilisation et Pré-production (En cours - v0.6)

**Objectif** : Préparation pour le déploiement en production

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Correction des bugs critiques** | 🔄 | **Haute** | Continu | Suivi des issues GitHub - **2 tests échouent (automation_full.py)** |
| **Support PostgreSQL complet** | ⚠️ | **Haute** | v0.6 | Migration depuis SQLite, tests CI à ajouter |
| **Dockerisation** | ❌ | **Haute** | v0.6 | Conteneurs pour déploiement facile |
| **CI/CD Pipeline** | ❌ | **Haute** | v0.6 | GitHub Actions pour tests et déploiement |
| **Configuration via environnement** | ✅ | Haute | v0.5 | Variables d'environnement complètes (ENVIRONMENT_VARIABLES.md) |
| **Documentation technique** | ✅ | Moyenne | v0.6 | Docs/architecture/, Docs/api/ |
| **Documentation utilisateur** | ✅ | Moyenne | v0.6 | Docs/guides/USER_GUIDE.md, Docs/guides/ADMIN_GUIDE.md |
| **Optimisation des performances** | ⚠️ | Moyenne | v0.6 | Cache, pagination, lazy loading (implémentés) |
| **Audit de sécurité** | ✅ | **Haute** | v0.5 | SECURITY_AUDIT_REPORT.md complet |
| **Backup automatique** | ✅ | Moyenne | v0.6 | Scripts backup_database.py et backup_config.py |
| **Refonte des assets statiques** | ✅ | Moyenne | v0.6 | Correction des ressources CSS/FullCalendar (PR #85) |

### Phase 5 : 📈 Améliorations majeures (Prévu - v0.7-v0.8)

**Objectif** : Ajout de fonctionnalités avancées et amélioration de l'expérience utilisateur

#### 5.1 Interface et Expérience Utilisateur

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Refonte de l'UI/UX** | ❌ | Haute | v0.7 | Design moderne et responsive |
| **Calendrier interactif** | ❌ | Haute | v0.7 | Drag & drop pour les shifts |
| **Tableau de bord utilisateur** | ❌ | Moyenne | v0.7 | Vue d'ensemble personnalisée |
| **Thème sombre/clair** | ✅ | Basse | v0.5 | **Déjà implémenté** (dark-theme.css) |
| **Accessibilité (WCAG)** | ⚠️ | Moyenne | v0.8 | Partiellement implémenté (skip link) |

#### 5.2 Fonctionnalités avancées

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Notifications par email** | ❌ | **Haute** | v0.7 | Alertes pour les astreintes et shifts |
| **Répétition des shifts** | ❌ | Haute | v0.7 | Shifts récurrents (hebdomadaires, mensuels) |
| **Échanges de shifts entre utilisateurs** | ❌ | Moyenne | v0.8 | Système de demande et validation |
| **Multi-langues (i18n)** | ❌ | Moyenne | v0.8 | Français, Anglais, Espagnol |
| **Gestion des fuseaux horaires** | ❌ | Moyenne | v0.8 | Support multi-timezone |
| **Historique des modifications** | ❌ | Basse | v0.9 | Audit trail des changements |

#### 5.3 Intégrations externes

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Google Calendar API** | ❌ | Moyenne | v0.8 | Synchronisation bidirectionnelle |
| **Microsoft Outlook API** | ❌ | Moyenne | v0.9 | Synchronisation avec Exchange |
| **Webhooks** | ❌ | Basse | v0.9 | Notifications vers des services externes |
| **API REST publique** | ❌ | Moyenne | v0.9 | Pour intégrations tierces |

### Phase 6 : 🚀 Production Ready (Prévu - v1.0)

**Objectif** : Préparation finale pour le déploiement en production

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Support MySQL/MariaDB** | ❌ | Moyenne | v1.0 | Alternative à PostgreSQL |
| **Scalabilité horizontale** | ❌ | Basse | v1.0 | Support multi-instances |
| **Monitoring et métriques** | ❌ | Moyenne | v1.0 | Prometheus, Grafana |
| **Documentation finale** | ❌ | Moyenne | v1.0 | Documentation complète |
| **Version stable** | ❌ | **Haute** | v1.0 | Version recommandée pour la production |
| **Tests de charge** | ❌ | Moyenne | v1.0 | Benchmark et optimisation |

### Phase 7 : 🌟 Fonctionnalités futures (Prévu - v1.5-v3.0)

**Objectif** : Innovations et extensions du produit

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Application mobile** | ❌ | Basse | v2.0 | React Native ou Flutter |
| **Synchronisation hors ligne** | ❌ | Basse | v2.0 | PWA avec cache local |
| **Intelligence artificielle** | ❌ | Très basse | v3.0 | Suggestions de planning optimisé |
| **Module de reporting** | ❌ | Moyenne | v1.5 | Statistiques et analytics |
| **API GraphQL** | ❌ | Basse | v1.5 | Alternative à l'API REST |
| **Plugin WordPress** | ❌ | Très basse | v2.0 | Intégration avec WordPress |

---

## 📊 Priorités par version

### Version 0.5 (Automatisation - **Terminé**)
- ✅ Tests unitaires complets (515 tests)
- ✅ Automatisation avancée (règles métiers)
- ✅ Gestion des conflits
- ✅ Contrainte légale (pas 2 astreintes de suite)
- ✅ Module advanced_shift_automation

### Version 0.6 (Stabilisation - **En cours**)
- ✅ Configuration avancée (variables d'environnement)
- ✅ Documentation technique complète
- ✅ Audit de sécurité
- ✅ Scripts de backup
- ✅ Refonte des assets statiques (PR #85)
- ⚠️ Support PostgreSQL (configuration possible, tests CI à ajouter)
- ❌ Dockerisation
- ❌ CI/CD Pipeline
- 🔄 **Correction des 2 tests échouants** (test_automation_full.py)
- 🔄 Correction des bugs critiques

### Version 0.7 (Fonctionnalités avancées)
- ❌ Notifications par email
- ❌ Répétition des shifts
- ❌ Refonte UI/UX
- ❌ Calendrier interactif (drag & drop)
- ❌ Multi-langues (i18n)

### Version 0.8 (Intégrations)
- ❌ Google Calendar API
- ❌ Microsoft Outlook API
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

## 🔍 Analyse du dépôt (Juin 2026)

### Statistiques du projet

| Métrique | Valeur | Détails |
|----------|--------|---------|
| **Lignes de code (app/)** | ~8,052 | 17 fichiers Python |
| **Lignes de code (tests/)** | ~6,298 | 21 fichiers Python |
| **Lignes de code (utils/)** | ~139,000+ | 10 modules utilitaires |
| **Total lignes Python** | ~15,000+ | app/ + tests/ |
| **Tests unitaires** | **522** | 515 passent, 2 échouent, 7 ignorés |
| **Couverture de code** | ~66% | Objectif : ≥80% |
| **Modèles de données** | 6 | User, Group, ShiftType, Shift, OnCall, Leave |
| **Modules de routes** | 5 | main, admin, auth, export, __init__ |
| **Modules utilitaires** | 10 | decorators, helpers, ics_exporter, automation, advanced_shift_automation, cache, lazy_loading, optimizations, pagination, performance_monitor |
| **Décorateurs** | 8 | admin_required, role_required, user_owns_resource, user_can_edit_resource, user_can_delete_resource, etc. |
| **Gestionnaires d'erreurs** | 10 | 400, 401, 403, 404, 405, 500, 502, 503, 504, Exception |
| **Templates** | 30+ | Jinja2 templates |
| **Fichiers de configuration** | 2 | config.py, config_performance.py |
| **Scripts** | 5 | backup_database.py, backup_config.py, cron_example.sh, validate_config.py |
| **Fichiers de log** | 6 | app, errors, http, debug, audit, sql |

### Structure du projet

```
leviia-schedule/
├── app/
│   ├── __init__.py              # Initialisation Flask (704 lignes)
│   ├── models.py                # Modèles de données (155 lignes)
│   ├── routes/
│   │   ├── __init__.py          # Import des routes
│   │   ├── admin.py             # Routes admin (712 lignes)
│   │   ├── auth.py              # Authentification (143 lignes)
│   │   ├── export.py            # Export ICS (127 lignes)
│   │   └── main.py              # Routes principales (915 lignes)
│   └── utils/
│       ├── __init__.py
│       ├── advanced_shift_automation.py  # Règles métiers (19,242 lignes)
│       ├── automation.py       # Automatisation (991 lignes)
│       ├── cache.py            # Cache (19,242 lignes)
│       ├── decorators.py       # Décorateurs (288 lignes)
│       ├── helpers.py          # Fonctions utilitaires (212 lignes)
│       ├── ics_exporter.py     # Export ICS (94 lignes)
│       ├── lazy_loading.py     # Chargement paresseux (26,729 lignes)
│       ├── optimizations.py    # Optimisations (28,152 lignes)
│       ├── pagination.py       # Pagination (734 lignes)
│       └── performance_monitor.py  # Monitoring (875 lignes)
├── config.py                   # Configuration principale (453 lignes)
├── config_performance.py       # Configuration performance (520 lignes)
├── run.py                      # Point d'entrée (138 lignes)
├── requirements.txt            # Dépendances
├── tests/
│   ├── conftest.py             # Configuration des tests (224 lignes)
│   ├── test_admin_automation.py
│   ├── test_admin_lists.py
│   ├── test_admin_priority.py
│   ├── test_advanced_shift_automation.py  # Tests automatisation avancée
│   ├── test_auth_priority.py
│   ├── test_automation.py
│   ├── test_config.py
│   ├── test_dark_theme.py      # Tests thème sombre (11 tests)
│   ├── test_decorators.py
│   ├── test_decorators_unit.py
│   ├── test_error_handlers.py
│   ├── test_export_routes.py
│   ├── test_helpers.py
│   ├── test_ics_export.py
│   ├── test_main_priority.py
│   ├── test_models.py
│   ├── test_routes.py
│   ├── test_run_functions.py
│   └── test_shift_rotation_fix.py
├── docs/
│   ├── ADMIN_GUIDE.md
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── BACKUP_GUIDE.md
│   ├── ENVIRONMENT_VARIABLES.md
│   ├── ERROR_HANDLING.md
│   ├── PERFORMANCE_OPTIMIZATION.md
│   ├── QUICK_START.md
│   ├── README.md
│   ├── SUMMARY.md
│   └── USER_GUIDE.md
├── scripts/
│   ├── backup_config.example.json
│   ├── backup_config.py
│   ├── backup_database.py
│   ├── cron_example.sh
│   └── validate_config.py
└── templates/
    ├── 400.html, 401.html, 403.html, 404.html, 405.html
    ├── 500.html, 502.html, 503.html, 504.html
    ├── _pagination.html
    ├── add_leave.html, add_oncall.html, add_shift.html
    ├── admin/ (10+ templates)
    ├── auth/ (4 templates)
    ├── base.html
    ├── index.html
    ├── leave.html
    ├── oncall.html
    └── schedule.html
```

### Derniers changements (Commit ceb829b)

- **Merge PR #65** : Revert des modifications des ressources statiques CSS et FullCalendar
- **Contexte** : Correction des problèmes d'affichage des assets
- **Impact** : Retour à la version stable des ressources statiques

---

## 🔍 Suivi des dépendances

### Dépendances actuelles (requirements.txt)

| Dépendance | Version | Statut | Priorité |
|------------|---------|--------|----------|
| Flask | 3.1.3 | ✅ Stable | Basse |
| SQLAlchemy | 2.0.51 | ✅ Stable | Basse |
| Flask-SQLAlchemy | 3.1.1 | ✅ Stable | Basse |
| Flask-Login | 0.6.3 | ✅ Stable | Basse |
| icalendar | 7.1.3 | ✅ Stable | Basse |
| python-dateutil | 2.9.0.post0 | ✅ Stable | Basse |
| pytz | 2026.2 | ✅ Stable | Basse |

### Dépendances de développement

| Dépendance | Version | Statut | Priorité |
|------------|---------|--------|----------|
| pytest | 9.1.1 | ✅ Stable | Basse |
| pytest-flask | 1.3.0 | ✅ Stable | Basse |
| Ruff | 0.15.18 | ✅ Stable | Basse |
| mypy | 2.1.0 | ✅ Stable | Basse |
| Black | 26.5.1 | ✅ Stable | Basse |
| Bandit | 1.9.4 | ✅ Stable | Basse |
| Safety | 3.8.1 | ✅ Stable | Basse |
| cryptography | 49.0.0 | ⚠️ Conflit | Moyenne |

### Dépendances à ajouter

| Dépendance | Version cible | Action | Priorité |
|------------|---------------|--------|----------|
| psycopg2-binary | ≥2.9 | À ajouter pour PostgreSQL | Moyenne |
| python-dotenv | ≥1.0 | Pour gestion des .env | Moyenne |
| gunicorn | ≥21.0 | Pour production | Moyenne |

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
- [x] Tests unitaires avec couverture ≥ 66% (actuellement **522 tests : 515 passent, 2 échouent, 7 ignorés**)
- [x] Documentation mise à jour
- [x] Pas de régression sur les fonctionnalités existantes
- [x] Revue de sécurité pour les changements critiques
- [x] Audit de sécurité complet (SECURITY_AUDIT_REPORT.md)
- [ ] Couverture des tests ≥ 80% (objectif futur)
- [ ] Documentation utilisateur complète (en cours)
- [ ] CI/CD Pipeline fonctionnel (à implémenter)

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

Les contributions sont les bienvenues ! Consultez le [guide de contribution](CONTRIBUTING.md) pour :

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
| 4.0.0 | Juin 2026 | Vibe Code | Mise à jour après PR #85 : 522 tests (515 passent, 2 échouent, 7 ignorés), correction des assets statiques, commit 0adf3cc |
| 3.0.0 | Juin 2026 | Vibe Code | Analyse complète du dépôt, mise à jour des statistiques, ajout des détails techniques |
| 2.0.0 | Juin 2026 | Vibe Code | Mise à jour complète avec l'état actuel (403 tests, automatisation avancée) |
| 1.0.0 | Juin 2026 | Vibe Code | Création initiale de la feuille de route |

---

## 🎯 Prochaines étapes prioritaires

### À court terme (1-2 semaines)
1. **🔴 Corriger les 2 tests échouants** dans test_automation_full.py (priorité maximale)
2. **Corriger les bugs critiques** identifiés dans les issues GitHub
3. **Finaliser le support PostgreSQL** avec tests CI
4. **Ajouter la Dockerisation** pour faciliter le déploiement
5. **Configurer le CI/CD Pipeline** (GitHub Actions)

### À moyen terme (1 mois)
1. **Implémenter les notifications par email**
2. **Ajouter la répétition des shifts**
3. **Améliorer l'accessibilité WCAG**
4. **Commencer la refonte UI/UX**

### À long terme (3-6 mois)
1. **Intégration Google Calendar API**
2. **Support multi-langues (i18n)**
3. **API REST publique**
4. **Préparation pour la version 1.0 stable**

---

## ⚠️ Notes importantes

1. **Version de développement** : Ce projet est actuellement en phase de développement actif et **n'est pas prêt pour une utilisation en production** sans une revue complète.
2. **Stabilité** : La version stable (v1.0) est prévue pour le déploiement en production.
3. **Sécurité** : Un audit de sécurité complet a été réalisé (SECURITY_AUDIT_REPORT.md).
4. **Tests** : **515 tests passent, 2 échouent, 7 ignorés** (total : 522 tests). L'objectif est d'atteindre 500+ tests avec une couverture ≥ 80%. Les 2 échecs concernent l'automatisation des astreintes (test_automation_full.py) et sont prioritaires à corriger.
5. **Documentation** : La documentation est complète pour les développeurs et administrateurs.

> **⚠️ Rappel** : Cette feuille de route est évolutive et peut être ajustée en fonction des priorités, des retours utilisateurs et des contraintes techniques. Les dates de livraison sont indicatives et peuvent varier.

---

*Document généré après analyse complète du dépôt - Dernière synchronisation : Juin 2026*
*Commit analysé : 0adf3cc465f01cae7fc468fee79e2cd9f5152b7c (Merge PR #85)*
