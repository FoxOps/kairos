# Chasse aux bugs v1.0

> Passe ciblée sur les fonctionnalités les plus récentes de l'app (multi-fuseau
> horaire, multi-langue, formats date/heure, audit trail, notifications
> Apprise, workflow d'échange de shifts à 3 parties, API REST publique v1,
> support MySQL/MariaDB, `SettingsService`, sauvegardes) — les plus jeunes,
> donc les moins éprouvées. Le cœur historique du planning a déjà fait l'objet
> de plusieurs passes documentées (`report/BUG_HUNT_REPORT.md`,
> `report/CHASSE_AU_BUG.md`) et n'est pas repris ici. Chaque trouvaille a été
> vérifiée par lecture directe du code puis, quand c'était possible,
> reproduite empiriquement (test réel qui plante avant correctif, passe
> après) — pas de spéculation.

## Corrigés dans cette PR

### 1. HIGH — Supprimer un shift référencé par un échange actif fait planter `/swaps`, `/admin/swaps` et `/swaps/<id>/confirm`

**Fichiers** : `app/services/shift_service.py` (aucun chemin de suppression
ne vérifie les `SwapRequest` actifs), `app/models/swap_request.py`
(`SwapRequest.shift` est une simple `@property` faisant
`db.session.get(Shift, self.shift_id)` — pas une relation ORM, voir le
docstring du modèle), `app/templates/swaps.html`,
`app/templates/admin/swaps.html`, `app/templates/confirm_swap.html`.

Aucun des chemins de suppression de `ShiftService` (suppression unique ou
en masse — jour/semaine/utilisateur/tout) ne vérifie qu'un `SwapRequest`
référence encore le shift. Une fois la ligne `Shift` supprimée,
`swap.shift` retourne silencieusement `None`. Les trois templates
déréférençaient `swap.shift.date`/`swap_request.shift.date` **sans aucune
garde** — contrairement à `target_shift`, toujours protégé par `{% if
swap.target_shift %}`. Résultat : `jinja2.exceptions.UndefinedError:
'None' has no attribute 'date'`, une exception non gérée qui fait planter
**toute la page** pour chaque utilisateur ayant cette demande dans sa
liste (y compris tous les admins sur `/admin/swaps`) — pas seulement la
ligne concernée. Reproduit et confirmé par un test réel (suppression
directe du shift référencé, puis `GET /swaps` → `UndefinedError`) avant
correctif.

Scénario déclencheur plausible et courant : suppression en masse d'une
semaine/d'un utilisateur par un admin, sans qu'aucun avertissement
n'existe sur un échange en cours.

**Correctif appliqué** : garde défensive dans les 4 emplacements de
templates concernés (`{% if swap.shift %}...{% else %}<span>Shift
supprimé</span>{% endif %}`), même pattern que `target_shift` déjà en
place. La couche service était déjà correcte de son côté : `POST
/swaps/<id>/confirm` passe par `SwapService.confirm_swap()` →
`_validation_error()`, qui gère déjà `shift is None` proprement
(`"Shift introuvable"`) — seul le rendu `GET` (affichage brut dans le
template) avait le trou. Pas de changement de règle métier (blocage de la
suppression, annulation automatique de la demande) : décision produit
plus large, volontairement laissée hors de cette PR — voir "Non traités"
ci-dessous.

Tests de régression ajoutés : `tests/integration/test_swap_routes.py`
(`test_swaps_page_survives_deleted_shift`,
`test_confirm_page_survives_deleted_shift`,
`test_admin_swaps_page_survives_deleted_shift`).

### 2. MEDIUM — Le filtre de domaine de l'audit log ignore silencieusement 2 domaines réels

**Fichier** : `app/routes/admin_audit_routes.py`

`ACTION_DOMAINS` (utilisé pour peupler le menu déroulant de filtre sur
`/admin/audit-log`) listait `auth, group, leave, oncall, profile,
setting, shift, shift_type, swap, user` — mais `AuditService.log()` est
bien appelé avec `"service_account.*"`
(`app/services/service_account_service.py`) et
`"notification_target.*"` (`app/routes/admin_notification_target_routes.py`),
deux domaines introduits par des fonctionnalités récentes. Un admin ne
pouvait donc pas filtrer l'historique sur l'activité des clés API ou des
cibles de notification externes — et pire, `action_prefix = f"{domain}."
if domain in ACTION_DOMAINS else None` (ligne 50) signifie qu'une URL
`?action_domain=service_account` construite à la main ne filtre ni
n'erreure : elle retourne silencieusement la liste complète non filtrée,
pouvant laisser croire à tort que le filtre a fonctionné.

