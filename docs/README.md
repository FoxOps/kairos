# 📚 Documentation Leviia Schedule

> **Bienvenue dans la documentation officielle de Leviia Schedule**
> **Version** : 1.0.0 | **Dernière mise à jour** : Juin 2026

---

## 📋 Index de la Documentation

### 🎯 **Pour commencer**

| Document | Description | Public |
|----------|-------------|--------|
| [🚀 Guide de Démarrage Rapide](QUICK_START.md) | Installation et configuration en 5 minutes | ✅ Tous |
| [📖 Guide Utilisateur Complet](USER_GUIDE.md) | Documentation complète pour tous les utilisateurs | ✅ Tous |

### 🛡️ **Pour les Administrateurs**

| Document | Description | Public |
|----------|-------------|--------|
| [🛡️ Guide Administrateur](ADMIN_GUIDE.md) | Configuration avancée, sécurité, maintenance | ⚠️ Administrateurs |

### 📊 **Documentation Technique**

| Document | Description | Public |
|----------|-------------|--------|
| [📋 README.md](../README.md) | Documentation technique, installation, développement | ✅ Développeurs |
| [🗺️ ROADMAP.md](../ROADMAP.md) | Feuille de route du développement | ✅ Tous |
| [📝 TESTING_SUMMARY.md](../TESTING_SUMMARY.md) | Résumé des tests unitaires | ✅ Développeurs |
| [🔍 ERROR_HANDLING.md](ERROR_HANDLING.md) | Gestion des erreurs et exceptions | ✅ Développeurs |

---

## 🎯 **Par où commencer ?**

### Vous êtes un **utilisateur standard**
→ Commencez par le **[Guide de Démarrage Rapide](QUICK_START.md)** pour une prise en main rapide
→ Consultez le **[Guide Utilisateur Complet](USER_GUIDE.md)** pour toutes les fonctionnalités

### Vous êtes un **administrateur**
→ Lisez le **[Guide Administrateur](ADMIN_GUIDE.md)** pour la configuration et la gestion
→ Consultez le **[Guide Utilisateur](USER_GUIDE.md)** pour comprendre l'utilisation quotidienne

### Vous êtes un **développeur**
→ Lisez le **[README.md](../README.md)** pour l'installation et le développement
→ Consultez la **[Feuille de Route](../ROADMAP.md)** pour les fonctionnalités à venir
→ Explorez le **[ERROR_HANDLING.md](ERROR_HANDLING.md)** pour la gestion des erreurs

---

## 📚 **Structure de la Documentation**

```
docs/
├── 📖 USER_GUIDE.md          # Guide utilisateur complet (450+ lignes)
├── 🛡️ ADMIN_GUIDE.md         # Guide administrateur (600+ lignes)
├── 🚀 QUICK_START.md          # Guide de démarrage rapide
├── 📚 README.md               # Index de la documentation (ce fichier)
└── 🔍 ERROR_HANDLING.md       # Gestion des erreurs (existant)
```

---

## 🎓 **Contenu des Guides**

### 📖 Guide Utilisateur Complet

**15 chapitres** couvrant :
1. Introduction à Leviia Schedule
2. Installation et configuration
3. Authentification
4. Interface utilisateur
5. Gestion des utilisateurs
6. Gestion des groupes
7. Gestion des types de shifts
8. Gestion des shifts
9. Gestion des astreintes (On-Call)
10. Gestion des congés
11. Export ICS et intégration calendrier
12. Automatisation avancée
13. Tableau de bord administrateur
14. FAQ et dépannage
15. Support et contact

**Taille** : ~450 lignes | **Temps de lecture** : ~30 minutes

### 🛡️ Guide Administrateur

**12 chapitres** couvrant :
1. Rôle de l'administrateur
2. Gestion de la sécurité
3. Gestion avancée des utilisateurs
4. Architecture des groupes
5. Configuration des types de shifts
6. Tableau de bord et statistiques
7. Automatisation complète
8. Configuration technique
9. Export et intégrations
10. Personnalisation
11. Maintenance et sauvegardes
12. Gestion des erreurs

**Taille** : ~600 lignes | **Temps de lecture** : ~40 minutes

### 🚀 Guide de Démarrage Rapide

**Contenu** :
- Installation en 5 minutes
- Première connexion
- Configuration de base
- Utilisation quotidienne
- Astuces rapides
- Dépannage express

**Taille** : ~100 lignes | **Temps de lecture** : ~5 minutes

---

## 🔍 **Comment chercher dans la documentation ?**

### Par mots-clés

