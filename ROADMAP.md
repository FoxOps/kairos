# 🗺️ Feuille de Route - Leviia Schedule

> **Version** : 1.0.0 - Planification stratégique du développement
> **Dernière mise à jour** : Juin 2026
> **Statut** : Développement actif

---

## 📌 Vue d'ensemble

Cette feuille de route présente les étapes clés et les priorités de développement pour **Leviia Schedule**, une application web de gestion des plannings et des astreintes.

## 🎯 Objectifs principaux

- ✅ **Fonctionnalités de base** : Implémentation complète des fonctionnalités principales
- 🔄 **Stabilisation** : Tests, corrections de bugs et optimisations
- 📈 **Améliorations** : Fonctionnalités avancées et intégrations
- 🚀 **Production Ready** : Préparation pour le déploiement en production

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

---

### Phase 2 : 🔄 Stabilisation (En cours)

**Objectif** : Amélioration de la qualité, tests et préparation à la production

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Tests unitaires complets** | ⚠️ | **Haute** | v0.4 | Couverture à 80%+ des fonctionnalités |
| **Tests d'intégration** | ❌ | Haute | v0.4 | Scénarios utilisateurs complets |
| **Documentation technique** | ❌ | Moyenne | v0.4 | Documentation API et architecture |
| **Documentation utilisateur** | ❌ | Moyenne | v0.5 | Guide d'utilisation complet |
| **Correction des bugs critiques** | 🔄 | **Haute** | Continu | Suivi des issues GitHub |
| **Optimisation des requêtes SQL** | ❌ | Moyenne | v0.4 | Index, requêtes optimisées |
| **Gestion des erreurs améliorée** | ❌ | Moyenne | v0.4 | Pages d'erreur personnalisées |
| **Journalisation (Logging)** | ❌ | Moyenne | v0.4 | Configuration et niveaux de log |

---

### Phase 3 : 📈 Améliorations majeures

**Objectif** : Ajout de fonctionnalités avancées et amélioration de l'expérience utilisateur

#### 3.1 Interface et Expérience Utilisateur

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Refonte de l'UI/UX** | ❌ | Haute | v0.6 | Design moderne et responsive |
| **Calendrier interactif** | ❌ | Haute | v0.6 | Drag & drop pour les shifts |
| **Tableau de bord utilisateur** | ❌ | Moyenne | v0.6 | Vue d'ensemble personnalisée |
| **Thème sombre/clair** | ❌ | Basse | v0.7 | Préférences utilisateur |
| **Accessibilité (WCAG)** | ❌ | Moyenne | v0.7 | Conformité aux standards |

#### 3.2 Fonctionnalités avancées

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Notifications par email** | ❌ | **Haute** | v0.6 | Alertes pour les astreintes et shifts |
| **Répétition des shifts** | ❌ | Haute | v0.6 | Shifts récurrents (hebdomadaires, mensuels) |
| **Échanges de shifts entre utilisateurs** | ❌ | Moyenne | v0.7 | Système de demande et validation |
| **Multi-langues (i18n)** | ❌ | Moyenne | v0.7 | Français, Anglais, Espagnol |
| **Gestion des fuseaux horaires** | ❌ | Moyenne | v0.7 | Support multi-timezone |
| **Historique des modifications** | ❌ | Basse | v0.8 | Audit trail des changements |

#### 3.3 Intégrations externes

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Google Calendar API** | ❌ | Moyenne | v0.7 | Synchronisation bidirectionnelle |
| **Microsoft Outlook API** | ❌ | Moyenne | v0.8 | Synchronisation avec Exchange |
| **Webhooks** | ❌ | Basse | v0.8 | Notifications vers des services externes |
| **API REST publique** | ❌ | Moyenne | v0.8 | Pour intégrations tierces |

---

### Phase 4 : 🚀 Production Ready

**Objectif** : Préparation pour le déploiement en production et scalabilité