**Correctif** : ajout de `"service_account"` et `"notification_target"`
à `ACTION_DOMAINS`. Le template consomme déjà cette liste dynamiquement
(`{% for domain in action_domains %}`), aucun changement de template
nécessaire.

### 3. LOW — `SettingsService.get_public_base_url()` viole sa propre règle documentée « un Setting présent gagne toujours »

**Fichier** : `app/services/settings_service.py`

`set_public_base_url(None)` stocke une chaîne vide (`url or ""`) — le
seul setter de ce module qui persiste volontairement une valeur falsy,
pour représenter « explicitement effacé ». Mais `get_public_base_url()`
faisait `if value: return str(value)`, donc une ligne `Setting` vide
était traitée comme « absente » et retombait silencieusement sur la
variable d'environnement `PUBLIC_BASE_URL`. Un admin qui efface
explicitement la valeur via `/admin/settings` ne récupère donc pas
« aucune surcharge » comme attendu, mais silencieusement la valeur
d'environnement précédente — contredisant la règle documentée dans
CLAUDE.md ("Configuration: two parallel systems") : *"a Setting row, if
present, always wins"*.

**Correctif** : `if value is not None` (au lieu de `if value:`) —
`Setting.get()` ne retourne `None` que si aucune ligne n'existe du tout
(voir son propre docstring), donc ce test distingue correctement
« jamais configuré » de « explicitement effacé ». Test de régression
ajouté (`tests/unit/test_settings_service.py::test_explicit_clear_does_not_fall_back_to_env`).

### 4. Bug transverse trouvé en creusant Bandit B104 : `PROMETHEUS_ENABLED` jamais câblé

Documenté et corrigé dans `report/SECURITY_AUDIT_v1.0.md` (section
"Corrections apportées") plutôt que répété ici — trouvé pendant l'audit
sécurité, pas la présente passe, mais mérite mention croisée : la
fonctionnalité `/metrics` était structurellement inatteignable en
déploiement réel, masqué par un test qui contournait le vrai chemin
`create_app()`.

## Non traités (identifiés, documentés, décision produit hors périmètre)

### LOW/MEDIUM — Pas de verrouillage optimiste sur les transitions du workflow d'échange

**Fichier** : `app/services/swap_service.py` (`approve_swap`,
`confirm_swap`)

Chaque méthode de transition lit `swap_request.status`, valide, puis
écrit — sans verrou de ligne (`SELECT ... FOR UPDATE`) ni contrôle de
version entre la lecture et le `commit()`. Deux requêtes réellement
concurrentes (deux admins qui cliquent "Approuver" en même temps, ou une
double soumission de `/confirm`) peuvent toutes deux passer les
vérifications `is_awaiting_admin()`/`is_awaiting_target()` avant qu'aucune
ne commite, menant à un double traitement (réassignation du shift deux
fois, notifications dupliquées). Les doubles soumissions *séquentielles*
sont déjà sûres (la deuxième requête relit le statut déjà mis à jour et
est correctement rejetée) — seule la concurrence réelle est concernée.
Non exploitable pour une élévation de privilège, mais un vrai trou
d'intégrité des données dans un workflow dont la raison d'être est
justement « validation à 3 parties, re-validée à chaque étape ». Correctif
(verrou de ligne ou compteur de version) volontairement non appliqué ici
— changement de comportement transactionnel qui mérite sa propre revue,
pas une correction one-off dans une passe de chasse aux bugs.

### LOW — `SettingsService.set_pagination()`/`set_backup_retention()` ne sont pas atomiques entre leurs deux réglages

**Fichier** : `app/services/settings_service.py`,
`app/models/setting.py::Setting.set()`

