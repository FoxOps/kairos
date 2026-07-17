# Audit de sécurité v1.0

> Réalisé dans le cadre de la stabilisation v1.0 (voir le plan en 6 PR
> thématiques). Périmètre : configuration HTTP/session, authentification,
> gestion des secrets, injection SQL, analyse statique (Bandit), scan de
> dépendances (Safety), CI/CD. Ne remplace pas un pentest ou un audit tiers
> — c'est une revue de code + configuration, avec vérification directe
> (exécution réelle des scanners, pas seulement lecture du code).

## Résumé

Aucune vulnérabilité critique ou haute trouvée dans le code applicatif
(`app/`). Deux vraies faiblesses corrigées pendant cet audit (voir
"Corrections apportées"). Le reste de ce document est principalement une
**confirmation** de protections déjà en place (CSRF, CSP, hachage des mots
de passe, etc.), avec preuve à l'appui plutôt qu'une supposition.

## Corrections apportées pendant cet audit

### 1. Bandit B105/B107/B104 — faux positifs non annotés côté Bandit

`ruff` (règle `S105`/`S107`, flake8-bandit) et `bandit` détectent des
patterns proches mais utilisent des mécanismes de suppression **différents**
(`# noqa: S105` pour ruff, `# nosec BXXX` pour bandit) — un `# noqa: S105`
existant ne supprime pas l'avertissement bandit équivalent. Trois faux
positifs déjà revus côté ruff n'avaient donc jamais été explicitement
marqués comme acceptés côté bandit :

- `app/services/settings_service.py:38` — `ICS_TOKEN_EXPIRY_DAYS_KEY`, un
  nom de clé `Setting`, pas un secret (B105).
- `app/services/user_service.py:50,71` — paramètre `password: str = ""`
  (valeur par défaut vide, pas un mot de passe en dur) sur
  `UserService.create()`/`update()` (B107 x2).

Ajout de `# nosec BXXX` explicites avec justification en commentaire.
`bandit -r app/` : **0 finding** après correction (3 avant).

### 2. Bandit B104 — bind 0.0.0.0

