# 📋 Rapport de Refactorisation - Phase 5: Documentation
**Branche** : `refacto/phase5`
**PR** : [#101](https://github.com/FoxOps/leviia-schedule/pull/101)
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
- [x] Architecture : schémas Mermaid (`Docs/architecture/ARCHITECTURE.md`)
- [x] API : documentation OpenAPI/Swagger (`Docs/api/API.md` + `openapi.yaml`)
- [x] Base de données : schéma ERD (`Docs/architecture/ERD.md`)
- [x] Flux utilisateur : diagrammes de séquence (`Docs/architecture/SEQUENCE_DIAGRAMS.md`)

### 5.2 Documentation Utilisateur
- [ ] Guide de démarrage rapide
- [ ] Guide d'installation
- [ ] Guide d'administration
- [ ] FAQ

---

## 📝 Journal

*(mis à jour à chaque étape)*

### 2026-07-12 — Réorganisation docs/ → Docs/ + 5.1 Documentation Technique terminée

**Audit préalable** (agent Explore, lecture des 14 fichiers + comparaison
avec `app/routes/*.py`, `app/models/*.py`, `CLAUDE.md`) : verdict par
fichier (KEEP / UPDATE / REWRITE / DELETE), liste réelle des endpoints
HTTP, liste réelle des champs de modèles. Base de tout le travail qui a
suivi plutôt que de réécrire à l'aveugle.

**Réorganisation** : `docs/` (14 fichiers, minuscule) → `Docs/`
(majuscule, demande explicite), éclaté en 5 sous-dossiers par type
(`architecture/`, `api/`, `guides/`, `deployment/`, `reference/`).
`SUMMARY.md` supprimé (confirmé pur résumé de résumés, aucun contenu
unique). Liens cassés corrigés dans `README.md` (racine), `ROADMAP.md`,
`.gitlab-ci/.gitlab-ci.yml`. `README.md` racine corrigé au passage sur
plusieurs points obsolètes trouvés en chemin : `app/models.py` →
`app/models/`, versions Authlib/icalendar, statistiques de tests (522
tests/66% avant Phase 4 → 768 tests/81% aujourd'hui), lien mort vers un
`TESTING_SUMMARY.md` qui n'a jamais existé.

**ARCHITECTURE.md** réécrit intégralement (l'ancienne version décrivait
`app/models.py` en fichier plat, aucune mention de services/repositories
ni du CSRF app-wide) — 2 diagrammes Mermaid (vue en couches, découpage
des blueprints sur plusieurs fichiers).

**ERD.md** (nouveau) : `erDiagram` Mermaid généré depuis les modèles
réels. Corrige une erreur de l'ancienne doc (`Leave` n'a pas de champ
`reason`) et documente `AutomationConfig`, absent de toute doc
précédente.

**SEQUENCE_DIAGRAMS.md** (nouveau) : 5 diagrammes — connexion basique,
connexion OIDC/SSO, ajout de congé avec rééquilibrage automatique des
shifts, mise à jour de shift par API JSON avec vérification CSRF, export
ICS (session ou token porteur).

**API.md** réécrit intégralement (l'ancienne version documentait des
routes fictives — `/leaves/my-leaves`, `/schedule/my-shifts`,
`/admin/users/generate-token/<id>` — et omettait la quasi-totalité des
vrais endpoints `/api/*`). **`openapi.yaml`** (nouveau) : spec OpenAPI
3.0 pour les 9 endpoints JSON réels, validée avec
`openapi-spec-validator`.

Prochaine étape : 5.2 documentation utilisateur (mise à jour
QUICK_START/USER_GUIDE/ADMIN_GUIDE, nouveau FAQ.md), puis nettoyage des
fichiers de référence (`ENVIRONMENT_VARIABLES.md`,
`PERFORMANCE_OPTIMIZATION.md`) qui documentent des fonctionnalités
supprimées comme code mort en Phase 4.

---

*Dernière mise à jour : 2026-07-12*
