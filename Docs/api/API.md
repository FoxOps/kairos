# API

> Réécrit intégralement en Phase 5 (2026-07). L'ancienne version
> documentait des routes qui n'ont jamais existé dans le code
> (`/leaves/my-leaves`, `/schedule/my-shifts`, `/oncall/my-oncalls`,
> `/admin/users/generate-token/<id>`) et omettait la quasi-totalité des
> vrais endpoints `/api/*`. Contenu vérifié ligne par ligne contre
> `app/routes/*.py`.

Pour une spec machine-lisible complète (schémas, codes d'erreur), voir
[`openapi.yaml`](openapi.yaml) — importable dans Swagger UI, Postman,
Insomnia, etc.

## Important : cette application n'est pas une API REST

La quasi-totalité des routes de Leviia Schedule rendent des pages HTML
côté serveur (Jinja2), pas du JSON — c'est une application web
traditionnelle, pas une SPA consommant une API. Seuls les endpoints
listés ci-dessous renvoient du JSON ou du contenu ICS. Pour toutes les
autres routes (créer un utilisateur, ajouter un shift en masse depuis le
formulaire admin, etc.), voir le
[Guide Administrateur](../guides/ADMIN_GUIDE.md) et le
[Guide Utilisateur](../guides/USER_GUIDE.md).

## Authentification

- **Session** : cookie de session Flask-Login, créé par `POST /login`
  (email/mot de passe) ou le flux OIDC (`GET /oidc/login` →
  `GET /oidc/callback`).
- **CSRF** : toute requête d'écriture (POST/PUT/PATCH/DELETE) doit inclure
  l'en-tête `X-CSRFToken`, dont la valeur est lue depuis
  `<meta name="csrf-token">` sur les pages HTML rendues par le serveur.
  Sans lui : `400 Bad Request`. Voir
  [`architecture/SEQUENCE_DIAGRAMS.md`](../architecture/SEQUENCE_DIAGRAMS.md#mise-à-jour-dun-shift-par-glisser-déposer-api-json--csrf).
- **Token ICS** (`export/*` uniquement) : bearer token dans le paramètre
  de requête `?token=...`, généré par un utilisateur via
  `POST /profile/ics-token`. Pensé pour les abonnements calendrier
  externes (Google Calendar, Outlook) qui ne portent pas de cookie.

## Endpoints JSON

### Planning (`/api/shifts`, `/api/users`, `/api/shift-types`)

| Méthode | Route | Auth | Description |
|---|---|---|---|
| GET | `/api/shifts` | connecté | Événements calendrier (shifts **+ astreintes + congés**, malgré le nom) sur ±180 jours, format FullCalendar |
| POST | `/api/shifts` | admin | Crée un shift (`userId`, `shiftTypeId`, `start`, `end?`) |
| PATCH/PUT | `/api/shifts/<id>` | admin | Déplace/redimensionne (`start`, `end?` — durée conservée si `end` absent) |
| DELETE | `/api/shifts/<id>` | admin | Supprime |
| GET | `/api/users` | connecté | Utilisateurs visibles (admin : tous ; utilisateur normal : lui-même) |
| GET | `/api/shift-types` | connecté | Liste des types de shift |

Règles de validation communes à POST/PATCH `/api/shifts` :
- Rejeté (`400`) si la date tombe un samedi/dimanche.
- Rejeté (`400`) si l'utilisateur a déjà un shift ce jour-là (conflit).

### Astreintes (`/api/oncall/<id>`)

| Méthode | Route | Auth | Description |
|---|---|---|---|
| PATCH/PUT | `/api/oncall/<id>` | admin | Déplace (`start` doit tomber un **vendredi**, `end?`) |
| DELETE | `/api/oncall/<id>` | admin | Supprime |

Il n'y a **pas** de `POST /api/oncall` — la création se fait uniquement
via le formulaire `/oncall/add` (server-rendered), pas par API JSON.

### Congés (`/api/leave/<id>`)

| Méthode | Route | Auth | Description |
|---|---|---|---|
| PATCH/PUT | `/api/leave/<id>` | connecté | Modifie les dates (`start`, `end?`) — restreint à ses propres congés sauf admin |
| DELETE | `/api/leave/<id>` | connecté | Supprime — même restriction |

Contrairement aux shifts et astreintes (réservés admin), un utilisateur
normal peut modifier/supprimer **ses propres** congés via l'API — un
`403` est renvoyé s'il tente d'agir sur le congé d'un autre utilisateur.

### Export ICS (`/export/*`)

| Méthode | Route | Auth | Description |
|---|---|---|---|
| GET | `/export/shifts?scope=my\|all&token=...` | session ou token | Export `.ics` des shifts |
| GET | `/export/oncall?scope=my\|all&token=...` | session ou token | Export `.ics` des astreintes |
| GET | `/export/leaves?scope=my\|all&token=...` | session ou token | Export `.ics` des congés |

`scope` par défaut : `all`. `scope=my` filtre sur l'utilisateur résolu
(session ou token). Réponse `401` si ni session ni token valide (ou
redirect `/login` pour un client navigateur classique).

## Formats de réponse

Toutes les réponses JSON d'écriture (POST/PATCH/DELETE) suivent le même
format :

```json
// Succès
{ "success": true, "message": "...", "shift": { /* objet créé/modifié, si pertinent */ } }

// Erreur
{ "success": false, "error": "message d'erreur en français" }
```

## Codes HTTP utilisés

| Code | Signification dans ce contexte |
|---|---|
| 200 | Succès |
| 400 | Validation échouée (dates, conflit, week-end, JSON absent/invalide, CSRF absent/invalide) |
| 401 | Non authentifié (routes HTML : redirect `/login` à la place) |
| 403 | Authentifié mais non autorisé (non-admin sur route admin, ou congé d'un autre utilisateur) |
| 404 | Ressource introuvable |
| 500 | Erreur serveur inattendue |

## Modèles de données référencés

Voir [`architecture/ERD.md`](../architecture/ERD.md) pour le schéma
complet. Champs à retenir pour l'API :

- Un objet **shift** JSON expose `id`, `title`, `start`, `end`,
  `className`, `userId`, `shiftTypeId` — pas directement les colonnes du
  modèle `Shift`.
- Le modèle `Leave` **n'a pas de champ `reason`** malgré ce que
  documentait l'ancienne version de ce fichier.
- `User.to_dict()` exclut toujours `password_hash` et `ics_token` — ces
  champs ne sont jamais présents dans une réponse JSON, y compris
  `/api/users`.