`Setting.set()` commite en interne à chaque appel. `set_pagination()`
valide `items_per_page <= max_per_page` ensemble puis appelle
`Setting.set()` deux fois — deux transactions indépendantes déjà
commitées chacune. Si le deuxième appel échoue après le succès du
premier, le `except` ne fait un rollback que de la session courante : la
première valeur reste déjà durablement commitée, laissant les deux
réglages dans une combinaison jamais validée ensemble. Faible probabilité
(nécessite une erreur DB transitoire en plein milieu d'une requête), mais
un vrai trou étant donné que la validation est explicitement présentée
comme une contrainte conjointe. Non corrigé : nécessiterait soit une
transaction unique explicite dans `Setting.set()` (changement structurel
touchant tous les appelants), soit une validation avant tout `commit()`
dans chaque setter concerné — décision d'architecture, pas un correctif
isolé.

### LOW — Expiration des clés API à minuit UTC, pas en fin de journée

**Fichier** : `app/routes/admin_service_account_routes.py`,
`app/models/service_account.py`

Le formulaire admin prend une simple date (`<input type="date">`),
convertie en `datetime` à minuit. Un admin qui choisit "2026-08-01" en
pensant que la clé fonctionne jusqu'à la fin de cette journée la verra
déjà invalide dès 00:00 UTC ce jour-là. Erre du côté prudent (expire tôt,
jamais tard) donc pas un problème de sécurité, mais un vrai décalage
sémantique entre ce que suggère l'interface et ce que fait réellement le
contrôle. Non corrigé : changer ça (passer à 23:59:59 ou end-of-day dans
le fuseau de l'admin) est un choix produit mineur mais visible, mérite
confirmation explicite plutôt qu'un changement silencieux de comportement
d'expiration de crédentials.

## Vérifié et écarté (investigué, code correct)

- **Rate limiting de l'API keyed par service account vs IP**
  (`app/api/rate_limit.py`, `app/auth/service_account_auth.py`) :
  suspicion initiale que le hook `before_request` du blueprint tournerait
  après la vérification de rate-limit au niveau app, désactivant la clé
  par compte. Vérifié dans le code source de Flask/Flask-Limiter : les
  décorateurs `@limiter.limit()` au niveau route sont délibérément
  différés à l'appel de la vue (après tous les hooks `before_request` de
  blueprint) — confirmé empiriquement. `g.service_account` est bien
  peuplé avant que la limite par compte ne s'applique. Pas de bug.
- **Conversion multi-fuseau horaire** (lecture/écriture symétriques,
  org-tz ⟷ viewer-tz) : cohérent des deux côtés ; les cas limites de
  DST sont une contrepartie inhérente à tout système basé sur `zoneinfo`,
  déjà un compromis accepté et documenté, pas une régression.
- **`force_locale()` dans les notifications** (email hebdo, notifications
  in-app) : chaque message persisté/multi-destinataire est bien construit
  par destinataire dans son propre bloc `force_locale()`.
- **Cache `flask.g` de `get_date_format()`/`get_time_format()`** :
  correctement scopé par requête, pas de risque de valeur périmée.
- **Path traversal / nettoyage des fichiers temporaires S3 dans
  `BackupService`** : le check `startswith(local_dir + os.sep)` final
  intercepte correctement `../` et l'injection de chemin absolu (vérifié
  directement) ; le fichier temporaire S3 est nettoyé via
  `response.call_on_close()`.
- **Double réservation du même shift comme `target_shift` par deux
  demandes concurrentes** : possible d'atteindre cet état à la
  confirmation, mais `approve_swap()` re-valide et rejette correctement
  la deuxième demande au moment de l'approbation — un désagrément UX, pas
  une corruption de données.
- **`normalize_database_uri()` MySQL/MariaDB** : réécrit correctement les
  schémas nus, laisse intact un `+driver` déjà explicite ; aucun SQL brut
  dépendant du dialecte trouvé ailleurs dans `app/`.

## Verdict

Les fonctionnalités récentes sont globalement bien construites :
conventions de gestion d'erreur cohérentes (fire-and-forget vs
levée d'exception, documenté et respecté), re-validation systématique à
chaque étape du workflow d'échange, gestion symétrique et correcte du
fuseau horaire/de la langue. Le seul problème **haute sévérité** (n°1) a
été corrigé dans cette PR — c'était un vrai trou (rien dans le chemin de
suppression de shift ne savait qu'un `SwapRequest` pouvait le référencer)
et son mode d'échec (page entière en 500, non récupérable sans accès DB)
justifiait une correction avant v1.0 plutôt qu'un simple signalement. Les
trois éléments non traités sont documentés avec leur justification de
mise à l'écart (décision produit ou changement structurel plus large, pas
une négligence) — à trancher explicitement avant ou après le lancement
v1.0, selon la tolérance au risque de l'équipe.
