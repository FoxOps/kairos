# 📋 Rapport de Refactorisation - Phase 5: Documentation
**Branche** : `refacto/phase5`
**PR** : à créer
**Date de début** : 2026-07-12
**Statut** : 🟡 En cours
**Base** : `main` (inclut Phases 1 + 2 + 3 + 4, PR #100 mergée)

---

## 📈 État des lieux (avant restructuration)

Un dossier `docs/` (minuscule) existe déjà : 14 fichiers markdown,
~340 Ko, tous datés du 4 juillet — **avant** les Phases 2/3/4 qui ont
massivement changé l'architecture (main.py → services/repositories,
CSS/JS restructurés, tests réorganisés, CSRF ajouté, code mort
supprimé). Audit en cours pour distinguer ce qui reste exact de ce qui
est maintenant faux/obsolète, avant de décider quoi garder, réécrire ou
supprimer.

L'utilisateur a explicitement demandé que toute la documentation vive
dans un dossier `Docs/` (majuscule), avec sous-dossiers par type si
pertinent — `docs/` (minuscule, existant) sera donc renommé/réorganisé,
pas dupliqué.

---

## 🎯 Plan de travail

### 5.1 Documentation Technique
- [ ] Architecture : schémas Mermaid
- [ ] API : documentation OpenAPI/Swagger
- [ ] Base de données : schéma ERD
- [ ] Flux utilisateur : diagrammes de séquence

### 5.2 Documentation Utilisateur
- [ ] Guide de démarrage rapide
- [ ] Guide d'installation
- [ ] Guide d'administration
- [ ] FAQ

---

## 📝 Journal

*(mis à jour à chaque étape)*

---

*Dernière mise à jour : 2026-07-12*
