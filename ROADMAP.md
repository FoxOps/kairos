# 🗺️ Feuille de Route - Leviia Schedule

> **Version** : 2.0.0 - Mise à jour stratégique du développement
> **Dernière mise à jour** : Juin 2026
> **Statut** : Développement actif - **403 tests passent**

---

## 📌 Vue d'ensemble

Cette feuille de route présente les étapes clés et les priorités de développement pour **Leviia Schedule**, une application web de gestion des plannings et des astreintes.

## 🎯 Objectifs principaux

- ✅ **Fonctionnalités de base** : Implémentation complète des fonctionnalités principales
- ✅ **Tests complets** : 403 tests unitaires tous passants
- 🔄 **Stabilisation** : Corrections de bugs et optimisations
- 📈 **Améliorations** : Fonctionnalités avancées et intégrations
- 🚀 **Production Ready** : Préparation pour le déploiement en production

---

## 📊 État actuel du projet

### ✅ **Fonctionnalités implémentées et testées**

| Catégorie | Élément | Statut | Détails |
|----------|---------|--------|---------|
| **Cœur** | Gestion des utilisateurs | ✅ | CRUD complet + authentification |
| **Cœur** | Gestion des groupes | ✅ | Avec permissions schedule/oncall |
| **Cœur** | Gestion des shifts | ✅ | Avec types personnalisables |
| **Cœur** | Gestion des astreintes | ✅ | Rotations automatiques |
| **Cœur** | Gestion des congés | ✅ | Avec gestion des conflits |
| **Export** | Export ICS (shifts) | ✅ | Format iCalendar |
| **Export** | Export ICS (astreintes) | ✅ | Format iCalendar |
| **Export** | Export ICS (congés) | ✅ | Format iCalendar |
| **Export** | Authentification par token | ✅ | Accès sans session |
| **Sécurité** | Authentification Flask-Login | ✅ | Avec "remember me" |
| **Sécurité** | Gestion des permissions | ✅ | Décorateurs admin_required, user_owns_resource |
| **Sécurité** | Gestion des erreurs | ✅ | Pages personnalisées 400-504 |
| **Sécurité** | Logging complet | ✅ | Rotation, syslog, filtrage sensible |
| **Automatisation** | Règles métiers shifts | ✅ | 5 règles complexes implémentées |
| **Automatisation** | Rotation astreintes | ✅ | Vendredi 21h, 7 jours |
| **Automatisation** | Gestion des conflits | ✅ | Congés vs shifts vs astreintes |
| **Tests** | Tests unitaires | ✅ | **403 tests**, tous passent |
| **Tests** | Tests d'intégration | ✅ | Scénarios complets |
| **Tests** | Tests des erreurs | ✅ | Gestionnaires 400-504 |
| **Tests** | Tests d'export | ✅ | ICS, routes d'export |
| **Tests** | Tests d'automatisation | ✅ | Règles métiers |
| **Qualité** | Linting (Ruff) | ✅ | Configuration .ruff.toml |
| **Qualité** | Vérification types (mypy) | ✅ | Configuration complète |
| **Qualité** | Formatage (Black) | ✅ | Configuration complète |
| **Qualité** | Analyse sécurité (Bandit) | ✅ | Configuration complète |
| **Qualité** | Scan vulnérabilités (Safety) | ✅ | Configuration complète |
| **Infrastructure** | Configuration flexible | ✅ | Variables d'environnement |
| **Infrastructure** | Support SQLite | ✅ | Par défaut |
| **Infrastructure** | Support PostgreSQL | ⚠️ | Configuration possible, non testé en CI |
| **Infrastructure** | Makefile | ✅ | test, lint, format, security, all, clean |
| **Documentation** | README.md | ✅ | Complète et à jour |
| **Documentation** | ROADMAP.md | ✅ | Feuille de route détaillée |
| **Documentation** | TESTING_SUMMARY.md | ✅ | Documentation des tests |

---

## 📅 Phases de développement

### Phase 1 : ✅ Fondations (Terminé)

**Objectif** : Mise en place de l'architecture de base et des fonctionnalités principales