`app/config/base.py:HOST` — bind sur toutes les interfaces, signalé par
Bandit comme risque potentiel. **Faux positif documenté** : l'app tourne
toujours en conteneur ou derrière un reverse proxy en production —
`127.0.0.1` casserait silencieusement toute exposition. Annoté `# nosec
B104` avec justification (exposition réseau contrôlée par le déploiement,
pas par l'app).

### 3. Bandit B324 — MD5 dans `scripts/find_duplicates.py`

Usage non cryptographique (empreinte de similarité de code, pas un besoin
de sécurité). Corrigé avec `usedforsecurity=False` (le correctif suggéré
par Bandit lui-même) plutôt qu'un changement d'algorithme inutile.

### 4. Bug réel trouvé en creusant B104 : `PROMETHEUS_ENABLED` jamais câblé

Pas une vulnérabilité de sécurité à proprement parler, mais documenté ici
car trouvé pendant cette passe et corrigé dans la même PR : `app/__init__.py`
teste `app.config.get("PROMETHEUS_ENABLED", False)`, mais cette clé n'était
**jamais lue depuis l'environnement** dans `app/config/base.py::Config` —
la fonctionnalité `/metrics` était donc structurellement inatteignable en
déploiement réel, quel que soit l'env var positionné, masqué par un test
qui forçait `app.config["PROMETHEUS_ENABLED"] = True` directement au lieu
de passer par le vrai chemin `create_app()`. Voir `report/BUG_HUNT_v1.0.md`
pour le détail complet et la correction (câblage ajouté + suppression des
routes `/health`/`/ready` dupliquées et bugguées dans ce même module, déjà
correctement servies par `app/utils/health.py`).

## Ce qui a été vérifié et confirmé sain

### CSRF

`Flask-WTF CSRFProtect` actif sur toute l'application (`app/__init__.py`).
Seule exemption : les blueprints `app/api/resources/*` (API publique
`/api/v1/*`), exemptés via `csrf.exempt(blp)` — justifié : cette API
n'accepte jamais l'authentification par cookie (bearer token uniquement,
`ServiceAccount`), donc le risque que CSRF protège (requête cross-site
avec cookie de session valide) ne s'applique pas.

### En-têtes de sécurité HTTP (Talisman + CSP)

`Flask-Talisman` actif partout sauf en `TESTING`.
`TALISMAN_FORCE_HTTPS`/`TALISMAN_STRICT_TRANSPORT_SECURITY`
configurables par env, activés par défaut. CSP (`CSP_POLICY`,
`app/__init__.py`) : `default-src 'self'`, `object-src 'none'`, pas de
`'unsafe-inline'` sur `script-src` (seulement sur `script-src-attr`, pour
les attributs `onclick=""` du HTML statique écrit par les développeurs —
jamais de données utilisateur — et sur `style-src`, pour un seul style
dynamique de largeur de barre sur le dashboard). Domaines externes
whitelistés (`cdnjs.cloudflare.com`, `cdn.jsdelivr.net`) documentés et
justifiés un par un dans le code (CDN pour Tailwind/daisyUI/Font
Awesome/FullCalendar — l'app n'a pas de pipeline de build JS/CSS, voir
CLAUDE.md "Frontend").

### Cookies de session

`SESSION_COOKIE_HTTPONLY=True` par défaut, `SESSION_COOKIE_SAMESITE=Lax`,
`SESSION_PROTECTION="strong"` (Flask-Login réinvalide la session si
l'IP/user-agent change). `SESSION_COOKIE_SECURE` est `False` par défaut
dans `Config` (nécessaire pour un premier lancement local sans TLS) mais
`True` par défaut dans `docker/.env.example`
(`TALISMAN_FORCE_HTTPS`/déploiement derrière proxy TLS) — cohérent avec
l'architecture documentée.

### `ProxyFix`

`ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)` — fait confiance à
exactement **un** hop de proxy. Correct pour la topologie documentée (un
seul reverse proxy devant l'app) ; une chaîne de proxies plus longue sans
ajuster ces valeurs laisserait un client usurper son IP dans les logs
d'audit, mais ce n'est pas la topologie de déploiement documentée.

### Mots de passe

`werkzeug.security.generate_password_hash()` (scrypt par défaut).
`User.password_hash` est `String(255)` (élargi cette session, voir
CLAUDE.md — bug réel trouvé et corrigé en construisant le support
MySQL : la valeur par défaut de 128 caractères tronquait silencieusement
un hash scrypt de ~162 caractères sous SQLite, et le rejetait
explicitement sous MySQL/PostgreSQL).

### Jetons d'API (`ServiceAccount`)

`token_hash` en SHA-256 (pas de hash lent type PBKDF2/bcrypt) —
délibéré et documenté : le token a 256 bits d'entropie
(`secrets.token_urlsafe(32)`), contrairement à un mot de passe humain à
faible entropie, donc un hash lent n'ajouterait que de la latence sans
bénéfice de sécurité réel. Le token complet n'est **jamais persisté**
(affiché une seule fois, à la création/régénération — UX identique à un
PAT GitHub).

### Injection SQL

Aucune requête SQL brute construite par concaténation trouvée dans
`app/`. Les deux seuls appels `.execute()` avec du SQL textuel utilisent
`sqlalchemy.text()` correctement (`app/utils/health.py`) — le seul
contre-exemple (`app/utils/prometheus_metrics.py`, chaîne brute sans
`text()`) était du code mort inatteignable, supprimé (voir "Bug réel
trouvé" ci-dessus) plutôt que juste corrigé, puisqu'il dupliquait déjà
une route existante correcte.

### Secrets par défaut

`SECRET_KEY`/`SECURITY_PASSWORD_SALT` : si non définis via env,
générés aléatoirement via `secrets.token_urlsafe()` au démarrage — pas
de valeur statique en dur qui finirait dans un dépôt public. Effet de
bord documenté ailleurs (pas un bug de sécurité) : sans `SECRET_KEY`
fixé explicitement, chaque redémarrage invalide les sessions actives —
c'est pourquoi `docker/.env.example`/`.env.example` documentent
explicitement de générer et fixer une vraie valeur.

### Webhooks Apprise

`NotificationTarget.apprise_url` traité comme un secret : jamais dans
`AuditService` `details`, jamais dans la vue liste (`/admin/notification-targets`,
seulement pré-rempli sur le formulaire d'édition), jamais interpolé dans
un message de log (voir CLAUDE.md "External notifications (Apprise)" pour
le détail — y compris la limite documentée du filtre anti-données-sensibles
des logs sur ce point précis, mitigée par discipline aux points d'appel
plutôt que par une regex qui ne peut pas couvrir toutes les formes d'URL
Apprise).

### Path traversal (sauvegardes)

`BackupService` (téléchargement de backups locaux) : garde
préfixe + containment check sur le chemin résolu avant tout accès
fichier (`app/services/backup_service.py`, voir CLAUDE.md "Database
backups").

### Traçabilité (audit trail)

`AuditService.log()` capture acteur/IP/action/ressource pour les
domaines sensibles (`auth.*`, `user.*`, `setting.*`, etc.) — écriture
DB + fichier, échoue de façon silencieuse et journalisée (jamais
bloquant pour l'action métier qu'il enregistre), avec un test de
régression dédié (`test_failure_writing_entry_does_not_raise`).

## Bandit — état final

```
bandit -r app/     -> 0 finding (3 avant correction)
bandit -r scripts/ -> 0 finding bloquant (findings Low restants : B101
                       assert dans un script, B110 try/except/pass déjà
                       délibéré dans find_duplicates.py — hygiène de script,
                       pas une surface d'attaque)
```

## Safety (scan de dépendances) — non exécuté en CI, gap documenté

`safety check` (l'ancienne commande, utilisée jusqu'ici par
`.gitlab-ci/.gitlab-ci.yml`) est **non supportée depuis mai 2024** — la
CI l'appelait avec une syntaxe déjà invalide pour la version installée
(`safety==3.8.1`). Son remplaçant, `safety scan`, nécessite soit
`safety auth login` (interactif), soit une clé `SAFETY_API_KEY` — confirmé
par test direct : sans clé, `safety scan` bloque indéfiniment en attendant
un prompt de connexion, ce qui **bloquerait tout pipeline CI**
indéfiniment plutôt que d'échouer proprement. La CI (voir
"CI/CD" ci-dessous) exécute maintenant `safety scan` seulement si
`SAFETY_API_KEY` est configurée (CI/CD > Variables), et l'ignore
explicitement sinon (message clair, pas un `|| true` qui masque
silencieusement l'absence de scan).

**Action recommandée, non faite ici** (nécessite un compte
platform.safetycli.com, décision hors du périmètre code) : configurer
`SAFETY_API_KEY` pour activer réellement le scan de dépendances en CI.

## CI/CD — jobs bloquants

`.gitlab-ci/.gitlab-ci.yml` : `run_linting` et `run_security` étaient
tous les deux non-bloquants (`|| true` sur chaque commande), donc une
régression de lint/type-check/format/sécurité ne faisait jamais échouer
le pipeline. Corrigé : `run_linting` (ruff/mypy/black) est maintenant
strictement aligné sur `make lint`/`make format-check` (mêmes commandes
exactes) et bloquant ; `run_security` (`bandit`) est bloquant, `safety`
reste conditionnel pour les raisons ci-dessus.

**Point important non résolu par cette PR** : ce dépôt est hébergé sur
GitHub (`FoxOps/leviia-schedule`), mais `.gitlab-ci/.gitlab-ci.yml` est
une configuration **GitLab CI** — il n'existe **aucun workflow GitHub
Actions** (`.github/workflows/` n'existe pas). Rendre ce fichier
bloquant améliore sa qualité intrinsèque mais n'a, en l'état, **aucun
effet réel sur les pull requests GitHub de ce dépôt** puisqu'aucune CI ne
s'exécute dessus (confirmé : `gh pr checks` ne remonte aucun check sur
les PR de cette série). Décision à prendre par l'équipe : soit ce fichier
sert un mirroring GitLab existant en dehors de ce que ce dépôt Git seul
peut confirmer, soit un vrai workflow GitHub Actions équivalent doit être
ajouté pour qu'un gate de qualité s'applique réellement aux PR de ce
dépôt.

## Verdict

Aucune vulnérabilité applicative critique/haute trouvée. Les protections
structurelles (CSRF, CSP, hachage des mots de passe, jetons API,
protection session, audit trail) sont en place et cohérentes avec leur
documentation. Les deux gaps réels identifiés sont opérationnels, pas
applicatifs : (1) le scan de dépendances (Safety) n'est pas actif faute
de clé API — décision d'équipe, pas un correctif de code — et (2) aucune
CI ne s'exécute réellement sur ce dépôt GitHub. Ni l'un ni l'autre
n'indique une faille dans le code de l'application elle-même.
