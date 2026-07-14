# TESTING_SUMMARY.md - Stratégie de Tests Leviia Schedule

## 📊 Aperçu Global

- **Date de mise à jour** : 14 juillet 2026 (échange de shifts entre utilisateurs + annulation post-approbation)
- **Nombre total de tests** : 975
- **Tests réussis** : 975 ✅
- **Tests échoués** : 0
- **Couverture de code** : **~88%** (`--cov=app --cov=config`)
- **Lint (ruff)** : propre - **0 erreur**
- **Types (mypy)** : propre - **0 erreur**
- **Formatage (black)** : conforme

---

## 🎯 Stratégie de Tests

### Philosophie : quatre couches, pas trois

1. **Tests unitaires** (`tests/unit/`) : composants isolés (modèles, config,
   automatisation, helpers, décorateurs) - pas de client HTTP.
2. **Tests d'intégration** (`tests/integration/`) : routes Flask via le
   client de test (`client`, `logged_in_client`), CSRF/CSP/permissions,
   pas de navigateur réel.
3. **Tests E2E - client de test** (`tests/e2e/test_user_flows.py`) :
   parcours utilisateur complets (login → action → vérification →
   logout), toujours via le client de test Flask.
4. **Tests E2E - navigateur réel** (`tests/e2e/test_browser_flows.py`,
   `test_oidc_browser_flow.py`) : Playwright + Chromium, **optionnel**
   (voir section dédiée plus bas). Existe précisément parce que les
   trois couches précédentes n'exécutent jamais de JS ni n'appliquent
   CSS/CSP - une catégorie de bug entière (3 vrais bugs CSP trouvés en
   PR #103) leur est structurellement invisible.

### Outils utilisés

- **Framework** : `pytest` (+ `pytest-flask`, `pytest-cov`)
- **Fixtures** : `tests/conftest.py` (chaîne `test_app`/`client`/
  `logged_in_client`) + `tests/fixtures/` (modèles : user, group, shift,
  leave, oncall, swap)
- **Navigateur réel (optionnel)** : `pytest-playwright` + Chromium, voir
  `requirements-e2e.txt`
- **CI** : GitLab CI (`.gitlab-ci/.gitlab-ci.yml`) - `run_tests` (client
  de test, bloquant), `run_e2e_browser` (Playwright, `allow_failure:
  true` tant que non éprouvé en CI)

---

## 📁 Structure des tests

```
tests/
├── conftest.py                      # Fixture chain : test_app, client, logged_in_client
├── fixtures/                        # test_user, test_group, test_shift, test_leave, test_oncall...
│
├── unit/                            # 463 tests - composants isolés, pas de HTTP
│   ├── test_models.py               # User, Group, Shift, OnCall, Leave, ShiftType, NotificationLog
│   ├── test_repositories.py         # Couche accès aux données
│   ├── test_services.py             # Couche logique métier
│   ├── test_automation*.py          # Règles métier shifts/astreintes (3 fichiers)
│   ├── test_advanced_shift_automation.py
│   ├── test_shift_rotation_fix.py
│   ├── test_decorators_unit.py
│   ├── test_helpers.py
│   ├── test_ics_export.py
│   ├── test_cache_manager.py
│   ├── test_config.py
│   ├── test_run_functions.py        # setup_database/create_default_data
│   ├── test_vendor_assets.py        # Bulma/FontAwesome/FullCalendar vendorisés
│   ├── test_oidc_config.py          # OIDCConfig (25 tests)
│   ├── test_oidc_auth.py            # OIDCAuthLib, réseau mocké (31 tests)
│   ├── test_user_manager_oidc_sync.py  # Sync utilisateur OIDC (12 tests)
│   ├── test_notification_config.py  # NotificationConfig (SMTP via env vars)
│   ├── test_email_sender.py         # Envoi SMTP bas niveau, mocké
│   ├── test_notification_service.py # Rappels hebdo shifts/astreinte, idempotence
│   ├── test_backup_config.py        # BackupConfig (SMTP/S3 via env vars)
│   ├── test_backup_database.py      # scripts/backup_database.py (indépendant de app/)
│   └── test_backup_service.py       # BackupService (couche support /admin/backups)
│
├── integration/                     # 454 tests - routes Flask, client de test
│   ├── test_routes.py, test_*_priority.py, test_*_coverage.py
│   ├── test_admin_*.py              # Routes admin (users/groups/shift-types/automation/backups)
│   ├── test_security.py             # CSP, CSRF, Talisman, contrôle d'accès
│   ├── test_oidc_routes.py          # /login, /oidc/login, /oidc/callback, /logout (13 tests)
│   ├── test_performance.py          # Temps de réponse, N+1, compression
│   ├── test_prometheus_metrics.py, test_health.py
│   ├── test_dark_theme.py, test_theme_fixes.py
│   └── test_error_handlers.py
│
└── e2e/                             # 27 tests
    ├── test_user_flows.py           # 6 tests, client de test Flask
    ├── conftest.py                  # live_server_url, oidc_live_servers (Playwright)
    ├── test_browser_flows.py        # 16 tests, Chromium réel (optionnel)
    ├── oidc_mock_provider.py        # Faux fournisseur OIDC réel (Flask, pas Docker)
    └── test_oidc_browser_flow.py    # 5 tests, flux SSO complet en navigateur réel (optionnel)
```

---

## 🧪 Tests E2E navigateur réel (Playwright) - optionnels

**Ne sont PAS installés par défaut** (`requirements.txt` seul suffit à
faire tourner toute l'app et le reste de la suite). Pour les activer :

```bash
pip install -r requirements-e2e.txt
playwright install chromium
```

Sans ça, `pytest tests/` skippe proprement les deux modules concernés
(`pytest.importorskip("playwright")` en tête de fichier) - visible comme
`skipped` dans le résumé, jamais comme échec ni erreur de collecte.
Vérifié explicitement : sans playwright installé, la suite E2E devient
6 passent + 2 skippés (au lieu de 25 passent).

Ce que cette couche vérifie et qu'aucune autre ne peut :
- **Zéro erreur console** sur 8 pages clés (`TestNoConsoleErrors`) -
  généralise en garde-fou permanent l'audit manuel qui a trouvé 3 bugs
  CSP réels lors de la refonte UI/UX (script inline bloqué sur 2 pages,
  police d'icônes FullCalendar bloquée par `font-src` manquant)
- Menu burger mobile (toggle `is-active`/`aria-expanded`, JS pur)
- Thème sombre (persistance `localStorage`, inexistant côté serveur)
- Bouton copier presse-papiers (retour visuel réel)
- **Flux SSO complet** contre un vrai faux fournisseur OIDC
  (`oidc_mock_provider.py`, une vraie appli Flask sur un port séparé,
  pas un mock Python) : redirection navigateur, vraie page de login IdP
  avec un clic, échanges serveur-à-serveur réels (découverte, token,
  userinfo), session établie et invalidée pour de vrai. A permis de
  trouver et corriger un bug réel bloquant (boucle de redirection
  infinie `/login` ↔ `/oidc/login` sur tout échec SSO forcé).

Détail complet : `report/E2E Playwright - Tests navigateur réel.md`.

---

## 🔐 Tests OIDC/SSO

Zéro test existant avant le 13 juillet 2026 malgré ~450 lignes de logique
(`config_oidc.py`, `app/auth/oidc_auth.py`, `app/auth/user_manager.py`).
Trois niveaux, volontairement complémentaires (voir
`report/E2E Playwright - Tests navigateur réel.md` pour la justification) :

1. **Unitaire** (68 tests) : chaque méthode isolée, appels réseau
   (`requests.get/post`) mockés, JWT de test non signé (le code ne
   vérifie jamais de signature, seulement l'expiration).
2. **Intégration** (13 tests) : câblage des routes, `oidc_auth` mocké à
   la frontière du module de routes. **A trouvé un bug réel bloquant** :
   boucle de redirection infinie sur tout échec OIDC quand le SSO est
   forcé (`OIDC_DISABLE_BASIC_AUTH=true`) - corrigé.
3. **E2E navigateur réel** (5 tests) : voir section précédente.

---

## 🔧 Commandes de test

```bash
# Tout (test -> lint -> format -> security)
make all

# Tests seuls
python -m pytest tests/ -v --tb=short         # tout (make test)
python -m pytest tests/unit/ -v               # une couche
python -m pytest tests/test_models.py -v      # un fichier
python -m pytest tests/unit/test_models.py::TestUserModel::test_user_creation -v  # un test

# Couverture
python -m pytest tests/ --cov=app --cov=config --cov-report=term-missing
python -m pytest tests/ --cov=app --cov=config --cov-report=html

# E2E navigateur réel (optionnel, voir section dédiée)
pip install -r requirements-e2e.txt && playwright install chromium
python -m pytest tests/e2e/test_browser_flows.py tests/e2e/test_oidc_browser_flow.py -v

# Qualité de code
ruff check . --config=.ruff.toml
mypy app/ tests/ --ignore-missing-imports --allow-untyped-decorators
black --check . --exclude=".git|__pycache__|instance|venv"

# Sécurité (non bloquant, || true dans le Makefile)
bandit -r app/ tests/
safety scan --full-report   # nécessite un compte Safety CLI (login interactif)
```

---

## 📝 Bonnes pratiques établies dans ce projet

1. **Réutiliser les fixtures existantes** (`test_app`, `client`,
   `logged_in_client`, `test_user`, `test_group`, etc.) plutôt que de
   construire des instances d'app à la main - sauf besoin explicite
   d'une config différente (Talisman/CSRF réactivés, OIDC configuré),
   auquel cas construire un fixture dédié qui `monkeypatch` par-dessus
   `test_app` plutôt que dupliquer `create_app()`.
2. **Nommage clair** : `test_login_route_redirects_to_dashboard()`, pas
   `test_login()`.
3. **Isolation** : `test_app` recrée toutes les tables à chaque test
   (function-scoped). État global (`OIDCConfig`, singletons `oidc_auth`)
   sauvegardé/restauré explicitement quand un test le modifie (voir
   `tests/unit/test_oidc_config.py::clean_oidc_env`,
   `tests/integration/test_oidc_routes.py::oidc_mode`).
4. **Vérifier, ne pas supposer** : un test qui n'a jamais été vu échouer
   n'est pas un garde-fou. Avant de faire confiance à un nouveau test de
   régression, casser volontairement le code qu'il est censé protéger et
   confirmer qu'il échoue avec le bon message (pattern appliqué à
   `TestNoConsoleErrors` : `font-src` retiré temporairement de
   `CSP_POLICY`, test rouge confirmé, remis en place).
5. **Mocker à la bonne frontière** : mocker les appels réseau
   (`requests.get/post`) dans les tests unitaires, mocker les méthodes
   du module appelant (`app.routes.auth.oidc_auth.X`) dans les tests
   d'intégration, ne rien mocker en E2E navigateur (vrai serveur, vrai
   faux fournisseur OIDC).
6. **Un seul client HTTP authentifié par test** : combiner
   `logged_in_client` et `non_admin_client` (ou simplement deux
   `test_app.test_client()`) dans le même test fait finir par partager
   leur cookiejar - un client jamais connecté hérite silencieusement de
   la session du premier login effectué dans le test (artefact du
   harnais de test, pas un bug applicatif). Pour tester une permission
   après une action admin, préparer l'état voulu directement via le
   service (ex: `SwapService.approve_swap(...)` en `app_context()`)
   plutôt que via une seconde requête HTTP authentifiée différemment.

---

## 📈 Historique

- **26 juin 2026** : 522 tests (515 passent, 2 échouent, 7 ignorés),
  couverture ~66%, structure plate (`tests/test_*.py`), pas de CI.
- **13 juillet 2026** : 881 tests (0 échec), couverture ~88%, structure
  en 4 couches (`unit/`/`integration/`/`e2e/` + navigateur réel
  optionnel), CI GitLab, suite OIDC complète, `make all` (test + lint
  ruff/mypy + format black) intégralement propre.
- **13 juillet 2026 (suite)** : 891 tests (0 échec). Amélioration du
  moteur d'automatisation shifts/astreintes (PR #105 : retrait du moteur
  générique mort, dry-run réparé, rééquilibrage atomique, nouvelle règle
  effectif minimum, correctifs confirmations de suppression/astreintes
  en double/rechargement calendrier) puis mise en place des
  notifications par email hebdomadaires (rappels shifts/astreinte,
  `NotificationLog` anti-doublon, SMTP via variables d'environnement,
  scripts cron autonomes).
- **13 juillet 2026 (suite)** : 944 tests (0 échec). Refonte du système
  de sauvegarde (PR #107) : retrait de la scaffolding morte
  (`encrypt`/`encryption_key`/`frequency`), `BACKUP_ENABLED` opt-in
  (`false` par défaut), alertes email de succès/échec réutilisant le
  système de notifications, `BackupService` + interface d'administration
  (`/admin/backups` : liste, création, nettoyage, téléchargement avec
  protection contre la traversée de chemin), intégration Docker (crond
  conditionnel partagé avec les notifications).
- **13 juillet 2026 (suite)** : 931 tests (0 échec). Refonte UI/UX complète
  Bulma → Tailwind CSS 4 + daisyUI 5 via CDN cdnjs (PR #108) : suppression
  du vendoring local (`app/static/vendor/`, `scripts/download_vendor_assets.py`,
  `tests/unit/test_vendor_assets.py`), Font Awesome en mode SVG+JS (les
  `.woff2` cdnjs de la 7.2.0 sont corrompus, rejetés par le sanitizer de
  police de Chromium), FullCalendar maintenu en 6.1.21 via jsDelivr (la
  7.0.0 lève une erreur d'exécution réelle dans son propre code Preact
  compilé, confirmée via trois stratégies CDN différentes - bug amont, pas
  un problème d'hébergement). Baisse nette du nombre de tests par rapport à
  l'entrée précédente : suppression de `test_vendor_assets.py` et des tests
  spécifiques aux variables/classes Bulma désormais obsolètes, compensée
  partiellement par de nouveaux tests de thème (`test_dark_theme.py`
  réécrit). Suite complète (unit + integration + e2e navigateur réel) verte,
  y compris un bug JS réel trouvé en test manuel (pas par la suite
  automatisée) : le bascule de thème plantait après la conversion Font
  Awesome SVG+JS (`querySelector('i')` ne matchait plus), corrigé en ciblant
  par classe (`.fa-moon, .fa-sun`) plutôt que par balise.
- **14 juillet 2026** : 933 tests (0 échec). Refonte visuelle Dracula
  (thème sombre) / Alucard (thème clair) sur la base Tailwind/daisyUI de
  PR #108 (PR #110) : palette 100% issue du spec officiel
  draculatheme.com/spec, menu mobile converti en `drawer` daisyUI natif
  (remplace le toggle `hidden` maison), modale de création de shift
  réécrite en `<dialog>` natif (`showModal()`/`close()`) avec échappement
  HTML ajouté sur les données interpolées, composants daisyUI natifs
  adoptés là où le CSS était bricolé (`stats`, `list`, `avatar`,
  `breadcrumbs`, `tooltip`, `collapse`, `hero`, `swap`). Suite E2E
  navigateur réel mise à jour pour le nouveau mécanisme de menu mobile
  (case à cocher plutôt que classe `hidden`) et enrichie d'un test de
  bascule au clavier ; bug réel trouvé en test manuel (composant
  `avatar-placeholder` de daisyUI qui cible ses styles de centrage sur un
  `<div>` enfant, pas un `<span>` - corrigé).
- **14 juillet 2026** : 975 tests (0 échec, +42). Échange de shifts entre
  utilisateurs (`SwapRequest` : demande, don simple ou réciproque,
  validation/rejet admin) - nouvelle couche modèle/repository/service/
  routes (user + admin) sans précédent d'approbation dans ce repo (les
  congés n'en ont pas, et le restent). Nouveaux tests : modèle
  (`TestSwapRequestModel`), service (`TestRequestSwap`/`TestCancelSwap`/
  `TestApproveSwap`/`TestRejectSwap` - couvre notamment la revalidation
  métier à l'approbation, pas seulement à la création), routes
  utilisateur et admin (`tests/integration/test_swap_routes.py`,
  permissions admin vs non-admin incluses). Complété le même jour par
  `revert_swap` (annulation d'un échange *après* approbation par
  l'admin, statut `REVERTED` distinct de `CANCELLED` qui reste réservé à
  l'auto-annulation par le demandeur avant validation) - `/admin/swaps`
  affiche maintenant aussi les échanges déjà approuvés, pas seulement en
  attente (`TestRevertSwap`, tests routes associés). Piège de test
  découvert au passage : combiner `logged_in_client` et
  `non_admin_client` (ou deux `test_app.test_client()`) dans un même
  test fait finir par partager leur cookiejar - artefact du harnais de
  test, pas un bug applicatif ; toujours isoler un seul client HTTP
  authentifié par test (préparer l'état "déjà approuvé" via le service
  directement si besoin, pas via une seconde requête HTTP admin).