| Mot-clé | Documents pertinents |
|---------|----------------------|
| installation, config, setup | QUICK_START.md, USER_GUIDE.md, README.md |
| utilisateur, user, compte | USER_GUIDE.md, ADMIN_GUIDE.md |
| admin, administrateur, permissions | ADMIN_GUIDE.md, USER_GUIDE.md |
| shift, planning, calendrier | USER_GUIDE.md, ADMIN_GUIDE.md |
| astreinte, on-call, garde | USER_GUIDE.md, ADMIN_GUIDE.md |
| congé, absence, leave | USER_GUIDE.md, ADMIN_GUIDE.md |
| export, ICS, Google Calendar | USER_GUIDE.md, ADMIN_GUIDE.md |
| automatisation, automation | USER_GUIDE.md, ADMIN_GUIDE.md |
| sécurité, security, backup | ADMIN_GUIDE.md |
| erreur, error, bug | ERROR_HANDLING.md, ADMIN_GUIDE.md |

### Par fonctionnalité

| Fonctionnalité | Document | Section |
|---------------|----------|---------|
| Connexion | USER_GUIDE.md | 🔐 Authentification |
| Créer un utilisateur | ADMIN_GUIDE.md | 👥 Gestion Avancée des Utilisateurs |
| Configurer l'automatisation | ADMIN_GUIDE.md | ⚡ Automatisation Complète |
| Exporter vers Google Calendar | USER_GUIDE.md | 📤 Export ICS |
| Sauvegarder la base de données | ADMIN_GUIDE.md | 🔄 Maintenance et Sauvegardes |

---

## 📥 **Téléchargement**

Tous les documents sont disponibles en format Markdown dans le dossier `docs/`.

### Convertir en PDF

Pour convertir un document Markdown en PDF :

```bash
# Méthode 1 : Utiliser pandoc
pandoc docs/USER_GUIDE.md -o USER_GUIDE.pdf

# Méthode 2 : Utiliser un convertisseur en ligne
# (Recommandé : https://www.markdowntopdf.com/)
```

### Imprimer

1. Ouvrez le fichier Markdown dans un éditeur (VS Code, Typora, etc.)
2. Utilisez la fonction d'impression de votre navigateur
3. Sélectionnez le format paysage pour une meilleure lisibilité

---

## 🤝 **Contribuer à la Documentation**

Les contributions à la documentation sont les bienvenues !

### Comment contribuer ?

1. **Signaler une erreur** : Ouvrez une Issue sur GitHub
2. **Proposer une amélioration** : Ouvrez une Discussion sur GitHub
3. **Soumettre une modification** : Forker le dépôt, modifier les fichiers, ouvrir une Pull Request

### Règles de contribution

- Respectez le style existant (titres, emojis, formatage)
- Utilisez des exemples concrets
- Ajoutez des captures d'écran si nécessaire
- Mettez à jour le sommaire
- Vérifiez l'orthographe et la grammaire

---

## 📞 **Support et Contact**

### Vous avez une question ?

1. **Consultez la documentation** : La plupart des questions sont répondues ici
2. **Vérifiez les FAQ** : Dans le Guide Utilisateur ou le Guide Administrateur
3. **Contactez votre administrateur** : Pour les problèmes spécifiques à votre instance

### Vous avez trouvé un bug ?

1. **Vérifiez qu'il n'est pas déjà signalé** : [Issues GitHub](https://github.com/FoxOps/leviia-schedule/issues)
2. **Ouvrez une nouvelle Issue** : [Créer une Issue](https://github.com/FoxOps/leviia-schedule/issues/new)

### Vous voulez une nouvelle fonctionnalité ?

1. **Vérifiez qu'elle n'est pas déjà prévue** : [Feuille de Route](../ROADMAP.md)
2. **Ouvrez une Discussion** : [Créer une Discussion](https://github.com/FoxOps/leviia-schedule/discussions/new)

---

## 📝 **Historique des Versions**

| Version | Date | Auteur | Changements |
|---------|------|--------|-------------|
| 1.0.0 | Juin 2026 | Vibe Code | Création initiale de la documentation complète |

---

## 🎯 **Résumé**

| Besoin | Document | Temps de lecture |
|--------|----------|------------------|
| **Démarrage rapide** | [QUICK_START.md](QUICK_START.md) | 5 min |
| **Utilisation quotidienne** | [USER_GUIDE.md](USER_GUIDE.md) | 30 min |
| **Administration** | [ADMIN_GUIDE.md](ADMIN_GUIDE.md) | 40 min |
| **Développement** | [README.md](../README.md) | 20 min |

---

> **⚠️ Rappel** : Cette documentation est en constante évolution. N'hésitez pas à contribuer !

---

*© 2026 Leviia Schedule - Tous droits réservés selon la licence CeCILL v2.1*
