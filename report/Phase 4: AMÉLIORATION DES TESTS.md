# 📋 Rapport de Refactorisation - Phase 4: Amélioration des Tests
**Branche** : `refacto/phase4`
**PR** : à créer
**Date de début** : 2026-07-11
**Statut** : 🟡 En cours
**Base** : `main` (inclut Phases 1 + 2 + 3, PR #99 mergée)

---

## 📈 État des lieux (avant restructuration)

- 29 fichiers de tests, ~8085 lignes, tous à plat dans `tests/`, 511 tests,
  511 passent.
- `pytest-cov` **n'était pas installé** malgré le fait que `CLAUDE.md`
  documente déjà `pytest tests/ --cov=app --cov=config --cov-report=term-missing`
  comme commande existante — la commande plantait
  (`unrecognized arguments: --cov=app`). Installé maintenant.
- **Couverture réelle mesurée (baseline)** : **56%** (`app/` + `config.py`).
- Aucun test dédié pour la couche `app/services/` ou `app/repositories/`
  (créées en Phase 2) — seule `ScheduleService` a quelques tests indirects
  dans `test_main_coverage.py`/`test_main_priority.py`. Le reste
  (`UserService`, `GroupService`, `ShiftService`, `ShiftTypeService`,
  `OnCallService`, `LeaveService`, `ExportService`,
  `AutomationAdminService`) et tous les repositories ne sont couverts
  qu'indirectement via les tests de routes HTTP.
- **Pas de Selenium/Playwright, pas de chromedriver/geckodriver, pas de
  sudo** dans cet environnement : impossible d'installer un navigateur
  headless. Décision validée avec l'utilisateur : les tests "E2E" seront
  des parcours multi-requêtes via le client de test Flask existant
  (login → action → vérification → logout), pas de l'automatisation
  navigateur réelle. Documenté honnêtement plutôt que la case cochée sans
  base.

### Distorsion de la couverture par du code mort

Une partie non négligeable des lignes non couvertes vient de modules déjà
identifiés comme inutilisés dans `CLAUDE.md`, plus deux nouveaux repérés
cette phase :

| Module | Lignes | Couverture | Statut |
|---|---|---|---|
| `app/utils/monitoring/__init__.py` | 344 | 0% | mort (déjà noté dans CLAUDE.md) |
| `app/utils/pagination/__init__.py` | 248 | 0% | mort — atteignable seulement via des décorateurs eux-mêmes jamais appliqués (voir ci-dessous) |
| `app/utils/prometheus_metrics.py` | 86 | 0% | conditionnel (`PROMETHEUS_ENABLED`), pas mort mais jamais exercé en test |
| `app/utils/helpers/env_helpers.py` | 47 | 0% | mort (déjà noté dans CLAUDE.md) |
| `app/utils/cache/cache_helpers.py` | 40 | 0% | mort, zéro référence ailleurs dans `app/` |
| `app/utils/optimizations/__init__.py` (partiel) | ~230/292 non couvertes | 11% | seul `eager_load` est réellement importé par des routes (`admin_shift_type_routes.py`, `dashboard_routes.py`, `admin_user_routes.py`, `admin_group_routes.py`) ; `paginated_route`, `paginated_api`, `cached_route`, `cache_result`, `lazy_route`, `lazy_property_cache`, `batch_load`, `bulk_operation`, `retry_on_failure`, `measure_time` ne sont appliqués sur **aucune** route — code mort |

**Décision** : ne pas écrire de tests artificiels pour du code mort
uniquement pour gonfler le pourcentage — ça ne testerait rien de réel et
ça masquerait le vrai problème (du code jamais appelé qui devrait être
supprimé, pas testé). Un objectif de 80% sur le périmètre actuel inclut
~765 lignes de code mort confirmé ; un objectif réaliste et honnête porte
sur le code effectivement utilisé. Recommandation de suppression du code
mort documentée ici, suppression elle-même laissée à une décision
utilisateur séparée (hors périmètre "tests" de cette phase, et
`app/utils/monitoring/`/`env_helpers.py` sont déjà signalés comme tels
dans `CLAUDE.md` sans qu'une suppression n'ait été demandée jusqu'ici).

---

## 🎯 Plan de travail

### 4.1 Restructuration des tests
- [x] `tests/unit/` : 12 fichiers déplacés (sans client HTTP - models,
      automation, config, helpers...)
- [x] `tests/integration/` : 14 fichiers déplacés (passent par le client
      de test Flask - routes, auth, export...)
- [x] `tests/e2e/` : créé, rempli à l'étape suivante (parcours
      multi-requêtes, voir décision ci-dessus)
- [x] `tests/fixtures/` : `user_fixtures.py`, `shift_fixtures.py`,
      `leave_fixtures.py`, `oncall_fixtures.py` — extraits de `conftest.py`
      (qui ne garde que `test_app`/`client`), enregistrés via
      `pytest_plugins`
- [x] `Makefile` : chemins mis à jour (`test-main`, `test-dark-theme`) +
      nouvelles cibles `test-unit`/`test-integration`/`test-e2e`

### 4.2 Améliorations
- [x] `unit/test_services.py` + `unit/test_repositories.py` : tests réels
      pour la couche métier créée en Phase 2, jusqu'ici quasi intestée
      directement (107 tests, repositories 100%, services 90%+)
- [x] Couverture augmentée sur les couches ciblées (repositories/services) ;
      objectif 80% brut jugé non pertinent tel quel (voir distorsion par
      code mort ci-dessus), pas poursuivi aveuglément
- [x] Tests de performance (temps de réponse + détection N+1 sur
      `/schedule`)
- [x] Tests de sécurité — **a débouché sur deux vrais correctifs, pas
      seulement des tests** (voir Journal) :
      1. `User.to_dict()` exposait `password_hash` et `ics_token` (latent,
         rien ne l'appelait encore, mais c'était une bombe à retardement)
      2. **CSRF protection totalement absente de l'application** (pas
         seulement désactivée en test) - `Flask-WTF` est une dépendance,
         `WTF_CSRF_ENABLED` existe dans la config, mais `CSRFProtect`
         n'était instancié nulle part et aucun template n'avait de champ
         `csrf_token`. Corrigé : voir Journal pour le détail complet.
