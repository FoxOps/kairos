# 📚 Documentation Leviia Schedule

> **Documentation officielle complète**
> **Version** : 1.0.0 | **Dernière mise à jour** : Juin 2026

---

## 🎯 **Index de la Documentation**

Ce document sert de **point d'entrée central** pour toute la documentation Leviia Schedule.
La documentation est organisée en **trois catégories principales** pour faciliter la navigation selon votre rôle.

---

## 👥 **📖 CATÉGORIE : UTILISATEURS**

*Pour les utilisateurs finaux qui consultent et gèrent leur planning quotidien*

| Document | Description | Temps de lecture | Public |
|----------|-------------|------------------|--------|
| [🚀 **Guide de Démarrage Rapide**](QUICK_START.md) | Installation, première connexion et configuration de base en 5 minutes | 5 min | ✅ Tous |
| [📖 **Guide Utilisateur Complet**](USER_GUIDE.md) | Documentation exhaustive pour l'utilisation quotidienne (15 chapitres) | 30 min | ✅ Tous |

### 📌 **Contenu de la catégorie Utilisateurs**

Le **Guide de Démarrage Rapide** couvre :
- Installation et configuration initiale
- Première connexion avec les identifiants par défaut
- Configuration de base (groupes, utilisateurs)
- Utilisation quotidienne
- Astuces rapides et dépannage express

Le **Guide Utilisateur Complet** couvre en détail :
1. Introduction à Leviia Schedule
2. Installation et configuration
3. Authentification et gestion de profil
4. Interface utilisateur et navigation
5. Gestion des utilisateurs (consultation)
6. Gestion des groupes (affichage)
7. Types de shifts disponibles
8. **Gestion des shifts** - Consultation et gestion de son planning
9. **Gestion des astreintes** - Visualisation de ses périodes d'astreinte
10. **Gestion des congés** - Saisie et suivi de ses congés
11. **Export ICS** - Intégration avec Google Calendar, Outlook, etc.
12. Automatisation (compréhension des règles)
13. Tableau de bord (accès utilisateur)
14. FAQ et dépannage
15. Support et contact

---

## 🛡️ **📖 CATÉGORIE : ADMINISTRATEURS**

*Pour les administrateurs qui configurent, gèrent et maintiennent l'application*

