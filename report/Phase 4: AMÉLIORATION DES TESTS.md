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
- [ ] `tests/unit/` : tests sans client HTTP (models, services, repositories,
      automation, config, helpers...)
- [ ] `tests/integration/` : tests passant par le client de test Flask
      (routes, auth, export...)
- [ ] `tests/e2e/` : parcours multi-requêtes (voir décision ci-dessus)
- [ ] `tests/fixtures/` : extraction des fixtures de modèles hors de
      `conftest.py`
- [ ] `Makefile` : mise à jour des chemins (`test-main`, `test-dark-theme`)

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

---

*Dernière mise à jour : 2026-07-11*