- [x] Tests d'accessibilité — déjà partiellement couverts par
      `test_dark_theme.py`/`test_theme_fixes.py` (Phase 3), pas de WCAG
      2.1 AA complet (hors scope confirmé en Phase 3)
- [x] ~~Tests E2E avec Selenium ou Playwright~~ → parcours via client de
      test Flask (décision validée, pas de navigateur headless réel)

---

## 📝 Journal

*(mis à jour à chaque étape)*

### 2026-07-11 — 4.1 Restructuration terminée

Déplacement mécanique (`git mv`, historique préservé) des 26 fichiers de
tests existants vers `tests/unit/` (12, pas de client HTTP) et
`tests/integration/` (14, passent par le client de test Flask).
`tests/e2e/` et `tests/fixtures/` créés.

`conftest.py` réduit à `test_app`/`client` ; les fixtures de modèles
(`test_group`, `test_user`, `admin_user`, `test_shift`, `test_leave`,
`test_oncall`, etc.) extraites vers `tests/fixtures/*.py`, rattachées via
`pytest_plugins` pour rester visibles partout sans import explicite.

**Bug réel attrapé par les tests avant commit** : j'ai d'abord supprimé
l'alias `app = test_app` en bas de `conftest.py` en le prenant pour du
code mort (grep ne montrait aucun test demandant une fixture nommée
`app`). En réalité `pytest-flask` s'appuie dessus via sa fixture autouse
`_configure_application`, qui cherche littéralement une fixture `app` —
sans lui, 2 tests plantaient au setup (`fixture 'app' not found`). Alias
restauré avec un commentaire expliquant pourquoi il existe, pour ne pas
retomber dans le même piège plus tard.

511 tests passent toujours (197 unit + 314 integration après la
restructuration).

### 2026-07-11 — Tests unitaires services/repositories + tests E2E + performance

`tests/unit/test_repositories.py` (UserRepository, GroupRepository,
ShiftTypeRepository, ShiftRepository, LeaveRepository, OnCallRepository)
et `tests/unit/test_services.py` (UserService, GroupService,
ShiftTypeService, ShiftService, OnCallService, LeaveService,
ExportService) : 107 tests appelant la couche métier/données directement.
Couverture : repositories 100%, services 90%+ (sauf
`automation_admin_service` et `oncall_service`, non couverts ici —
`automation_admin_service` délègue à `AdvancedShiftAutomation` qui a déjà
sa propre suite dédiée).

Bug attrapé avant commit : `test_add_shifts_for_range_conflict_rolls_back`
utilisait la fixture `test_shift` dont la date est `date.today()`, qui
tombe un **samedi** dans cet environnement — `add_shifts_for_range` saute
les week-ends avant de vérifier les conflits, donc le test ne testait
rien du tout (`conflict_date` restait toujours `None`). Corrigé en créant
explicitement un shift sur un jour ouvré.

`tests/e2e/test_user_flows.py` : 4 parcours multi-requêtes (pas de
navigateur réel, décision validée) — admin crée groupe → utilisateur →
assigne des shifts → l'utilisateur se connecte et voit son planning ;
utilisateur demande un congé pour lui-même (accepté) puis pour un autre
(rejeté, vérifié en base) ; login faux mot de passe puis bon mot de
passe, session invalidée après logout ; export ICS authentifié vs. rejeté
sans authentification.