| Document | Description | Temps de lecture | Public |
|----------|-------------|------------------|--------|
| [🛡️ **Guide Administrateur**](ADMIN_GUIDE.md) | Configuration avancée, sécurité, maintenance et gestion complète | 40 min | ⚠️ Administrateurs |
| [🔄 **Guide de Sauvegarde**](BACKUP_GUIDE.md) | Procédures de sauvegarde et restauration de la base de données | 15 min | ⚠️ Administrateurs |
| [📈 **Guide d'Optimisation des Performances**](PERFORMANCE_OPTIMIZATION.md) | Optimisation de l'application pour les environnements de production | 20 min | ⚠️ Administrateurs |
| [🐳 **Guide Docker**](DOCKER_GUIDE.md) | Déploiement avec Docker et Docker Compose | 20 min | ⚠️ Administrateurs |

### 📌 **Contenu de la catégorie Administrateurs**

Le **Guide Administrateur** couvre :
1. Rôle et responsabilités de l'administrateur
2. **Gestion de la sécurité** - Bonnes pratiques, configuration SSL, protection des données
3. **Gestion avancée des utilisateurs** - Création, modification, suppression, permissions
4. **Architecture des groupes** - Organisation, hiérarchie, permissions par groupe
5. Configuration des types de shifts
6. **Tableau de bord et statistiques** - Suivi de l'activité, rapports
7. **Automatisation complète** - Configuration des règles métiers
8. **Configuration technique** - Paramètres avancés, variables d'environnement
9. Export et intégrations (configuration côté serveur)
10. Personnalisation de l'application
11. **Maintenance et sauvegardes** - Planification, procédures d'urgence
12. Gestion des erreurs (côté administration)

Le **Guide de Sauvegarde** couvre :
- Sauvegarde manuelle et automatique de la base de données
- Restauration des données
- Stratégies de sauvegarde (incrémentale, complète)
- Vérification de l'intégrité des sauvegardes
- Migration entre environnements

Le **Guide d'Optimisation des Performances** couvre :
- Optimisation de la base de données (index, requêtes)
- Configuration du pool de connexions
- Cache et optimisation des requêtes fréquentes
- Monitoring des performances
- Benchmarking et tests de charge

---

## 💻 **📖 CATÉGORIE : DÉVELOPPEURS**

*Pour les développeurs qui contribuent, étendent ou intègrent l'application*

| Document | Description | Temps de lecture | Public |
|----------|-------------|------------------|--------|
| [🏗️ **Architecture Technique**](ARCHITECTURE.md) | Architecture complète, composants, flux de données | 25 min | ✅ Développeurs |
| [🐳 **Guide Docker**](DOCKER_GUIDE.md) | Déploiement avec Docker et Docker Compose | 20 min | ✅ Tous |
| [📡 **API REST**](API.md) | Documentation complète de l'API (endpoints, schémas, exemples) | 20 min | ✅ Développeurs |
| [🔍 **Gestion des Erreurs**](ERROR_HANDLING.md) | Architecture de gestion des erreurs et système de logging | 15 min | ✅ Développeurs |
| [📝 **Résumé Technique**](SUMMARY.md) | Résumé complet de l'architecture, l'API et les composants | 20 min | ✅ Développeurs |

### 📌 **Contenu de la catégorie Développeurs**

Le **Document d'Architecture Technique** couvre :
- Vue d'ensemble de l'architecture
- Objectifs architecturaux
- Architecture globale (client-serveur, couches)
- **Structure du projet** - Organisation des fichiers et dossiers
- Composants techniques détaillés :
  - Backend (Flask)
  - Base de données (SQLAlchemy)
  - Authentification (Flask-Login)
  - Gestion des erreurs
  - Logging avancé
  - Export ICS
  - Automatisation
- **Modèles de données** - Diagramme Entité-Relation, modèles détaillés
- Flux de données
- Sécurité (implémentation technique)
- Environnements (développement, test, production)
- Performances et optimisations
- Configuration technique
- Tests et qualité de code
- Bonnes pratiques de développement

Le **Document API REST** couvre :
- Vue d'ensemble de l'API
- Authentification (sessions, tokens ICS)
- **Endpoints API complets** :
  - Authentification
  - Utilisateurs
  - Groupes
  - Types de Shifts
  - Shifts
  - Astreintes (On-Call)
  - Congés
  - Export ICS
  - Administration
- Schémas de données
- Exemples de requêtes (cURL, Python, JavaScript)
- Codes de réponse HTTP
- Bonnes pratiques d'utilisation de l'API

Le **Document de Gestion des Erreurs** couvre :
- Architecture de la gestion des erreurs
- Pages d'erreur personnalisées (400, 401, 403, 404, 405, 500, 502, 503, 504)
- Gestionnaires d'erreurs HTTP
- Gestion des exceptions Python
- **Système de logging complet** :
  - Configuration du logging
  - Niveaux de log
  - Fichiers de log (application, erreurs, HTTP, debug, audit)
  - Filtres de log (données sensibles)
  - Loggers spécifiques
  - Syslog pour la production
  - Audit logging
- Configuration avancée
- Bonnes pratiques
- Tests des gestionnaires d'erreurs

Le **Résumé Technique** couvre :
- Introduction complète au projet
- Résumé de l'architecture technique
- Résumé de l'API REST
- Résumé de la gestion des erreurs
- Structure de la documentation
- Guide d'utilisation de la documentation
- Résumé des composants techniques
- Configuration rapide pour les développeurs

---

## 🎯 **Par où commencer selon votre rôle ?**

### 🔹 **Je suis un utilisateur standard**
→ **Commencez ici** : [🚀 Guide de Démarrage Rapide](QUICK_START.md)
→ **Pour aller plus loin** : [📖 Guide Utilisateur Complet](USER_GUIDE.md)

### 🔹 **Je suis un administrateur**
→ **Commencez ici** : [🛡️ Guide Administrateur](ADMIN_GUIDE.md)
→ **Pour la sécurité** : [🛡️ Guide Administrateur - Section Sécurité](ADMIN_GUIDE.md#-gestion-de-la-sécurité)
→ **Pour les sauvegardes** : [🔄 Guide de Sauvegarde](BACKUP_GUIDE.md)
→ **Pour les performances** : [📈 Guide d'Optimisation](PERFORMANCE_OPTIMIZATION.md)

### 🔹 **Je suis un développeur**
→ **Commencez ici** : [🏗️ Architecture Technique](ARCHITECTURE.md)
→ **Pour intégrer l'API** : [📡 Documentation API REST](API.md)
→ **Pour comprendre la gestion des erreurs** : [🔍 Gestion des Erreurs](ERROR_HANDLING.md)
→ **Pour un résumé complet** : [📝 Résumé Technique](SUMMARY.md)

### 🔹 **Je veux tout savoir**
Lisez tous les documents dans l'ordre suivant :
1. [🚀 Guide de Démarrage Rapide](QUICK_START.md)
2. [📖 Guide Utilisateur Complet](USER_GUIDE.md)
3. [🛡️ Guide Administrateur](ADMIN_GUIDE.md)
4. [🏗️ Architecture Technique](ARCHITECTURE.md)
5. [📡 API REST](API.md)
6. [🔍 Gestion des Erreurs](ERROR_HANDLING.md)
7. [📝 Résumé Technique](SUMMARY.md)

---

## 🔍 **Comment chercher dans la documentation ?**

### 📌 **Par mots-clés**

| Mot-clé | Catégorie | Documents recommandés |
|---------|-----------|----------------------|
| installation, config, setup, démarrage | Utilisateurs | QUICK_START.md, USER_GUIDE.md |
| utilisateur, user, compte, profil | Utilisateurs | USER_GUIDE.md |
| admin, administrateur, permissions, sécurité | Administrateurs | ADMIN_GUIDE.md |
| shift, planning, calendrier, horaire | Utilisateurs/Administrateurs | USER_GUIDE.md, ADMIN_GUIDE.md |
| astreinte, on-call, garde, rotation | Utilisateurs/Administrateurs | USER_GUIDE.md, ADMIN_GUIDE.md |
| congé, absence, leave, vacance | Utilisateurs/Administrateurs | USER_GUIDE.md, ADMIN_GUIDE.md |
| export, ICS, Google Calendar, Outlook | Utilisateurs/Administrateurs | USER_GUIDE.md, ADMIN_GUIDE.md |
| automatisation, automation, règle | Administrateurs | ADMIN_GUIDE.md |
| sauvegarde, backup, restauration | Administrateurs | BACKUP_GUIDE.md |
| performance, optimisation, cache | Administrateurs | PERFORMANCE_OPTIMIZATION.md |
| architecture, modèle, base de données | Développeurs | ARCHITECTURE.md |
| API, endpoint, requête, JSON | Développeurs | API.md |
| erreur, error, exception, logging | Développeurs | ERROR_HANDLING.md |
| Flask, SQLAlchemy, Python | Développeurs | ARCHITECTURE.md, SUMMARY.md |

### 📌 **Par fonctionnalité**

| Fonctionnalité | Catégorie | Document | Section |
|---------------|-----------|----------|---------|
| **Première installation** | Utilisateurs | [QUICK_START.md](QUICK_START.md) | 🎯 En 5 Minutes |
| **Se connecter** | Utilisateurs | [USER_GUIDE.md](USER_GUIDE.md) | 🔐 Authentification |
| **Consulter mon planning** | Utilisateurs | [USER_GUIDE.md](USER_GUIDE.md) | 📅 Gestion des Shifts |
| **Prendre un congé** | Utilisateurs | [USER_GUIDE.md](USER_GUIDE.md) | 🏖️ Gestion des Congés |
| **Exporter vers mon calendrier** | Utilisateurs | [USER_GUIDE.md](USER_GUIDE.md) | 📤 Export ICS |
| **Créer un utilisateur** | Administrateurs | [ADMIN_GUIDE.md](ADMIN_GUIDE.md) | 👥 Gestion Avancée des Utilisateurs |
| **Configurer l'automatisation** | Administrateurs | [ADMIN_GUIDE.md](ADMIN_GUIDE.md) | ⚡ Automatisation Complète |
| **Sauvegarder la base** | Administrateurs | [BACKUP_GUIDE.md](BACKUP_GUIDE.md) | - |
| **Comprendre l'architecture** | Développeurs | [ARCHITECTURE.md](ARCHITECTURE.md) | 🏗️ Architecture Globale |
| **Utiliser l'API** | Développeurs | [API.md](API.md) | 📋 Endpoints API |
| **Gérer les erreurs** | Développeurs | [ERROR_HANDLING.md](ERROR_HANDLING.md) | 🏗️ Architecture de la Gestion des Erreurs |

---

## 📥 **Téléchargement et Conversion**

Tous les documents sont disponibles en format **Markdown** dans le dossier `docs/`.

### Convertir en PDF

```bash
# Méthode 1 : Utiliser pandoc (recommandé)
pandoc docs/USER_GUIDE.md -o USER_GUIDE.pdf

# Méthode 2 : Convertir tous les documents
for file in docs/*.md; do
  pandoc "$file" -o "${file%.md}.pdf"
done
```

### Convertir en HTML

```bash
# Méthode 1 : Utiliser pandoc
pandoc docs/README.md -o docs/README.html

# Méthode 2 : Utiliser un convertisseur en ligne
# Recommandé : https://markdowntohtml.com/
```

---

## 🤝 **Contribuer à la Documentation**

Les contributions à la documentation sont **les bienvenues** !

### Comment contribuer ?

1. **🐛 Signaler une erreur** : Ouvrez une [Issue GitHub](https://github.com/FoxOps/leviia-schedule/issues)
2. **💡 Proposer une amélioration** : Ouvrez une [Discussion GitHub](https://github.com/FoxOps/leviia-schedule/discussions)
3. **📝 Soumettre une modification** :
   - Forker le dépôt
   - Créer une branche (`git checkout -b docs/ma-contribution`)
   - Modifier les fichiers de documentation
   - Ouvrir une Pull Request

### Règles de contribution

- ✅ Respectez le **style existant** (titres, emojis, formatage)
- ✅ Utilisez des **exemples concrets** et des extraits de code
- ✅ Ajoutez des **captures d'écran** si nécessaire (dans un dossier `docs/images/`)
- ✅ Mettez à jour le **sommaire** et les **liens**
- ✅ Vérifiez l'**orthographe** et la **grammaire**
- ✅ Testez les **liens** et les **références**
- ✅ Suivez la **structure par catégories** définie dans ce document

---

## 📞 **Support et Contact**

### Vous avez une question ?

1. **📚 Consultez la documentation** : La plupart des questions sont répondues ici
2. **❓ Vérifiez les FAQ** : Dans le [Guide Utilisateur](USER_GUIDE.md#-faq-et-dépannage) ou le [Guide Administrateur](ADMIN_GUIDE.md)
3. **👨‍💼 Contactez votre administrateur** : Pour les problèmes spécifiques à votre instance

### Vous avez trouvé un bug ?

1. **🔍 Vérifiez qu'il n'est pas déjà signalé** : [Issues GitHub](https://github.com/FoxOps/leviia-schedule/issues)
2. **🐛 Ouvrez une nouvelle Issue** : [Créer une Issue](https://github.com/FoxOps/leviia-schedule/issues/new/choose)

### Vous voulez une nouvelle fonctionnalité ?

1. **📋 Vérifiez qu'elle n'est pas déjà prévue** : [Feuille de Route](../ROADMAP.md)
2. **💬 Ouvrez une Discussion** : [Créer une Discussion](https://github.com/FoxOps/leviia-schedule/discussions/new/choose)

---

## 📊 **Résumé des Documents**

| Catégorie | Document | Lignes | Chapitres | Temps de lecture |
|-----------|----------|--------|-----------|------------------|
| **Utilisateurs** | [QUICK_START.md](QUICK_START.md) | ~100 | 5 | 5 min |
| **Utilisateurs** | [USER_GUIDE.md](USER_GUIDE.md) | ~450 | 15 | 30 min |
| **Administrateurs** | [ADMIN_GUIDE.md](ADMIN_GUIDE.md) | ~600 | 12 | 40 min |
| **Administrateurs** | [BACKUP_GUIDE.md](BACKUP_GUIDE.md) | ~500 | 8 | 15 min |
| **Administrateurs** | [PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md) | ~600 | 10 | 20 min |
| **Développeurs** | [ARCHITECTURE.md](ARCHITECTURE.md) | ~700 | 15+ | 25 min |
| **Développeurs** | [API.md](API.md) | ~800 | 10+ | 20 min |
| **Développeurs** | [ERROR_HANDLING.md](ERROR_HANDLING.md) | ~400 | 8 | 15 min |
| **Développeurs** | [SUMMARY.md](SUMMARY.md) | ~500 | 10 | 20 min |

**Total** : ~9 documents | ~4,700 lignes | ~80 chapitres | ~3h30 de lecture complète

---

## 📝 **Historique des Versions**

| Version | Date | Auteur | Changements |
|---------|------|--------|-------------|
| 1.0.0 | Juin 2026 | Vibe Code | Création initiale de la documentation complète |
| 1.1.0 | Juin 2026 | Vibe Code | Réorganisation en catégories (Utilisateurs, Administrateurs, Développeurs) |

---

## 🎯 **Résumé Visuel**

```
┌─────────────────────────────────────────────────────────────────┐
│                    📚 DOCUMENTATION LEVIIA SCHEDULE                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                     │
│  👥 UTILISATEURS          🛡️ ADMINISTRATEURS          💻 DÉVELOPPEURS │
│  ─────────────          ─────────────────          ─────────────  │
│                                                                     │
│  • Guide de Démarrage    • Guide Administrateur    • Architecture   │
│    Rapide                • Guide de Sauvegarde      Technique      │
│  • Guide Utilisateur     • Guide d'Optimisation     • API REST      │
│    Complet               • Performances             • Gestion des   │
│                                                                     │
│                           Erreurs                    │
│                           • Résumé Technique          │
│                                                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

> **⚠️ Rappel** : Cette documentation est en constante évolution. N'hésitez pas à contribuer !

---

*© 2026 Leviia Schedule - Tous droits réservés selon la licence [CeCILL v2.1](../LICENSE)*