| Élément | Statut | Priorité | Livraison estimée | Détails |
|---------|--------|----------|-------------------|---------|
| **Support PostgreSQL** | ⚠️ | **Haute** | v0.5 | Migration depuis SQLite |
| **Support MySQL/MariaDB** | ❌ | Moyenne | v0.8 | Alternative à PostgreSQL |
| **Dockerisation** | ❌ | **Haute** | v0.5 | Conteneurs pour déploiement facile |
| **Configuration via environnement** | ⚠️ | Haute | v0.5 | Variables d'environnement complètes |
| **CI/CD Pipeline** | ❌ | **Haute** | v0.5 | GitHub Actions pour tests et déploiement |
| **Audit de sécurité** | ❌ | **Haute** | v0.9 | Analyse des vulnérabilités |
| **Optimisation des performances** | ❌ | Moyenne | v0.9 | Cache, pagination, lazy loading |
| **Scalabilité horizontale** | ❌ | Basse | v1.0 | Support multi-instances |
| **Backup automatique** | ❌ | Moyenne | v0.9 | Sauvegarde de la base de données |

---

### Phase 5 : 🌟 Fonctionnalités futures

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

### Version 0.4 (Stabilisation)
- ✅ Tests unitaires complets
- ✅ Correction des bugs critiques
- ✅ Optimisation des requêtes SQL
- ✅ Gestion des erreurs améliorée
- ✅ Journalisation complète

### Version 0.5 (Pré-production)
- ✅ Support PostgreSQL
- ✅ Dockerisation
- ✅ CI/CD Pipeline
- ✅ Configuration avancée

### Version 0.6 (Améliorations)
- ✅ Notifications par email
- ✅ Répétition des shifts
- ✅ Refonte UI/UX
- ✅ Calendrier interactif

### Version 0.7 (Fonctionnalités avancées)
- ✅ Multi-langues
- ✅ Google Calendar API
- ✅ Échanges de shifts
- ✅ Accessibilité WCAG

### Version 0.8 (Intégrations)
- ✅ Microsoft Outlook API
- ✅ API REST publique
- ✅ Webhooks
- ✅ Support MySQL

### Version 0.9 (Pré-lancement)
- ✅ Audit de sécurité
- ✅ Optimisation des performances
- ✅ Backup automatique
- ✅ Documentation complète

### Version 1.0 (Lancement)
- ✅ Version stable pour la production
- ✅ Support complet
- ✅ Documentation finale

---

## 🔍 Suivi des dépendances

### Dépendances critiques à surveiller

| Dépendance | Version actuelle | Version cible | Action | Priorité |
|------------|------------------|---------------|--------|----------|
| Flask | 3.1.1 | ≥3.0 | Mise à jour mineure | Moyenne |
| SQLAlchemy | 2.0.36 | ≥2.0 | Stable | Basse |
| python-dateutil | - | ≥2.8 | Mise à jour | Moyenne |
| icalendar | 5.0.14 | ≥5.0 | Stable | Basse |

---

## 📝 Méthodologie

### Processus de développement

1. **Planification** : Les fonctionnalités sont priorisées selon leur impact et leur complexité
2. **Développement** : Branches de fonctionnalités (`feature/*`) avec revues de code
3. **Tests** : Tests unitaires et d'intégration obligatoires pour chaque PR
4. **Revue** : Revue par au moins un autre contributeur avant merge
5. **Documentation** : Mise à jour de la documentation pour chaque nouvelle fonctionnalité

### Critères d'acceptation

- [ ] Code respectant les standards PEP 8
- [ ] Tests unitaires avec couverture ≥ 80%
- [ ] Documentation mise à jour
- [ ] Pas de régression sur les fonctionnalités existantes
- [ ] Revue de sécurité pour les changements critiques

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
| 1.0.0 | Juin 2026 | Vibe Code | Création initiale de la feuille de route |

---

> **⚠️ Note importante** : Cette feuille de route est évolutive et peut être ajustée en fonction des priorités, des retours utilisateurs et des contraintes techniques. Les dates de livraison sont indicatives et peuvent varier.

---

*Document généré automatiquement - Dernière synchronisation avec le dépôt : Juin 2026*