`tests/integration/test_performance.py` : seuils larges sur `/schedule`
et `/dashboard` (attrape une régression grossière, pas un micro-
benchmark) + comptage de requêtes SQL pour vérifier que `joinedload()`
dans `ShiftRepository.list_paginated` évite le N+1. **Vérifié que le test
détecte vraiment une régression** : en retirant temporairement
`joinedload()` du code (13 requêtes au lieu de 3 pour 10 shifts), les
deux tests échouent immédiatement ; remis en place ensuite.

Bug attrapé avant commit : `_seed_shifts` utilisait des emails fixes
(`perf0@test.com`...) - appelée deux fois dans le même test avec des
tailles différentes, la deuxième insertion violait la contrainte unique
sur l'email. Corrigé avec un paramètre `offset`.

624 puis 628 tests passent au fil de ces ajouts.

### 2026-07-11 — Tests de sécurité : deux vrais correctifs, pas juste des tests

En écrivant `tests/integration/test_security.py`, deux problèmes réels
sont apparus - pas des artefacts de test, des trous présents en
production :

**1. `User.to_dict()` exposait `password_hash` et `ics_token`.**
`BaseModel.to_dict()` sérialise toutes les colonnes sans distinction ;
`User` n'avait pas de surcharge. Personne n'appelle `user.to_dict()`
dans le code actuel (vérifié par grep), donc latent - mais la méthode
existe et n'importe quel futur endpoint JSON qui l'utiliserait aurait
fuité le hash du mot de passe et le jeton d'export ICS (un jeton
porteur, équivalent à un mot de passe pour le flux anonyme). Corrigé par
une surcharge `User.to_dict()` qui retire ces deux champs. Testé
(`TestSensitiveDataNotSerialized`).

**2. La protection CSRF était totalement absente de l'application, pas
seulement désactivée en test.** `Flask-WTF` est une dépendance,
`WTF_CSRF_ENABLED` existe dans `app/config/testing.py`, mais
`CSRFProtect` n'était **instancié nulle part** dans `app/__init__.py`, et
**aucun des 19 templates avec formulaire POST** n'avait de champ
`csrf_token`. Le flag de config était entièrement décoratif : en
production comme en dev, toutes les routes POST (login, ajout/suppression
de shifts, gestion admin des utilisateurs/groupes, etc.) étaient
exploitables par CSRF.

Décision utilisateur validée : correction complète dans cette même
session (pas juste documentée), vu l'ampleur de l'impact en prod :
- `csrf = CSRFProtect()` + `csrf.init_app(app)` dans `app/__init__.py`
  (même pattern que `db`/`login_manager`/`limiter`)
- `<meta name="csrf-token" content="{{ csrf_token() }}">` ajouté à
  `base.html` pour que le JS puisse le lire
- Champ caché `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`
  ajouté juste après la balise `<form method="POST">` dans les 19
  templates concernés (22 formulaires au total - `schedule.html` et
  `oncall.html` en ont plusieurs)
- Les 5 appels `fetch()` avec méthode d'écriture (PATCH/POST/DELETE) dans
  `index.html` (drag & drop FullCalendar, création/suppression de shift
  via modale) envoient maintenant l'en-tête `X-CSRFToken` lu depuis la
  balise meta

**Vérifié en conditions réelles**, pas seulement via les tests :
serveur Flask avec `app.config.Config` (config de type prod, pas
TestingConfig) et `WTF_CSRF_ENABLED` à sa valeur par défaut (True,
puisque non surchargée hors TestingConfig) :
- POST `/login` sans jeton → 400 (rejeté)
- GET `/login` puis POST avec le jeton extrait du HTML → 302 (connecté),
  cookie de session valide, `/dashboard` accessible ensuite
- POST `/api/shifts` avec en-tête `X-CSRFToken` manquant → 400 ; avec
  l'en-tête correct (celui rendu dans la balise meta) → 200, shift bien
  créé

`tests/integration/test_security.py` (13 tests) : construit sa propre
instance d'app avec Talisman ET CSRF réactivés (`TestingConfig` les
désactive tous les deux pour simplifier les autres suites) pour tester
ces deux protections spécifiquement, plus les headers de sécurité
Talisman, le stockage des mots de passe (hashé, jamais en clair), et le
contrôle d'accès admin/non-admin (dashboard admin, liste utilisateurs,
ajout de shift, suppression de shift - tous 302/403 pour un non-admin ou
un anonyme).

641 tests passent.

---

*Dernière mise à jour : 2026-07-11*
