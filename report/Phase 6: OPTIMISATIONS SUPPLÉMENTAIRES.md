# 📋 Rapport de Refactorisation - Phase 6: Optimisations Supplémentaires
**Branche** : `refacto/phase6`
**PR** : [#102](https://github.com/FoxOps/leviia-schedule/pull/102)
**Date de début** : 2026-07-12
**Statut** : 🟢 Prêt pour revue
**Base** : `main` (inclut Phases 1 à 5, PR #101 mergée)

---

## 📈 État des lieux

Audit en cours de l'état réel de chaque sous-point avant de coder quoi
que ce soit — plusieurs phases précédentes ont montré que la doc/le plan
d'origine décrit parfois des choses déjà faites, déjà mortes, ou
inapplicables sans un changement d'outillage majeur (bundler JS,
infra Kubernetes réelle, etc.). Détail à suivre dans le Journal.

---

## 🎯 Plan de travail

### 6.1 Performance
- [x] Lazy loading des images — non applicable, voir Journal
- [ ] Code splitting JS — documenté, reporté (pas de bundler)
- [ ] Tree shaking CSS/JS — documenté, reporté (pas de bundler)
- [x] Compression Gzip/Brotli

### 6.2 Sécurité
- [x] CSP (Content Security Policy)
- [x] Security headers
- [x] Audit régulier des dépendances — bandit/safety déjà en CI, cadence documentée

### 6.3 DevOps
- [x] CI/CD amélioré (GitLab, futur dépôt)
- [x] Docker optimisé
- [x] Kubernetes ready
- [x] Monitoring (Prometheus, Grafana)

---

## 📝 Journal

### CSP + security headers toujours actifs (commit `6764d19`)

**Bug réel trouvé et corrigé** : dans `app/__init__.py`, Talisman n'était
initialisé que si `TALISMAN_FORCE_HTTPS` était vrai. Or ce flag ne devrait
contrôler que la redirection HTTP->HTTPS et HSTS, pas les autres en-têtes
(CSP, X-Content-Type-Options, X-Frame-Options...). Conséquence concrète :
`docker/docker-compose.yml` met `TALISMAN_FORCE_HTTPS=false` (pas de TLS
terminé dans le conteneur, un reverse proxy s'en charge) — ce déploiement
n'avait donc **aucun** en-tête de sécurité du tout. Corrigé : Talisman est
maintenant toujours initialisé sauf en `TESTING`.

**CSP stricte ajoutée** (`CSP_POLICY` dans `app/__init__.py`) :
`script-src 'self'` (bloque tout `<script>` injecté), `object-src 'none'`,
`style-src 'self' 'unsafe-inline'` (un seul style dynamique dans
`dashboard.html`, largeur de barre de graphique), `script-src-attr
'unsafe-inline'` (21 attributs `onclick=""` restants dans les templates —
contenu statique écrit par les développeurs, jamais de données
utilisateur ; `script-src-attr` est une directive CSP niveau 3 distincte
de `script-src`, les nonces ne couvrent pas les attributs d'événements).

Pour permettre `script-src 'self'` sans `unsafe-inline` ni nonce, le
script inline de ~576 lignes de `index.html` (config FullCalendar : drag
& drop, création de shift via modal, etc.) a été externalisé vers
`app/static/js/calendar/fullcalendar-config.js` (module ES6). Les données
serveur (liste d'événements, `is_admin`, token CSRF) passent maintenant
par des attributs `data-*` et un bloc `<script type="application/json">`
plutôt que par de l'interpolation Jinja dans du JS inline.

4 tests de régression ajoutés dans `tests/integration/test_security.py`
(gating même sans `TALISMAN_FORCE_HTTPS`, contenu exact de la CSP, absence
de script inline exécutable sur `/`). 771 tests passent.

### Compression Gzip/Brotli (flask-compress)

**Bug réel trouvé et corrigé** : `flask-compress==1.24` est une
dépendance déclarée avec sa config (`COMPRESS_REGISTER`,
`COMPRESS_MIMETYPES`) dans `app/config/production.py`, mais `Compress`
n'était importé ni instancié nulle part dans `app/__init__.py`. La
compression ne faisait donc **rien** en pratique, peu importe
l'environnement — la config existait mais l'extension n'avait jamais été
branchée à l'application.

Corrigé : instance `compress = Compress()` au niveau module (même
pattern que `db`/`login_manager`/`csrf`), `compress.init_app(app)` appelé
dans `create_app()`, désactivé en `TESTING` (le client de test ne décode
pas `Content-Encoding`, casserait les assertions texte sur `resp.data`
dans le reste de la suite).

Vérifié sur un serveur réel (`curl -H "Accept-Encoding: gzip" ...`) :
`/login` → `Content-Encoding: gzip`, taille réduite. Les fichiers
statiques servis en streaming (`fullcalendar-config.js`, 27 Ko) utilisent
br/zstd plutôt que gzip (comportement par défaut de flask-compress pour
les réponses streamées — gzip est exclu de `COMPRESS_ALGORITHM_STREAMING`
en amont) : 27 166 → 5 099 octets en br, 5 407 en zstd.

2 tests de régression ajoutés dans `tests/integration/test_performance.py`
(`TestCompression`) : réponse compressée si `Accept-Encoding: gzip`,
non compressée sinon.

### Lazy loading des images — non applicable

Audit (`find app/static/images app/templates -iname "*.png" -o ...`) :
la seule image du projet est `app/static/images/favicon.png`. Aucune
image de contenu à lazy-loader. Rien à faire.

### Code splitting / tree shaking JS — documenté, reporté

Aucun bundler dans le projet (`package.json`, `webpack.config.js`,
`vite.config.js`, `rollup.config.js` : tous absents). Le JS est servi tel
quel en fichiers statiques (vanilla ES6 modules, vendor libs en local).
Introduire un bundler (Vite/esbuild/Rollup) pour permettre code
splitting + tree shaking serait un changement d'outillage majeur (build
step, config, CI à adapter) hors du périmètre "optimisations" de cette
phase — décision utilisateur : documenter et reporter plutôt
qu'introduire un bundler dans cette phase.

### Audit régulier des dépendances

`bandit` et `safety` tournaient déjà (job `run_security` en CI, cible
`make security` en local) mais uniquement sur push/MR — jamais de cadence
indépendante des commits (une dépendance peut devenir vulnérable sans
qu'aucun code ne change). Un pipeline GitLab planifié (CI/CD > Schedules,
propriété du projet GitLab, pas configurable depuis le YAML du repo) est
la façon standard de couvrir ça ; commentaire ajouté dans
`.gitlab-ci.yml` documentant comment le brancher (`$CI_PIPELINE_SOURCE ==
"schedule"`) une fois le dépôt GitLab en place.

### CI/CD (.gitlab-ci.yml) — commit `4ce3c5c`

- `.python-template` installait les dépendances deux fois : une fois
  avant `python -m venv .venv` (dans le python système du conteneur,
  perdu ensuite), une fois après. Réordonné pour n'installer qu'une fois,
  dans le venv.
- `run_tests` déclarait `artifacts.reports.junit: junit.xml` et une regex
  de coverage (`coverage: '/^TOTAL...'`) sans jamais passer `--junitxml`
  ni `--cov` à pytest — les deux étaient cassés depuis toujours (aucun
  fichier généré, aucune ligne à matcher). Corrigé.
- `deploy_swarm` déployait via `docker stack deploy -c
  docker-compose.prod.yml`, fichier introuvable n'importe où dans le
  repo (confirmé par recherche exhaustive) — job mort. Supprimé (k8s via
  `deploy_production` est le vrai chemin de déploiement).
- `deploy_production` : `kubectl rollout status ... -n production` visait
  un namespace qui n'existe dans aucun manifest `k8s/` (tous déclarent
  `namespace: leviia-schedule`) — aurait échoué en "not found". Corrigé.
  Le job ne déployait de toute façon jamais l'image tout juste construite
  par `build_docker` : `k8s/deployment.yaml` a un placeholder
  `your-registry/leviia-schedule:latest` en dur. Ajout d'un `sed` pour le
  remplacer par `$CI_REGISTRY_IMAGE:latest` avant `kubectl apply`.

### Docker optimisé — commit `4ce3c5c`

`docker/Dockerfile.optimized` (multi-stage, créé en Phase 1 mais jamais
branché nulle part — ni CI, ni docker-compose.yml, ni Makefile) a été
construit et lancé localement pour validation (`docker build` +
`docker run` + `curl /health`), comme point de départ avant de le
promouvoir. Premier essai : `ModuleNotFoundError: No module named
'flask'` au démarrage malgré une image qui build sans erreur — bug réel :
`pip install --user` dans le stage builder installe dans
`/root/.local`, qui hérite du mode `700` de `/root` dans l'image de
base ; une fois `USER appuser` (non-root) actif, ce répertoire est
illisible, `--chown` sur le seul contenu copié ne change rien puisque
c'est `/root` lui-même qui bloque la traversée. Corrigé en installant
avec `pip install --prefix=/install` puis en copiant vers `/usr/local`
(déjà dans le `sys.path` par défaut de l'image `python:3.11-alpine`,
déjà `755`). Re-testé avec succès : `/health` répond `200`, `docker exec
whoami` renvoie `appuser`, mode développement (`python run.py`) et
production (`FLASK_ENV=production` → Gunicorn) vérifiés tous les deux.

Taille comparée avec `docker images` : 415 Mo (optimisé, multi-stage)
contre 926 Mo (ancien Dockerfile, mono-stage) — un peu plus de 2x plus
léger. `docker/Dockerfile.optimized` a remplacé `docker/Dockerfile`
(promotion suivant le plan déjà écrit dans
`report/DOCKER_OPTIMIZED_TEST.md` §"Prochaines étapes"), l'ancien
fichier supprimé pour éviter la dérive entre deux Dockerfiles.
`FLASK_ENV` par défaut remis à `development` dans l'image (l'optimisé
avait `production` par défaut, ce qui aurait fait tourner Gunicorn par
défaut dans le stack `docker-compose.yml` de dev, qui ne définit pas
`FLASK_ENV`).

Bugs annexes trouvés et corrigés dans la foulée :
- `docker-compose.yml` n'avait aucune clé `build:` — `docker compose
  build` ne pouvait rien construire. Ajoutée (`context: ..`, `dockerfile:
  docker/Dockerfile`), vérifiée avec un vrai `docker compose build`.
- `docker/Makefile` : `up-prod` utilisait `up -d -e FLASK_ENV=production`
  — `-e` n'est pas un flag valide pour `docker compose up` (c'est un flag
  de `docker run`). Corrigé en `FLASK_ENV=production docker compose ...
  up -d`, et ajout de `FLASK_ENV=${FLASK_ENV:-development}` dans
  `docker-compose.yml` pour que la variable d'environnement shell
  atteigne réellement le conteneur.
- `docker/Makefile` : `shell` ciblait `exec web sh`, un service qui
  n'existe pas dans `docker-compose.yml` (le service s'appelle
  `leviia-schedule`). Corrigé.
- `docker/setup-env.sh` cherchait `.env.example` dans le répertoire
  courant, alors que ce fichier est à la racine du repo et que le script
  vit dans `docker/` — cassé quel que soit le répertoire depuis lequel il
  était lancé (personne ne l'appelle nulle part actuellement, script
  orphelin, mais autant le corriger). `cd` vers son propre répertoire en
  entrée de script + référence `../.env.example`.

Non touché : l'IP codée en dur (`192.168.1.169`) dans la config OIDC mock
de `docker-compose.yml`. C'est un contournement délibéré d'un problème
déjà réglé par un commit dédié de cette branche de travail
(accessibilité de l'issuer OIDC à la fois depuis le conteneur et le
navigateur hôte) — le retoucher risquerait de réintroduire ce bug-là,
hors du périmètre de cette phase.

### Kubernetes ready — commit `4ce3c5c`

`k8s/deployment.yaml` avait des annotations `checksum/config` /
`checksum/secret` en syntaxe Helm (`{{ include (print ...) | sha256sum
}}`) sur un manifest appliqué tel quel via `kubectl apply -f k8s/` (pas
de Helm dans ce projet, confirmé par recherche `find` — aucun `Chart.yaml`
nulle part) : cette syntaxe n'était jamais interprétée, restait du texte
littéral dans l'annotation. Le but (forcer un rolling restart des pods
quand la ConfigMap ou le Secret change) ne s'est donc jamais produit.
Annotations mortes supprimées, alternative documentée en commentaire
(`kubectl rollout restart` explicite).

Les manifests eux-mêmes (probes `/health`/`/ready`, Service, Ingress,
ConfigMap, Secret template, PVC, HPA, PDB, Namespace) existaient déjà et
sont corrects (probes déjà vérifiées en Phase 4). Validation YAML de
tous les fichiers `k8s/*.yaml` faite avec `yaml.safe_load_all` (pas de
`kubectl` disponible dans cet environnement pour un `--dry-run=client`
réel).

### Monitoring — Grafana — commit `4ce3c5c`

Aucun artefact Grafana n'existait dans le repo (`find` exhaustif, zéro
résultat). Créé `grafana/leviia-schedule-dashboard.json` (importable
tel quel, datasource Prometheus paramétrable via variable de template) :
requêtes/s et erreurs/s par endpoint, latence p95, temps requêtes SQL
p95, utilisateurs/sessions actifs, volumétrie métier (shifts/astreintes/
congés/utilisateurs/groupes), CPU/mémoire/disque. Chaque nom de métrique
utilisé dans le dashboard vérifié un par un contre
`app/utils/prometheus_metrics.py` (grep croisé des deux listes). JSON
validé syntaxiquement. Dashboard **non** testé contre une instance
Grafana réelle — aucune disponible dans cet environnement, indiqué
explicitement dans `grafana/README.md`.

---

*Dernière mise à jour : 2026-07-12 — Phase 6 complète : 6.1 Performance,
6.2 Sécurité, 6.3 DevOps tous traités. Reste : revue finale avant merge.*
