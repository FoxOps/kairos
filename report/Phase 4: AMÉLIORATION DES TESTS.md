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
- [ ] `unit/test_services.py` + `unit/test_repositories.py` : tests réels
      pour la couche métier créée en Phase 2, actuellement quasi
      intestée directement
- [ ] Augmenter la couverture — objectif réaliste sur le code vivant
      (périmètre exact chiffré une fois le code mort exclu), pas 80%
      brut sur du code mort inclus
- [ ] Tests de performance (temps de réponse routes critiques)
- [ ] Tests de sécurité (headers Talisman, CSRF, injection basique,
      contrôle d'accès admin/non-admin)
- [ ] Tests d'accessibilité — déjà partiellement couverts par
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

---

*Dernière mise à jour : 2026-07-11*
