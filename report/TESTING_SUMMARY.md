# TESTING_SUMMARY.md - Stratégie de Tests Leviia Schedule

## 📊 Aperçu Global

- **Date de mise à jour** : 17 juillet 2026 (stabilisation v1.0, PR #122-#127)
- **Nombre total de tests** : 1314
- **Tests réussis** : 1314 ✅
- **Tests échoués** : 0
- **Couverture de code** : **~92%** (`--cov=app`)
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
├── unit/                            # 662 tests - composants isolés, pas de HTTP
│   ├── test_service_account_model.py     # ServiceAccount : jeton/hash SHA-256, is_valid()
│   ├── test_service_account_repository.py
│   ├── test_service_account_service.py   # create/revoke/regenerate + audit trail
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
│   ├── test_config.py               # DATABASE_URL, normalize_database_uri() (MySQL/PostgreSQL
│   │                                 #   driver rewrite), get_database_type(), SQLALCHEMY_ENGINE_OPTIONS
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
│   ├── test_backup_service.py       # BackupService (couche support /admin/backups)
│   └── test_settings_service.py     # SettingsService (fuseau horaire, langue, formats date/heure...)
│
├── integration/                     # 615 tests - routes Flask, client de test
│   ├── test_routes.py, test_*_priority.py, test_*_coverage.py
│   ├── test_admin_*.py              # Routes admin (users/groups/shift-types/automation/backups,
│   │                                 #   service accounts)
│   ├── test_service_account_auth.py # resolve_service_account() : header manquant/invalide/expiré/révoqué
│   ├── test_api_v1_routes.py        # Endpoints /api/v1/* (shifts/oncall/leave/users/shift-types)
│   ├── test_api_csrf_exemption.py   # Blueprints app/api/ exemptés de CSRFProtect
│   └── test_openapi_spec.py         # /api/v1/openapi.json généré, pas d'UI Swagger servie
│   ├── test_security.py             # CSP, CSRF, Talisman, contrôle d'accès
│   ├── test_oidc_routes.py          # /login, /oidc/login, /oidc/callback, /logout (13 tests)
│   ├── test_performance.py          # Temps de réponse, N+1, compression
│   ├── test_i18n.py                 # get_locale(), <html lang>, catalogue en.po (round-trip)
│   ├── test_prometheus_metrics.py, test_health.py
│   ├── test_dark_theme.py, test_theme_fixes.py
│   └── test_error_handlers.py
│
└── e2e/                             # 32 tests
    ├── test_user_flows.py           # 6 tests, client de test Flask
    ├── conftest.py                  # live_server_url, oidc_live_servers (Playwright)
    ├── test_browser_flows.py        # 20 tests, Chromium réel (optionnel) - dont la création
    │                                 #   d'un compte de service (jeton affiché une fois)
    ├── oidc_mock_provider.py        # Faux fournisseur OIDC réel (Flask, pas Docker)
    └── test_oidc_browser_flow.py    # 6 tests, flux SSO complet en navigateur réel (optionnel)
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
6 passent + 2 skippés (au lieu de 24 passent).

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
7. **Ne jamais imbriquer `with test_app.app_context():` quand un test
   mute puis re-vérifie un objet de fixture via une requête fraîche** :
   `test_app` a déjà un contexte actif pour toute la durée du test (voir
   `tests/conftest.py`). En pousser un second fait résoudre `db.session`
   vers une **session SQLAlchemy différente** de celle utilisée par les
   fixtures - confirmé via l'erreur SQLAlchemy elle-même : `"Object ...
   is already attached to session 'N' (this is 'M')"`. Un objet créé par
   une fixture (attaché à la session N) mute normalement en mémoire dans
   le bloc imbriqué (session M), mais `db.session.commit()` dans ce bloc
   ne committe RIEN pour cet objet - il reste invisible même en SQL brut
   après coup. Inoffensif tant qu'un test ne vérifie que l'attribut
   Python en mémoire (`objet.champ == valeur`, la quasi-totalité des
   tests de ce fichier) ; silencieusement faux dès qu'on vérifie l'état
   réellement persisté (`Model.query.count()` après un bulk `.delete()`,
   par exemple - voir `TestPurgeSwaps` dans `test_swap_service.py`, où
   ça a fait échouer un test de façon 100% reproductible malgré un code
   applicatif correct). Un objet **créé** à l'intérieur du bloc imbriqué
   (pas depuis une fixture) n'est pas concerné, puisqu'il est ajouté
   directement à la session M. L'app réelle n'est jamais affectée : une
   requête HTTP a un unique contexte, jamais imbriqué.

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
- **14 juillet 2026** : 994 tests (0 échec, +19). Notifications internes
  à l'app (bell icon sidebar, badge non-lu) : `AppNotification` -
  distinct de `NotificationLog` qui reste réservé aux rappels email
  hebdo et n'est jamais affiché. `AppNotificationService` déclenché
  synchroniquement par `SwapService` (nouvelle demande -> tous les
  admins ; approbation/annulation -> demandeur + destinataire ; rejet ->
  demandeur seul). Bug réel trouvé et corrigé *avant* qu'il ne casse la
  prod : le nouveau `context_processor` (badge non-lu) accédait à
  `current_user.is_authenticated` sans vérifier `has_request_context()`
  - `NotificationService` (emails hebdo) rend ses templates via un
  simple `app_context()` (scripts cron, jamais de requête HTTP), où
  `current_user` résout à `None` plutôt que de lever une exception ;
  résultat : `'NoneType' object has no attribute 'is_authenticated'` sur
  **chaque** email de rappel, silencieusement avalé dans
  `NotificationBatchResult.failed`. Détecté par la suite existante
  (`tests/unit/test_notification_service.py`, 5 tests rouges) en
  relançant la suite complète après la feature - pas par un test écrit
  pour ce bug précis. Rappel qu'un `context_processor` s'exécute pour
  *tout* rendu de template de l'app, y compris hors requête HTTP.
- **14 juillet 2026** : 1006 tests (0 échec, +12). Corrections retours
  utilisateur sur l'échange de shifts + notifications : badge de statut
  `REVERTED` simplifié en "Annulée" (au lieu de "Annulée après
  approbation") côté page utilisateur ; flash "Échange rejeté." passé de
  `success` (vert) à `warning` (orange), un rejet n'étant pas un succès
  côté demandeur. Purge ajoutée des deux côtés : notifications lues
  (`AppNotificationService.purge_read`, garde les non-lues) et demandes
  d'échange terminées/non-pending (`SwapService.purge_resolved_for_user`
  côté utilisateur - matché comme demandeur *ou* destinataire, donc peut
  faire disparaître une ligne encore visible pour l'autre partie, un seul
  enregistrement historique partagé ; `purge_all_resolved` côté admin,
  tous utilisateurs). Découverte majeure au passage, documentée en detail
  dans "Bonnes pratiques" ci-dessous (point 7) : imbriquer
  `with test_app.app_context():` dans un test dont `test_app` a déjà un
  contexte actif fait résoudre `db.session` vers une session SQLAlchemy
  différente de celle des fixtures - un commit dans le bloc imbriqué ne
  persiste alors rien pour un objet de fixture, silencieusement, tant
  qu'on ne vérifie pas l'état via une requête fraîche. A fait échouer un
  nouveau test de purge de façon 100% reproductible en isolation malgré
  un code applicatif correct (confirmé via les tests de routes HTTP
  équivalents, eux non affectés) - probablement latent et invisible dans
  le reste de la suite jusqu'ici car la quasi-totalité des tests
  existants ne vérifient que l'attribut Python en mémoire après une
  action, jamais un état fraîchement requêté.
- **16 juillet 2026** : 1099 tests (0 échec, +93). Deux features livrées
  (PR #115 puis #116, même architecture Setting/User réutilisée pour
  chacune) :
  - **i18n Français/Anglais** (Flask-Babel) : `User.language` +
    `SettingsService.default_language`, retrofit complet de tout le texte
    utilisateur (55 templates, tous les `flash()`, erreurs de services, JS
    codé en dur via un mécanisme JSON server→JS car pas de build step,
    4 templates email rendus dans la langue de chaque destinataire via
    `force_locale()`), catalogue `en.po` traduit intégralement (806
    chaînes), `fr.po` gardé à `msgstr` vides à dessein (repli standard sur
    le français, comportement inchangé pour la suite existante).
    Nouveau `tests/integration/test_i18n.py`, dont un test round-trip
    dédié (`TestEnCatalogTranslation`) qui rend une page avec
    `default_language="en"` et vérifie que l'anglais apparaît vraiment -
    attrape à la fois "chaîne jamais traduite" et "catalogue jamais
    compilé". Nouvelle fixture pytest session-scope autouse
    (`tests/conftest.py::_compile_babel_catalogs`) : sans elle un
    checkout frais n'a pas de `.mo` (gitignorés, artefacts de build) et
    gettext retombe silencieusement sur le français même en anglais.
  - **Formats de date/heure configurables** : même pattern
    (`User.date_format`/`time_format` + `SettingsService.default_date_format`/
    `default_time_format`), 3 formats de date / 2 formats d'heure,
    retrofit des `strftime()` d'affichage vers 3 nouveaux filtres Jinja
    (`format_date`/`format_time`/`format_datetime`). Bug réel trouvé et
    corrigé en cours de route : régression N+1
    (`test_schedule_query_count_stable_across_dataset_size`, déjà présent
    dans la suite avant cette session) - les nouveaux résolveurs de
    format n'avaient pas le cache par requête dont bénéficie `get_locale()`
    via `flask_babel` en interne, donc chaque cellule date/heure d'un
    tableau déclenchait sa propre requête `Setting.get()` ; fix par cache
    sur `flask.g`.
  - Après coup, en relançant la suite complète : 2 tests trouvés cassés
    depuis la scission `/profile/update` → `/profile/settings` (session
    antérieure, migration timezone) - `TestApiCreateShiftTimezoneConversion`
    et `TestApiUpdateOncall::test_update_converts_viewer_tz_to_org_tz_for_storage`
    postaient encore `timezone` vers `/profile/update`, une route qui ne
    lit que nom/email/mot de passe ; le POST était silencieusement ignoré
    et aucune conversion de fuseau horaire n'avait lieu. Longtemps
    mal-diagnostiqués en cours de session comme "bug DST préexistant" avant
    lecture attentive du code des deux routes - corrigés en pointant vers
    `/profile/settings`.
- **16 juillet 2026** : 1133 tests (0 échec, +34). Audit trail (PR #117) :
  modèle `AuditLog` (append-only) + `AuditLogRepository` + `AuditService.log()`
  comme point d'écriture unique, double écriture DB + `logs/audit.log`.
  Avant cette PR, `log_audit_action()` existait dans le code depuis
  longtemps mais n'était appelé nulle part en dehors des tests - confirmé
  par grep sur `app/routes/`/`app/services/`, zéro résultat. Retrofit de
  tout le CRUD métier (utilisateurs, groupes, shifts, astreintes, congés,
  types de shift, tout le cycle de vie des échanges, paramètres admin) et
  des événements d'authentification (connexion réussie/échouée,
  déconnexion, inscription, changement de mot de passe). Tests
  représentatifs par domaine (pas une duplication systématique par
  méthode, le pattern d'appel est identique partout) plus une suite dédiée
  pour `AuditLogRepository`/`AuditService` (résolution d'acteur explicite
  vs `current_user` vs aucun, non-propagation d'exception si l'écriture
  échoue - `test_failure_writing_entry_does_not_raise`) et pour la route
  admin `/admin/audit-log` (filtres, pagination, permission admin-only,
  purge avec/sans rétention configurée). Un test s'est cassé en cours de
  route (`test_resolves_actor_from_current_user_in_request_context`) :
  il comptait *toutes* les lignes `AuditLog` de la table, mais la
  connexion réelle effectuée par le fixture `logged_in_client` écrit
  désormais elle-même une entrée `auth.login_success` - corrigé en
  filtrant sur l'action testée plutôt qu'en comptant la table entière.
- **16 juillet 2026** : 1176 tests (0 échec, +43). Notifications externes
  via Apprise (Slack/Discord/Telegram/webhooks génériques) : nouveau
  modèle `NotificationTarget` (catégories JSON encodées, `subscribes_to()`
  avec la règle "liste vide = toutes catégories") + `AppriseNotificationService`,
  deux points d'entrée testés séparément - `notify()` (fire-and-forget,
  jamais d'exception propagée même si le repository échoue, une cible en
  échec n'empêche pas les autres d'être notifiées) et `send_test()`
  (retourne le vrai succès/échec pour le bouton "Tester" de l'admin).
  `apprise.Apprise` parle réseau, donc entièrement mocké
  (`unittest.mock.patch` sur le point d'import du service) - aucun appel
  réseau réel dans la suite. Tests représentatifs pour chaque site
  d'appel retrofit (`SwapService.request_swap()` déclenche bien
  `notify("swap", ...)`, mocké) plutôt qu'une duplication par méthode.
  Suite complète pour `/admin/notification-targets` : CRUD, permission
  admin-only, toggle global, action de test avec succès/échec mockés.
- **16 juillet 2026** : 1183 tests (0 échec, +7). Ajout de deux
  catégories Apprise dédiées (`shift_weekly`/`oncall_weekly`) qui
  relaient chaque envoi hebdomadaire réussi (pas seulement les échecs
  comme la catégorie `system`), avec un opt-out par utilisateur
  indépendant de celui des emails (`User.apprise_shift_notifications_enabled`/
  `apprise_oncall_notifications_enabled`, nouvelle migration), visible
  et modifiable dans `/profile/settings` dans sa propre section (même
  garde "n'applique les cases cochées que si la section était visible"
  que pour la section email). Tests : relais déclenché sur succès,
  relais absent si le toggle utilisateur est désactivé (`NotificationService`),
  section masquée/visible selon le toggle global, persistance/ignorance
  des cases selon le toggle global (`/profile/settings`).
- **16 juillet 2026** : 1193 tests (0 échec, +10). Retour utilisateur :
  le simple booléen `apprise_shift_notifications_enabled`/
  `apprise_oncall_notifications_enabled` remplacé par une vraie
  sélection de cibles (`User.apprise_shift_target_ids`/
  `apprise_oncall_target_ids`, liste JSON encodée d'ids `NotificationTarget`,
  même migration modifiée en place car pas encore mergée). Nouvelle
  méthode `AppriseNotificationService.notify_to_targets(target_ids, ...)`
  (fire-and-forget, resout chaque id à l'envoi et ignore silencieusement
  une cible supprimée/désactivée depuis la sélection). `/profile/settings`
  n'affiche et n'accepte que les cibles activées ET abonnées à la
  catégorie correspondante (`NotificationTargetRepository.list_enabled_for_category`)
  - un id soumis hors de cette liste éligible est silencieusement
  ignoré (testé explicitement). Lien de documentation Apprise pointé
  vers appriseit.com/services.
- **16 juillet 2026** : 1224 tests (0 échec, +31). Trois chantiers
  indépendants sur une même branche :
  - **Sécurité** : la boucle `nav_links` de `base.html` (Accueil/
    Tableau de bord/Shifts/Astreintes/Congés/Échanges) était la seule
    section de la sidebar sans garde `current_user.is_authenticated`
    - corrige d'un coup `/login` et toutes les pages d'erreur 400-504
    (même layout partagé). Fuite d'information (structure interne de
    l'app), pas un bypass fonctionnel (toutes les routes ciblées
    restent `@login_required`).
  - **Workflow d'échange de shifts en 2 temps** : nouvel état
    `AWAITING_ADMIN` entre la demande (`PENDING`) et la validation
    admin - le destinataire choisit désormais lui-même son shift à
    échanger (ou aucun) au moment de confirmer, ou refuse directement,
    avant même qu'un admin ne voie la demande. Aucune migration
    nécessaire (`status` reste un `String(20)` libre,
    `target_shift_id` déjà nullable). Retrofit complet des tests
    existants (nouvelle fixture `confirmed_swap_request` pour les tests
    d'approbation/rejet/annulation admin, qui ne partent plus
    directement de `PENDING`) + nouveaux tests `TestConfirmSwap`/
    `TestTargetRejectSwap`. `/api/swaps/target-shifts` et
    `swap-form.js` devenus morts (le demandeur ne choisit plus le
    shift retour) - supprimés, ainsi que `app/static/js/utils/date.js`
    (plus aucun appelant réel une fois `swap-form.js` retiré).
  - **Makefile** : 39 cibles réduites à 15 (suppression du bloc
    `bug-hunt`/`scripts/bug_hunt.sh`, confirmé jamais exécuté dans ce
    repo - `reports/` n'existait pas - et déjà divergent de la vraie
    config `ruff`/`.ruff.toml` ; fusion des variantes `test-*`/
    `backup-*` redondantes en invocations directes documentées).
    `find-duplicates` gardé seul, unique apport réel de l'ancien bloc
    bug-hunt.
- **17 juillet 2026** : 1314 tests (0 échec). Stabilisation v1.0 (PR
  #122-#127, 6 PR thématiques) : hygiène Docker/dépendances, code mort
  (`config.py`/`ProductionConfig`/`DevelopmentConfig`/`get_database_type()`),
  optimisation SQL (N+1 Apprise, bulk delete, `joinedload` manquant),
  audit sécurité complet + chasse aux bugs ciblée + CI bloquante, i18n
  (chaînes JS + placeholders + 206 chaînes `en.po` en retard rattrapées),
  test de charge. Deux tests de régression ajoutés pour deux bugs réels
  trouvés *pendant le test de charge* : `run.py` forçait `debug=True` sur
  le serveur de développement Flask quel que soit `FLASK_DEBUG` (risque
  RCE via le débogueur Werkzeug), et Flask-Talisman force
  `SESSION_COOKIE_SECURE=True` indépendamment de `TALISMAN_FORCE_HTTPS`
  (cassait la connexion sur tout déploiement HTTP simple, le mode par
  défaut documenté) - les deux étaient couplés et corrigés ensemble. Voir
  `report/SECURITY_AUDIT_v1.0.md`, `report/BUG_HUNT_v1.0.md`,
  `report/LOAD_TEST_v1.0.md` pour le détail complet.
