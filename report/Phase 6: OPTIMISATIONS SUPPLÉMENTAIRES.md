# 📋 Rapport de Refactorisation - Phase 6: Optimisations Supplémentaires
**Branche** : `refacto/phase6`
**PR** : à créer
**Date de début** : 2026-07-12
**Statut** : 🟡 En cours
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
- [ ] Audit régulier des dépendances

### 6.3 DevOps
- [ ] CI/CD amélioré (GitLab, futur dépôt)
- [ ] Docker optimisé
- [ ] Kubernetes ready
- [ ] Monitoring (Prometheus, Grafana)

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

---

*Dernière mise à jour : 2026-07-12 — 6.1 Performance (compression, lazy
loading, code splitting) et 6.2 Sécurité (CSP, headers) traités. Reste :
audit dépendances régulier, 6.3 DevOps.*