| Élément | Statut | Priorité | Livraison | Détails |
|---------|--------|----------|-----------|---------|
| Architecture Flask + SQLAlchemy | ✅ | Haute | v0.1 | Structure du projet et configuration |
| Modèles de données (Utilisateurs, Groupes, Shifts) | ✅ | Haute | v0.1 | Base de données SQLite |
| Système d'authentification | ✅ | Haute | v0.1 | Flask-Login avec rôles admin/utilisateur |
| Gestion des types de shifts | ✅ | Haute | v0.1 | Configuration des horaires |
| Planning des shifts | ✅ | Haute | v0.2 | Attribution et visualisation |
| Gestion des astreintes (On-Call) | ✅ | Haute | v0.2 | Rotations et notifications |
| Gestion des congés | ✅ | Haute | v0.2 | Saisie et visualisation |
| Export ICS | ✅ | Moyenne | v0.3 | Intégration calendrier externe |
| **Système de logging avancé** | ✅ | Haute | v0.3 | Rotation, syslog, filtrage |
| **Gestion des erreurs personnalisées** | ✅ | Haute | v0.3 | Pages 400-504 |

---

### Phase 2 : ✅ Tests et Qualité (Terminé)

**Objectif** : Assurer la qualité du code et la couverture des tests

| Élément | Statut | Priorité | Livraison | Détails |
|---------|--------|----------|-----------|---------|
| **Tests unitaires complets** | ✅ | **Haute** | v0.4 | **403 tests** - Couverture ~66% |
| **Tests d'intégration** | ✅ | Haute | v0.4 | Scénarios utilisateurs complets |
| **Tests des gestionnaires d'erreurs** | ✅ | Moyenne | v0.4 | Toutes les erreurs HTTP |
| **Tests de l'export ICS** | ✅ | Moyenne | v0.4 | Shifts, astreintes, congés |
| **Tests de l'automatisation** | ✅ | Moyenne | v0.4 | Règles métiers complexes |
| **Tests des décorateurs** | ✅ | Moyenne | v0.4 | Permissions et accès |
| **Optimisation des requêtes SQL** | ✅ | Moyenne | v0.4 | Index composites, joinedload |
| **Gestion des erreurs améliorée** | ✅ | Moyenne | v0.4 | Pages d'erreur personnalisées |
| **Journalisation (Logging)** | ✅ | Moyenne | v0.4 | Configuration complète |

---

### Phase 3 : ✅ Automatisation Avancée (Terminé)

**Objectif** : Implémentation des règles métiers complexes

| Élément | Statut | Priorité | Livraison | Détails |
|---------|--------|----------|-----------|---------|
| **Règles métiers shifts** | ✅ | **Haute** | v0.5 | 5 règles complexes |
| **Automatisation des astreintes** | ✅ | **Haute** | v0.5 | Rotation automatique |
| **Gestion des conflits** | ✅ | **Haute** | v0.5 | Congés vs shifts vs astreintes |
| **Module advanced_shift_automation** | ✅ | **Haute** | v0.5 | Règles spécifiques |
| **Contrainte légale** | ✅ | **Haute** | v0.5 | Pas 2 astreintes de suite |

**Règles métiers implémentées :**
1. ✅ Créneau 13h-21h : Réservé à la personne d'astreinte SI elle fait partie d'un groupe schedule
2. ✅ Rotation des créneaux : Si une personne était sur 13h-21h une semaine, elle doit être sur 07h-15h la semaine suivante
3. ✅ Créneau par défaut : 09h-17h pour tous les autres cas (plusieurs personnes peuvent être sur ce créneau)
4. ✅ Cas des congés : Si seulement 2 personnes disponibles, la personne NON d'astreinte doit être sur 07h-15h
5. ✅ Contrainte légale : Pas 2 astreintes de suite - minimum 2 semaines sans astreinte entre deux astreintes

---

### Phase 4 : 🔄 Stabilisation et Pré-production (En cours)

