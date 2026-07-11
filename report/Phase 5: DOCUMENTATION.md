# 📋 Rapport de Refactorisation - Phase 5: Documentation
**Branche** : `refacto/phase5`
**PR** : [#101](https://github.com/FoxOps/leviia-schedule/pull/101)
**Date de début** : 2026-07-12
**Statut** : 🟢 Terminée
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
- [x] Guide de démarrage rapide (`Docs/guides/QUICK_START.md`)
- [x] Guide d'installation (section dédiée dans `Docs/guides/USER_GUIDE.md`,
      plus complète que le quickstart)
- [x] Guide d'administration (`Docs/guides/ADMIN_GUIDE.md`, section
      SSO/OIDC ajoutée — promise par QUICK_START.md mais jamais écrite)
- [x] FAQ (`Docs/guides/FAQ.md`, nouveau, extrait et corrigé depuis
      USER_GUIDE.md)

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

### 2026-07-12 — 5.2 Documentation Utilisateur + nettoyage reference/ terminés

**QUICK_START.md / USER_GUIDE.md** : ni l'un ni l'autre ne mentionnait
`cp .env.example .env` avant le premier démarrage — sans ce fichier,
`DEFAULT_ADMIN_PASSWORD` n'est pas défini et `run.py` génère un mot de
passe admin aléatoire jamais affiché, pas `admin123` comme documenté
partout. Vérifié en confrontant `run.py::create_default_data` au
`.env.example` réel, corrigé aux deux endroits. `USER_GUIDE.md` corrigé
aussi sur `SQLALCHEMY_DATABASE_URI` (config Flask interne, pas le nom
réel de la variable d'environnement — c'est `DATABASE_URL`), les
sections "modifier un shift/une astreinte/un congé" (possible par
glisser-déposer en mode édition, réservé admin, pas juste "supprimer et
recréer"), et les règles de validation des congés (lues dans
`can_add_leave()` : aucune vérification de date future, aucun blocage
sur chevauchement shift/astreinte — rééquilibrage automatique à la
place).

**FAQ.md** (nouveau) : section FAQ extraite de `USER_GUIDE.md` (évite la
duplication constatée avec `SUMMARY.md`), corrigée sur les mêmes points,
plus une entrée sur les erreurs 400 liées au CSRF.

**ADMIN_GUIDE.md** : toutes les références à `config.py` corrigées vers
`app/config/` (+ précision sur la distinction avec le `config.py` legacy
racine) ; "Générer un token ICS via Admin > Utilisateurs" corrigé — c'est
un self-service (`POST /profile/ics-token`), la route admin décrite n'a
jamais existé ; chemins de personnalisation des règles métiers mis à jour
(`app/auth/decorators.py`, déplacé en Phase 2) ; "MySQL/MariaDB - à
venir" corrigé — déjà supporté via `DATABASE_URL`. **Section SSO/OIDC
complète ajoutée** (activation, désactivation de l'auth basique,
déconnexion RP-initiated, mapping des claims, cas Docker avec
`OIDC_INTERNAL_ISSUER`) : `QUICK_START.md` promettait ce contenu
("Guide Administrateur pour une configuration complète SSO/OIDC")
depuis toujours sans qu'il n'ait jamais existé.

**ENVIRONMENT_VARIABLES.md** : sections Pagination/Lazy Loading/
Optimisation des Requêtes/Monitoring des Performances retirées — toutes
lues par `config_performance.py`, module vérifié comme n'étant importé
nulle part dans `app/` ou `run.py` (les fonctionnalités qu'elles
configuraient ont été supprimées comme code mort en Phase 4). Les
définir dans `.env` n'a aujourd'hui aucun effet ; documenté explicitement
plutôt que silencieusement retiré. Section Cache réduite aux variables
réellement lues. Section SSO/OIDC complète ajoutée (absente auparavant).

**PERFORMANCE_OPTIMIZATION.md** réécrit intégralement : 1397 → ~100
lignes. ~90% de l'ancien contenu documentait des systèmes qui n'existent
plus (pagination avancée, lazy loading 785 lignes, un `PerformanceMonitor`
qui d'après l'audit Phase 4 n'a en réalité jamais fonctionné — import
cassé vers un module inexistant). Nouveau contenu : cache, `eager_load`,
index composites, pointeur vers `prometheus_metrics.py`/`health.py`.

**ERROR_HANDLING.md** : références `config.py` corrigées vers
`app/config/`, fonction de logging renommée (`configure_logging()` dans
`app/utils/logging/logger.py`, pas `setup_logging()` dans
`app/__init__.py`), note CSRF ajoutée.

**DEPLOYMENT_GUIDE.md** : fichier détecté comme binaire par `file`
(191 séquences corrompues — émojis et caractères accentués remplacés par
un octet de contrôle + le code hexadécimal du point de code Unicode en
texte littéral). Motif entièrement déterministe et réversible, décodé par
script ; 4 cas particuliers résolus manuellement par le contexte. Vérifié
: 0 octet de contrôle restant, tous les caractères Unicode valides, aucun
autre fichier de `Docs/` affecté par le même problème.

**Docs/README.md** reconstruit pour refléter la structure en
sous-dossiers. Vérification systématique de tous les liens markdown
internes (`Docs/` + `README.md` + `ROADMAP.md` racine, script Python,
résolution de chemin réelle) : 2 liens morts trouvés et corrigés
(`CONTRIBUTING.md` inexistant dans `ROADMAP.md`, ancre invalidée par un
renommage de section).

**Bilan de la phase** :
- `docs/` → `Docs/` réorganisé en 5 sous-dossiers, `SUMMARY.md` supprimé
- 3 fichiers réécrits intégralement (`ARCHITECTURE.md`, `API.md`,
  `PERFORMANCE_OPTIMIZATION.md` — tous jugés majoritairement fictifs par
  l'audit initial)
- 3 nouveaux documents techniques (`ERD.md`, `SEQUENCE_DIAGRAMS.md`,
  `openapi.yaml`) + 1 nouveau guide (`FAQ.md`)
- 5 fichiers corrigés (`USER_GUIDE.md`, `ADMIN_GUIDE.md`, `QUICK_START.md`,
  `ENVIRONMENT_VARIABLES.md`, `ERROR_HANDLING.md`)
- 1 bug d'encodage réel réparé (`DEPLOYMENT_GUIDE.md`, 191 séquences
  corrompues, décodage déterministe)
- Section SSO/OIDC écrite pour la première fois (promise depuis
  `QUICK_START.md`, jamais tenue)
- Plusieurs inexactitudes fonctionnelles corrigées après lecture directe
  du code (validation des congés, workflow de token ICS, mot de passe
  admin par défaut, modification de shifts/astreintes/congés)

---

*Dernière mise à jour : 2026-07-12*