**Objectif** : Préparation pour le déploiement en production

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Correction des bugs critiques** | 🔄 | **Haute** | Continu | Suivi des issues GitHub |
| **Support PostgreSQL complet** | ⚠️ | **Haute** | v0.5 | Migration depuis SQLite, tests CI |
| **Dockerisation** | ❌ | **Haute** | v0.5 | Conteneurs pour déploiement facile |
| **CI/CD Pipeline** | ❌ | **Haute** | v0.5 | GitHub Actions pour tests et déploiement |
| **Configuration via environnement** | ✅ | Haute | v0.5 | Variables d'environnement complètes |
| **Documentation technique** | ❌ | Moyenne | v0.6 | Documentation API et architecture |
| **Documentation utilisateur** | ❌ | Moyenne | v0.6 | Guide d'utilisation complet |
| **Optimisation des performances** | ⚠️ | Moyenne | v0.6 | Cache, pagination, lazy loading |
| **Audit de sécurité** | ❌ | **Haute** | v0.9 | Analyse des vulnérabilités |
| **Backup automatique** | ❌ | Moyenne | v0.9 | Sauvegarde de la base de données |

---

### Phase 5 : 📈 Améliorations majeures

**Objectif** : Ajout de fonctionnalités avancées et amélioration de l'expérience utilisateur

#### 5.1 Interface et Expérience Utilisateur

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Refonte de l'UI/UX** | ❌ | Haute | v0.7 | Design moderne et responsive |
| **Calendrier interactif** | ❌ | Haute | v0.7 | Drag & drop pour les shifts |
| **Tableau de bord utilisateur** | ❌ | Moyenne | v0.7 | Vue d'ensemble personnalisée |
| **Thème sombre/clair** | ❌ | Basse | v0.8 | Préférences utilisateur |
| **Accessibilité (WCAG)** | ❌ | Moyenne | v0.8 | Conformité aux standards |

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

---

### Phase 6 : 🚀 Production Ready

**Objectif** : Préparation finale pour le déploiement en production

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Support MySQL/MariaDB** | ❌ | Moyenne | v1.0 | Alternative à PostgreSQL |
| **Scalabilité horizontale** | ❌ | Basse | v1.0 | Support multi-instances |
| **Monitoring et métriques** | ❌ | Moyenne | v1.0 | Prometheus, Grafana |
| **Documentation finale** | ❌ | Moyenne | v1.0 | Documentation complète |
| **Version stable** | ❌ | **Haute** | v1.0 | Version recommandée pour la production |

---

### Phase 7 : 🌟 Fonctionnalités futures

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

### Version 0.5 (Stabilisation - **En cours**)
- ✅ Tests unitaires complets (403 tests)
- ✅ Correction des bugs critiques
- ✅ Optimisation des requêtes SQL
- ✅ Gestion des erreurs améliorée
- ✅ Journalisation complète
- ✅ Automatisation avancée (règles métiers)
- ⚠️ Support PostgreSQL (configuration possible, tests CI à ajouter)
- ❌ Dockerisation
- ❌ CI/CD Pipeline

### Version 0.6 (Améliorations)
- ✅ Configuration avancée
- ❌ Notifications par email
- ❌ Répétition des shifts
- ❌ Refonte UI/UX
- ❌ Calendrier interactif
- ❌ Documentation technique
- ❌ Documentation utilisateur

### Version 0.7 (Fonctionnalités avancées)
- ❌ Multi-langues
- ❌ Google Calendar API
- ❌ Échanges de shifts
- ❌ Accessibilité WCAG
- ❌ Optimisation des performances

### Version 0.8 (Intégrations)
- ❌ Microsoft Outlook API
- ❌ API REST publique
- ❌ Webhooks
- ❌ Support MySQL
- ❌ Thème sombre/clair

### Version 0.9 (Pré-lancement)
- ❌ Audit de sécurité
- ❌ Backup automatique
- ❌ Documentation complète
- ❌ Monitoring et métriques

### Version 1.0 (Lancement)
- ❌ Version stable pour la production
- ❌ Support complet
- ❌ Documentation finale
- ❌ Tous les tests passent
- ❌ Audit de sécurité validé

---

## 🔍 Suivi des dépendances

### Dépendances actuelles

| Dépendance | Version actuelle | Version cible | Statut | Priorité |
|------------|------------------|---------------|--------|----------|
| Flask | 3.1.3 | ≥3.1 | ✅ Stable | Basse |
| SQLAlchemy | 2.0.51 | ≥2.0 | ✅ Stable | Basse |
| Flask-SQLAlchemy | 3.1.1 | ≥3.1 | ✅ Stable | Basse |
| Flask-Login | 0.6.3 | ≥0.6 | ✅ Stable | Basse |
| icalendar | 7.1.3 | ≥7.0 | ✅ Stable | Basse |
| python-dateutil | 2.9.0.post0 | ≥2.8 | ✅ Stable | Basse |
| pytz | 2026.2 | ≥2026.2 | ✅ Stable | Basse |
| pytest | 9.1.1 | ≥9.0 | ✅ Stable | Basse |
| pytest-flask | 1.3.0 | ≥1.3 | ✅ Stable | Basse |
| Ruff | 0.15.18 | ≥0.15 | ✅ Stable | Basse |
| mypy | 2.1.0 | ≥2.1 | ✅ Stable | Basse |
| Black | 26.5.1 | ≥26.5 | ✅ Stable | Basse |
| Bandit | 1.9.4 | ≥1.9 | ✅ Stable | Basse |
| Safety | 3.8.1 | ≥3.8 | ✅ Stable | Basse |
| cryptography | 49.0.0 | ≥49.0 | ✅ Stable | Moyenne |

### Dépendances à surveiller

| Dépendance | Version actuelle | Version cible | Action | Priorité |
|------------|------------------|---------------|--------|----------|
| Werkzeug | 3.1.8 | ≥3.1 | Mise à jour mineure | Moyenne |
| psycopg2-binary | - | - | À ajouter pour PostgreSQL | Moyenne |

---

## 📝 Méthodologie

### Processus de développement

1. **Planification** : Les fonctionnalités sont priorisées selon leur impact et leur complexité
2. **Développement** : Branches de fonctionnalités (`feature/*`) avec revues de code
3. **Tests** : Tests unitaires et d'intégration obligatoires pour chaque PR
4. **Revue** : Revue par au moins un autre contributeur avant merge
5. **Documentation** : Mise à jour de la documentation pour chaque nouvelle fonctionnalité
6. **Validation** : Tous les tests doivent passer avant merge

### Critères d'acceptation

- [x] Code respectant les standards PEP 8
- [x] Tests unitaires avec couverture ≥ 66% (actuellement 403 tests)
- [x] Documentation mise à jour
- [x] Pas de régression sur les fonctionnalités existantes
- [x] Revue de sécurité pour les changements critiques
- [ ] Couverture des tests ≥ 80% (objectif futur)
- [ ] Documentation utilisateur complète

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Consultez le [guide de contribution](CONTRIBUTING.md) pour :

- Signaler un bug
- Proposer une nouvelle fonctionnalité
- Soumettre une Pull Request
- Participer aux discussions

### Comment contribuer à la feuille de route ?

1. Ouvrez une **Issue** pour discuter d'une nouvelle fonctionnalité
2. Ouvrez une **Discussion** pour proposer des améliorations
3. Soumettez une **Pull Request** avec vos implémentations
4. Assurez-vous que tous les tests passent (`make test`)
5. Respectez les conventions de code (`make lint`, `make format`)

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
| 2.0.0 | Juin 2026 | Vibe Code | Mise à jour complète avec l'état actuel (403 tests, automatisation avancée) |
| 1.0.0 | Juin 2026 | Vibe Code | Création initiale de la feuille de route |

---

## 📊 Statistiques du projet

- **Lignes de code** : ~15,000+ (app/ + tests/)
- **Fichiers Python** : 30+ (15 dans app/, 15+ dans tests/)
- **Tests unitaires** : **403 tests** (tous passent ✅)
- **Couverture de code** : ~66%
- **Modèles de données** : 6 (User, Group, ShiftType, Shift, OnCall, Leave)
- **Modules de routes** : 5 (main, admin, auth, export, __init__)
- **Modules utilitaires** : 5 (decorators, helpers, ics_exporter, automation, advanced_shift_automation)
- **Décorateurs** : 8 (admin_required, role_required, user_owns_resource, user_can_edit_resource, user_can_delete_resource, etc.)
- **Gestionnaires d'erreurs** : 10 (400, 401, 403, 404, 405, 500, 502, 503, 504, Exception)
- **Fichiers de log** : 6 (app, errors, http, debug, audit, sql)

---

> **⚠️ Note importante** : Cette feuille de route est évolutive et peut être ajustée en fonction des priorités, des retours utilisateurs et des contraintes techniques. Les dates de livraison sont indicatives et peuvent varier.

---

*Document généré automatiquement - Dernière synchronisation avec le dépôt : Juin 2026*
