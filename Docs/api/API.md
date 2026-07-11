# 📡 API Documentation - Leviia Schedule

> **Version** : 1.0.0 - Documentation API Complète
> **Dernière mise à jour** : Juin 2026
> **Statut** : Développement actif
> **Base URL** : `http://localhost:5000` (développement) / `https://votre-domaine.com` (production)

---

## 📋 Table des Matières

- [📖 Vue d'ensemble](#-vue-densemble)
- [🔐 Authentification](#-authentification)
- [📋 Endpoints API](#-endpoints-api)
  - [Authentification](#authentification-1)
  - [Utilisateurs](#utilisateurs)
  - [Groupes](#groupes)
  - [Types de Shifts](#types-de-shifts)
  - [Shifts](#shifts)
  - [Astreintes (On-Call)](#astreintes-on-call)
  - [Congés](#congés)
  - [Export ICS](#export-ics)
  - [Administration](#administration)
- [📊 Schémas de Données](#-schémas-de-données)
- [📝 Exemples de Requêtes](#-exemples-de-requêtes)
- [🔧 Codes de Réponse](#-codes-de-réponse)
- [🚀 Bonnes Pratiques](#-bonnes-pratiques)
- [📝 Historique des Changements](#-historique-des-changements)

---

## 📖 Vue d'ensemble

L'API REST de **Leviia Schedule** permet d'interagir avec l'application de gestion des plannings et des astreintes. Elle suit les principes REST et retourne des réponses au format JSON (sauf pour les exports ICS).

### Caractéristiques de l'API

- **Format** : JSON (sauf export ICS qui retourne `text/calendar`)
- **Authentification** : Basée sur les sessions (Flask-Login) ou tokens ICS
- **Content-Type** : `application/json` pour les requêtes et réponses
- **CORS** : Désactivé par défaut (peut être activé via `CORS_ENABLED=true`)
- **Rate Limiting** : Non implémenté (à ajouter pour la production)

### Versionnement

- **Version actuelle** : v1 (non versionnée dans l'URL)
- **Compatibilité** : L'API est en développement, les changements peuvent être cassants

---

## 🔐 Authentification

### Méthodes d'Authentification

L'API supporte deux méthodes d'authentification :

#### 1. Authentification par Session (Flask-Login)

**Utilisation :**
- Connexion via `/login` (POST) avec email et mot de passe
- Les requêtes suivantes utilisent le cookie de session
- Déconnexion via `/logout`

**Headers requis :**
```
Cookie: session=your_session_id
```

**Exemple :**
```bash
# Connexion
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "email=admin@leviia.local&password=admin123"

# Requête authentifiée
curl http://localhost:5000/admin \
  -H "Cookie: session=your_session_id"
```

#### 2. Authentification par Token ICS

**Utilisation :**
- Chaque utilisateur a un token ICS unique (`ics_token`)
- Utilisé pour l'export ICS sans authentification par session
- Le token est généré automatiquement lors de la création de l'utilisateur

**Paramètres de requête :**
```
?token=your_ics_token
```

**Exemple :**
```bash
# Export ICS avec token
curl http://localhost:5000/export/shifts?token=your_ics_token
```

#### 3. Désactivation de l'Authentification (Développement uniquement)

**⚠️ ATTENTION :** Ne jamais utiliser en production !

```bash
export LOGIN_DISABLED=true
```

### Gestion des Sessions

- **Durée du cookie** : 1 jour (configurable via `REMEMBER_COOKIE_DURATION`)
- **Protection de session** : `strong` (configurable via `SESSION_PROTECTION`)
- **Stockage** : Côté serveur (Flask)

### Rôles et Permissions

| Rôle | Description | Accès |
|------|-------------|-------|
| **Admin** | Administrateur | Accès complet à toutes les fonctionnalités |
| **User** | Utilisateur standard | Accès limité à ses propres données |

**Vérification des permissions :**
- Les routes admin nécessitent le décorateur `@admin_required`
- Les routes utilisateur nécessitent `@login_required`
- Certaines routes vérifient la propriété des ressources (`@user_owns_resource`)

---

## 📋 Endpoints API

### Authentification

#### `POST /login`

**Description** : Connecter un utilisateur

**Request Body (form-data) :**
```
email: string (requis)
password: string (requis)
remember: boolean (optionnel, default: false)
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "email=admin@leviia.local&password=admin123&remember=true"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/` | - |
| 400 | Email ou mot de passe manquant | Message d'erreur |
| 401 | Email ou mot de passe incorrect | Message d'erreur |

**Cookies :**
- `session` : Cookie de session Flask
- `remember_token` : Cookie de souvenir (si `remember=true`)

---

#### `GET /logout`

**Description** : Déconnecter l'utilisateur actuel

**Headers requis :**
```
Cookie: session=your_session_id
```

**Exemple de requête :**
```bash
curl http://localhost:5000/logout \
  -H "Cookie: session=your_session_id"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/` | - |

---

#### `GET /profile`

**Description** : Récupérer le profil de l'utilisateur actuel

**Headers requis :**
```
Cookie: session=your_session_id
```

**Exemple de requête :**
```bash
curl http://localhost:5000/profile \
  -H "Cookie: session=your_session_id"
```

**Réponse (200 OK) :**
```json
{
  "id": 1,
  "name": "Administrateur",
  "email": "admin@leviia.local",
  "is_admin": true,
  "group": {
    "id": 1,
    "name": "Default Group"
  }
}
```

---

#### `GET /profile/update`
#### `POST /profile/update`

**Description** : Mettre à jour le profil de l'utilisateur actuel

**Headers requis :**
```
Cookie: session=your_session_id
```

**Request Body (form-data) :**
```
name: string (requis)
email: string (requis)
current_password: string (optionnel, requis pour changer le mot de passe)
new_password: string (optionnel)
confirm_password: string (optionnel, doit correspondre à new_password)
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/profile/update \
  -H "Cookie: session=your_session_id" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "name=Nouveau Nom&email=nouveau@email.com&current_password=admin123&new_password=nouveau123&confirm_password=nouveau123"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/profile` | - |
| 400 | Données manquantes ou invalides | Message d'erreur |

---

### Utilisateurs

#### `GET /admin/users`

**Description** : Lister tous les utilisateurs (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Exemple de requête :**
```bash
curl http://localhost:5000/admin/users \
  -H "Cookie: session=your_session_id"
```

**Réponse (200 OK) :**
```json
[
  {
    "id": 1,
    "name": "Administrateur",
    "email": "admin@leviia.local",
    "is_admin": true,
    "group_id": 1,
    "group": {
      "id": 1,
      "name": "Default Group"
    }
  },
  {
    "id": 2,
    "name": "Utilisateur 1",
    "email": "user1@leviia.local",
    "is_admin": false,
    "group_id": 1,
    "group": {
      "id": 1,
      "name": "Default Group"
    }
  }
]
```

---

#### `GET /admin/users/add`
#### `POST /admin/users/add`

**Description** : Ajouter un nouvel utilisateur (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Request Body (form-data) :**
```
name: string (requis)
email: string (requis, unique)
password: string (requis)
confirm_password: string (requis, doit correspondre à password)
group_id: integer (requis)
is_admin: boolean (optionnel, default: false)
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/admin/users/add \
  -H "Cookie: session=your_session_id" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "name=Nouvel Utilisateur&email=nouvel@email.com&password=motdepasse&confirm_password=motdepasse&group_id=1&is_admin=false"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/admin/users` | - |
| 400 | Données manquantes ou invalides | Message d'erreur |

---

#### `GET /admin/users/edit/<int:user_id>`
#### `POST /admin/users/edit/<int:user_id>`

**Description** : Modifier un utilisateur (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Request Body (form-data) :**
```
name: string (requis)
email: string (requis, unique)
group_id: integer (requis)
is_admin: boolean (optionnel)
password: string (optionnel)
confirm_password: string (optionnel, doit correspondre à password)
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/admin/users/edit/2 \
  -H "Cookie: session=your_session_id" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "name=Utilisateur Modifié&email=modifie@email.com&group_id=1&is_admin=true"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/admin/users` | - |
| 400 | Données manquantes ou invalides | Message d'erreur |
| 404 | Utilisateur non trouvé | Message d'erreur |

---

#### `POST /admin/users/delete/<int:user_id>`

**Description** : Supprimer un utilisateur (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/admin/users/delete/2 \
  -H "Cookie: session=your_session_id"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/admin/users` | - |
| 404 | Utilisateur non trouvé | Message d'erreur |

---

#### `POST /admin/users/generate-token/<int:user_id>`

**Description** : Générer un nouveau token ICS pour un utilisateur (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/admin/users/generate-token/2 \
  -H "Cookie: session=your_session_id"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/admin/users` | - |
| 200 | Token généré | `{"token": "nouveau_token_ics"}` |
| 404 | Utilisateur non trouvé | Message d'erreur |

---

### Groupes

#### `GET /admin/groups`

**Description** : Lister tous les groupes (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Exemple de requête :**
```bash
curl http://localhost:5000/admin/groups \
  -H "Cookie: session=your_session_id"
```

**Réponse (200 OK) :**
```json
[
  {
    "id": 1,
    "name": "Default Group",
    "is_part_of_schedule": true,
    "is_part_of_oncall": true,
    "users_count": 5
  },
  {
    "id": 2,
    "name": "Équipe A",
    "is_part_of_schedule": true,
    "is_part_of_oncall": false,
    "users_count": 3
  }
]
```

---

#### `GET /admin/groups/add`
#### `POST /admin/groups/add`

**Description** : Ajouter un nouveau groupe (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Request Body (form-data) :**
```
name: string (requis, unique)
is_part_of_schedule: boolean (optionnel, default: false)
is_part_of_oncall: boolean (optionnel, default: false)
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/admin/groups/add \
  -H "Cookie: session=your_session_id" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "name=Nouveau Groupe&is_part_of_schedule=true&is_part_of_oncall=true"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/admin/groups` | - |
| 400 | Données manquantes ou invalides | Message d'erreur |

---

#### `GET /admin/groups/edit/<int:group_id>`
#### `POST /admin/groups/edit/<int:group_id>`

**Description** : Modifier un groupe (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Request Body (form-data) :**
```
name: string (requis)
is_part_of_schedule: boolean (optionnel)
is_part_of_oncall: boolean (optionnel)
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/admin/groups/edit/2 \
  -H "Cookie: session=your_session_id" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "name=Groupe Modifié&is_part_of_schedule=true&is_part_of_oncall=false"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/admin/groups` | - |
| 400 | Données manquantes ou invalides | Message d'erreur |
| 404 | Groupe non trouvé | Message d'erreur |

---

#### `POST /admin/groups/delete/<int:group_id>`

**Description** : Supprimer un groupe (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/admin/groups/delete/2 \
  -H "Cookie: session=your_session_id"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/admin/groups` | - |
| 404 | Groupe non trouvé | Message d'erreur |

---

### Types de Shifts

#### `GET /admin/shift-types`

**Description** : Lister tous les types de shifts (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Exemple de requête :**
```bash
curl http://localhost:5000/admin/shift-types \
  -H "Cookie: session=your_session_id"
```

**Réponse (200 OK) :**
```json
[
  {
    "id": 1,
    "name": "matin",
    "label": "Matin",
    "start_hour": 8,
    "end_hour": 12
  },
  {
    "id": 2,
    "name": "apres-midi",
    "label": "Après-midi",
    "start_hour": 12,
    "end_hour": 18
  },
  {
    "id": 3,
    "name": "soiree",
    "label": "Soirée",
    "start_hour": 18,
    "end_hour": 22
  }
]
```

---

#### `GET /admin/shift-types/add`
#### `POST /admin/shift-types/add`

**Description** : Ajouter un nouveau type de shift (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Request Body (form-data) :**
```
name: string (requis, unique)
label: string (requis)
start_hour: integer (requis, 0-23)
end_hour: integer (requis, 0-23, doit être > start_hour)
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/admin/shift-types/add \
  -H "Cookie: session=your_session_id" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "name=nuit&label=Nuit&start_hour=22&end_hour=6"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/admin/shift-types` | - |
| 400 | Données manquantes ou invalides | Message d'erreur |

---

#### `GET /admin/shift-types/edit/<int:shift_type_id>`
#### `POST /admin/shift-types/edit/<int:shift_type_id>`

**Description** : Modifier un type de shift (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Request Body (form-data) :**
```
name: string (requis)
label: string (requis)
start_hour: integer (requis, 0-23)
end_hour: integer (requis, 0-23, doit être > start_hour)
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/admin/shift-types/edit/1 \
  -H "Cookie: session=your_session_id" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "name=matin&label=Matin&start_hour=7&end_hour=13"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/admin/shift-types` | - |
| 400 | Données manquantes ou invalides | Message d'erreur |
| 404 | Type de shift non trouvé | Message d'erreur |

---

#### `POST /admin/shift-types/delete/<int:shift_type_id>`

**Description** : Supprimer un type de shift (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/admin/shift-types/delete/3 \
  -H "Cookie: session=your_session_id"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/admin/shift-types` | - |
| 404 | Type de shift non trouvé | Message d'erreur |

---

### Shifts

#### `GET /schedule`

**Description** : Afficher le planning des shifts

**Headers requis :**
```
Cookie: session=your_session_id
```

**Paramètres de requête :**
| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| `view` | string | Vue du calendrier (`day`, `week`, `month`) | `month` |
| `date` | date | Date de référence (format: `YYYY-MM-DD`) | aujourd'hui |

**Exemple de requête :**
```bash
curl http://localhost:5000/schedule?view=week&date=2026-06-15 \
  -H "Cookie: session=your_session_id"
```

**Réponse (200 OK) :**
```json
{
  "shifts": [
    {
      "id": 1,
      "user": {
        "id": 1,
        "name": "Utilisateur 1"
      },
      "shift_type": {
        "id": 1,
        "name": "matin",
        "label": "Matin"
      },
      "start_time": "2026-06-15T08:00:00",
      "end_time": "2026-06-15T12:00:00",
      "date": "2026-06-15"
    }
  ],
  "on_calls": [],
  "leaves": []
}
```

---

#### `POST /schedule/shift`

**Description** : Ajouter un nouveau shift

**Headers requis :**
```
Cookie: session=your_session_id
Content-Type: application/x-www-form-urlencoded
```

**Request Body (form-data) :**
```
user_id: integer (requis)
shift_type_id: integer (requis)
date: date (requis, format: YYYY-MM-DD)
start_time: time (optionnel, format: HH:MM, défaut: heure de début du type de shift)
end_time: time (optionnel, format: HH:MM, défaut: heure de fin du type de shift)
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/schedule/shift \
  -H "Cookie: session=your_session_id" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "user_id=1&shift_type_id=1&date=2026-06-15"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/schedule` | - |
| 400 | Données manquantes ou invalides | Message d'erreur |
| 403 | Non autorisé (utilisateur ou groupe non autorisé) | Message d'erreur |

---

#### `POST /schedule/shift/<int:shift_id>/delete`

**Description** : Supprimer un shift

**Headers requis :**
```
Cookie: session=your_session_id
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/schedule/shift/1/delete \
  -H "Cookie: session=your_session_id"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/schedule` | - |
| 403 | Non autorisé (seul l'admin ou le propriétaire peut supprimer) | Message d'erreur |
| 404 | Shift non trouvé | Message d'erreur |

---

#### `GET /schedule/my-shifts`

**Description** : Récupérer les shifts de l'utilisateur actuel

**Headers requis :**
```
Cookie: session=your_session_id
```

**Paramètres de requête :**
| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| `start_date` | date | Date de début (format: `YYYY-MM-DD`) | 6 mois avant |
| `end_date` | date | Date de fin (format: `YYYY-MM-DD`) | 6 mois après |

**Exemple de requête :**
```bash
curl http://localhost:5000/schedule/my-shifts?start_date=2026-06-01&end_date=2026-06-30 \
  -H "Cookie: session=your_session_id"
```

**Réponse (200 OK) :**
```json
{
  "shifts": [
    {
      "id": 1,
      "shift_type": {
        "id": 1,
        "name": "matin",
        "label": "Matin"
      },
      "start_time": "2026-06-15T08:00:00",
      "end_time": "2026-06-15T12:00:00",
      "date": "2026-06-15"
    }
  ]
}
```

---

### Astreintes (On-Call)

#### `GET /oncall`

**Description** : Afficher les astreintes

**Headers requis :**
```
Cookie: session=your_session_id
```

**Paramètres de requête :**
| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| `view` | string | Vue du calendrier (`day`, `week`, `month`) | `month` |
| `date` | date | Date de référence (format: `YYYY-MM-DD`) | aujourd'hui |

**Exemple de requête :**
```bash
curl http://localhost:5000/oncall?view=week&date=2026-06-15 \
  -H "Cookie: session=your_session_id"
```

**Réponse (200 OK) :**
```json
{
  "on_calls": [
    {
      "id": 1,
      "user": {
        "id": 1,
        "name": "Utilisateur 1"
      },
      "start_time": "2026-06-15T18:00:00",
      "end_time": "2026-06-16T08:00:00"
    }
  ]
}
```

---

#### `POST /oncall`

**Description** : Ajouter une nouvelle astreinte

**Headers requis :**
```
Cookie: session=your_session_id
Content-Type: application/x-www-form-urlencoded
```

**Request Body (form-data) :**
```
user_id: integer (requis)
start_time: datetime (requis, format: YYYY-MM-DD HH:MM)
end_time: datetime (requis, format: YYYY-MM-DD HH:MM)
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/oncall \
  -H "Cookie: session=your_session_id" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "user_id=1&start_time=2026-06-15 18:00&end_time=2026-06-16 08:00"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/oncall` | - |
| 400 | Données manquantes ou invalides | Message d'erreur |
| 403 | Non autorisé (utilisateur ou groupe non autorisé) | Message d'erreur |

---

#### `POST /oncall/<int:oncall_id>/delete`

**Description** : Supprimer une astreinte

**Headers requis :**
```
Cookie: session=your_session_id
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/oncall/1/delete \
  -H "Cookie: session=your_session_id"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/oncall` | - |
| 403 | Non autorisé (seul l'admin ou le propriétaire peut supprimer) | Message d'erreur |
| 404 | Astreinte non trouvée | Message d'erreur |

---

#### `GET /oncall/my-oncalls`

**Description** : Récupérer les astreintes de l'utilisateur actuel

**Headers requis :**
```
Cookie: session=your_session_id
```

**Paramètres de requête :**
| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| `start_date` | date | Date de début (format: `YYYY-MM-DD`) | 6 mois avant |
| `end_date` | date | Date de fin (format: `YYYY-MM-DD`) | 6 mois après |

**Exemple de requête :**
```bash
curl http://localhost:5000/oncall/my-oncalls?start_date=2026-06-01&end_date=2026-06-30 \
  -H "Cookie: session=your_session_id"
```

**Réponse (200 OK) :**
```json
{
  "on_calls": [
    {
      "id": 1,
      "start_time": "2026-06-15T18:00:00",
      "end_time": "2026-06-16T08:00:00"
    }
  ]
}
```

---

### Congés

#### `GET /leaves`

**Description** : Afficher les congés

**Headers requis :**
```
Cookie: session=your_session_id
```

**Paramètres de requête :**
| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| `view` | string | Vue du calendrier (`day`, `week`, `month`) | `month` |
| `date` | date | Date de référence (format: `YYYY-MM-DD`) | aujourd'hui |

**Exemple de requête :**
```bash
curl http://localhost:5000/leaves?view=month&date=2026-06-15 \
  -H "Cookie: session=your_session_id"
```

**Réponse (200 OK) :**
```json
{
  "leaves": [
    {
      "id": 1,
      "user": {
        "id": 1,
        "name": "Utilisateur 1"
      },
      "start_date": "2026-06-15",
      "end_date": "2026-06-20"
    }
  ]
}
```

---

#### `POST /leaves`

**Description** : Ajouter un nouveau congé

**Headers requis :**
```
Cookie: session=your_session_id
Content-Type: application/x-www-form-urlencoded
```

**Request Body (form-data) :**
```
start_date: date (requis, format: YYYY-MM-DD)
end_date: date (requis, format: YYYY-MM-DD)
reason: string (optionnel)
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/leaves \
  -H "Cookie: session=your_session_id" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "start_date=2026-07-01&end_date=2026-07-15&reason=Vacances d'été"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/leaves` | - |
| 400 | Données manquantes ou invalides | Message d'erreur |

---

#### `POST /leaves/<int:leave_id>/delete`

**Description** : Supprimer un congé

**Headers requis :**
```
Cookie: session=your_session_id
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/leaves/1/delete \
  -H "Cookie: session=your_session_id"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 302 | Redirection vers `/leaves` | - |
| 403 | Non autorisé (seul l'admin ou le propriétaire peut supprimer) | Message d'erreur |
| 404 | Congé non trouvé | Message d'erreur |

---

#### `GET /leaves/my-leaves`

**Description** : Récupérer les congés de l'utilisateur actuel

**Headers requis :**
```
Cookie: session=your_session_id
```

**Paramètres de requête :**
| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| `start_date` | date | Date de début (format: `YYYY-MM-DD`) | 6 mois avant |
| `end_date` | date | Date de fin (format: `YYYY-MM-DD`) | 6 mois après |

**Exemple de requête :**
```bash
curl http://localhost:5000/leaves/my-leaves?start_date=2026-06-01&end_date=2026-06-30 \
  -H "Cookie: session=your_session_id"
```

**Réponse (200 OK) :**
```json
{
  "leaves": [
    {
      "id": 1,
      "start_date": "2026-06-15",
      "end_date": "2026-06-20",
      "reason": "Vacances"
    }
  ]
}
```

---

### Export ICS

#### `GET /export/shifts`

**Description** : Exporter les shifts au format ICS (iCalendar)

**Méthodes d'authentification :**
1. **Session** : Utilisateur connecté
2. **Token** : `?token=your_ics_token`

**Paramètres de requête :**
| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| `scope` | string | Portée de l'export (`all`, `my`) | `all` |
| `token` | string | Token ICS de l'utilisateur | - |

**Headers :**
```
Accept: text/calendar
Cookie: session=your_session_id  # Si authentification par session
```

**Exemple de requête (avec session) :**
```bash
curl http://localhost:5000/export/shifts?scope=my \
  -H "Cookie: session=your_session_id" \
  -H "Accept: text/calendar"
```

**Exemple de requête (avec token) :**
```bash
curl http://localhost:5000/export/shifts?scope=my&token=your_ics_token \
  -H "Accept: text/calendar"
```

**Réponse (200 OK) :**
```
Content-Type: text/calendar; charset=utf-8
Content-Disposition: attachment; filename=shifts_my.ics

BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Leviia Schedule//leviia-schedule//FR
BEGIN:VEVENT
UID:shift-1@leviia-schedule
DTSTART:20260615T080000
DTEND:20260615T120000
SUMMARY:Shift: Matin
DESCRIPTION:Shift pour Utilisateur 1
END:VEVENT
END:VCALENDAR
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 200 | Export réussi | Fichier ICS |
| 401 | Non autorisé | Message d'erreur |
| 404 | Utilisateur non trouvé | Message d'erreur |

---

#### `GET /export/oncall`

**Description** : Exporter les astreintes au format ICS

**Méthodes d'authentification :**
1. **Session** : Utilisateur connecté
2. **Token** : `?token=your_ics_token`

**Paramètres de requête :**
| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| `scope` | string | Portée de l'export (`all`, `my`) | `all` |
| `token` | string | Token ICS de l'utilisateur | - |

**Exemple de requête :**
```bash
curl http://localhost:5000/export/oncall?scope=my&token=your_ics_token \
  -H "Accept: text/calendar"
```

**Réponse (200 OK) :**
```
Content-Type: text/calendar; charset=utf-8
Content-Disposition: attachment; filename=oncall_my.ics

BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Leviia Schedule//leviia-schedule//FR
BEGIN:VEVENT
UID:oncall-1@leviia-schedule
DTSTART:20260615T180000
DTEND:20260616T080000
SUMMARY:Astreinte - Utilisateur 1
DESCRIPTION:Astreinte pour Utilisateur 1
END:VEVENT
END:VCALENDAR
```

---

#### `GET /export/leaves`

**Description** : Exporter les congés au format ICS

**Méthodes d'authentification :**
1. **Session** : Utilisateur connecté
2. **Token** : `?token=your_ics_token`

**Paramètres de requête :**
| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| `scope` | string | Portée de l'export (`all`, `my`) | `all` |
| `token` | string | Token ICS de l'utilisateur | - |

**Exemple de requête :**
```bash
curl http://localhost:5000/export/leaves?scope=my&token=your_ics_token \
  -H "Accept: text/calendar"
```

---

### Administration

#### `GET /admin`

**Description** : Dashboard d'administration (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Exemple de requête :**
```bash
curl http://localhost:5000/admin \
  -H "Cookie: session=your_session_id"
```

**Réponse (200 OK) :**
```json
{
  "stats": {
    "users_count": 5,
    "shifts_count": 100,
    "on_calls_count": 20,
    "leaves_count": 10,
    "groups_count": 2
  }
}
```

---

#### `GET /admin/automation`

**Description** : Statut de l'automatisation (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Exemple de requête :**
```bash
curl http://localhost:5000/admin/automation \
  -H "Cookie: session=your_session_id"
```

**Réponse (200 OK) :**
```json
{
  "automation_status": {
    "shift_automation": {
      "enabled": true,
      "last_run": "2026-06-15T10:00:00",
      "next_run": "2026-06-16T10:00:00"
    },
    "oncall_automation": {
      "enabled": true,
      "last_run": "2026-06-15T09:00:00",
      "next_run": "2026-06-16T09:00:00"
    }
  }
}
```

---

#### `POST /admin/automation/run`

**Description** : Exécuter manuellement l'automatisation (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Exemple de requête :**
```bash
curl -X POST http://localhost:5000/admin/automation/run \
  -H "Cookie: session=your_session_id"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 200 | Automatisation exécutée | `{"status": "success", "message": "Automatisation exécutée avec succès"}` |
| 500 | Erreur lors de l'exécution | Message d'erreur |

---

#### `GET /admin/cleanup`

**Description** : Nettoyer les données anciennes (admin uniquement)

**Headers requis :**
```
Cookie: session=your_session_id
```

**Paramètres de requête :**
| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| `days` | integer | Nombre de jours à conserver | 365 |

**Exemple de requête :**
```bash
curl http://localhost:5000/admin/cleanup?days=365 \
  -H "Cookie: session=your_session_id"
```

**Réponses :**
| Code | Description | Body |
|------|-------------|------|
| 200 | Nettoyage effectué | `{"status": "success", "deleted": {"shifts": 10, "on_calls": 5, "leaves": 2}}` |
| 500 | Erreur lors du nettoyage | Message d'erreur |

---

## 📊 Schémas de Données

### User

```json
{
  "id": 1,
  "name": "string",
  "email": "string",
  "is_admin": true,
  "group_id": 1,
  "group": {
    "id": 1,
    "name": "string",
    "is_part_of_schedule": true,
    "is_part_of_oncall": true
  },
  "ics_token": "string"
}
```

### Group

```json
{
  "id": 1,
  "name": "string",
  "is_part_of_schedule": true,
  "is_part_of_oncall": true,
  "users_count": 5
}
```

### ShiftType

```json
{
  "id": 1,
  "name": "string",
  "label": "string",
  "start_hour": 8,
  "end_hour": 12
}
```

### Shift

```json
{
  "id": 1,
  "user_id": 1,
  "user": {
    "id": 1,
    "name": "string"
  },
  "shift_type_id": 1,
  "shift_type": {
    "id": 1,
    "name": "string",
    "label": "string"
  },
  "start_time": "2026-06-15T08:00:00",
  "end_time": "2026-06-15T12:00:00",
  "date": "2026-06-15"
}
```

### OnCall

```json
{
  "id": 1,
  "user_id": 1,
  "user": {
    "id": 1,
    "name": "string"
  },
  "start_time": "2026-06-15T18:00:00",
  "end_time": "2026-06-16T08:00:00"
}
```

### Leave

```json
{
  "id": 1,
  "user_id": 1,
  "user": {
    "id": 1,
    "name": "string"
  },
  "start_date": "2026-06-15",
  "end_date": "2026-06-20",
  "reason": "string"
}
```

---

## 📝 Exemples de Requêtes

### Exemple 1 : Authentification et Récupération du Profil

```bash
# 1. Connexion
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "email=admin@leviia.local&password=admin123"

# 2. Récupérer le profil (avec le cookie de session)
curl http://localhost:5000/profile \
  -H "Cookie: session=your_session_id"
```

### Exemple 2 : Gestion des Utilisateurs (Admin)

```bash
# 1. Lister tous les utilisateurs
curl http://localhost:5000/admin/users \
  -H "Cookie: session=your_session_id"

# 2. Ajouter un nouvel utilisateur
curl -X POST http://localhost:5000/admin/users/add \
  -H "Cookie: session=your_session_id" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "name=Nouvel Utilisateur&email=nouvel@email.com&password=motdepasse&confirm_password=motdepasse&group_id=1"

# 3. Générer un token ICS pour un utilisateur
curl -X POST http://localhost:5000/admin/users/generate-token/2 \
  -H "Cookie: session=your_session_id"
```

### Exemple 3 : Gestion des Shifts

```bash
# 1. Lister les shifts de l'utilisateur actuel
curl http://localhost:5000/schedule/my-shifts \
  -H "Cookie: session=your_session_id"

# 2. Ajouter un nouveau shift
curl -X POST http://localhost:5000/schedule/shift \
  -H "Cookie: session=your_session_id" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "user_id=1&shift_type_id=1&date=2026-06-15"

# 3. Supprimer un shift
curl -X POST http://localhost:5000/schedule/shift/1/delete \
  -H "Cookie: session=your_session_id"
```

### Exemple 4 : Export ICS

```bash
# 1. Export des shifts avec session
curl http://localhost:5000/export/shifts?scope=my \
  -H "Cookie: session=your_session_id" \
  -H "Accept: text/calendar" \
  --output my_shifts.ics

# 2. Export des astreintes avec token
curl http://localhost:5000/export/oncall?scope=my&token=your_ics_token \
  -H "Accept: text/calendar" \
  --output my_oncall.ics

# 3. Export de tous les shifts (admin)
curl http://localhost:5000/export/shifts?scope=all \
  -H "Cookie: session=your_session_id" \
  -H "Accept: text/calendar" \
  --output all_shifts.ics
```

### Exemple 5 : Automatisation (Admin)

```bash
# 1. Vérifier le statut de l'automatisation
curl http://localhost:5000/admin/automation \
  -H "Cookie: session=your_session_id"

# 2. Exécuter manuellement l'automatisation
curl -X POST http://localhost:5000/admin/automation/run \
  -H "Cookie: session=your_session_id"

# 3. Nettoyer les données anciennes
curl http://localhost:5000/admin/cleanup?days=365 \
  -H "Cookie: session=your_session_id"
```

---

## 🔧 Codes de Réponse

### Codes HTTP Standard

| Code | Nom | Description |
|------|-----|-------------|
| 200 | OK | Requête réussie |
| 201 | Created | Ressource créée avec succès |
| 302 | Found | Redirection |
| 400 | Bad Request | Requête mal formée ou données invalides |
| 401 | Unauthorized | Authentification requise |
| 403 | Forbidden | Accès interdit (autorisation insuffisante) |
| 404 | Not Found | Ressource non trouvée |
| 405 | Method Not Allowed | Méthode HTTP non supportée |
| 500 | Internal Server Error | Erreur interne du serveur |
| 502 | Bad Gateway | Mauvaise passerelle |
| 503 | Service Unavailable | Service temporairement indisponible |
| 504 | Gateway Timeout | Délai d'attente dépassé |

### Messages d'Erreur Communs

#### 400 Bad Request

```json
{
  "error": "Bad Request",
  "message": "Données manquantes ou invalides",
  "code": 400
}
```

#### 401 Unauthorized

```json
{
  "error": "Unauthorized",
  "message": "Authentification requise",
  "code": 401
}
```

#### 403 Forbidden

```json
{
  "error": "Forbidden",
  "message": "Accès interdit",
  "code": 403
}
```

#### 404 Not Found

```json
{
  "error": "Not Found",
  "message": "Ressource non trouvée",
  "code": 404
}
```

#### 500 Internal Server Error

```json
{
  "error": "Internal Server Error",
  "message": "Une erreur interne du serveur s'est produite",
  "code": 500
}
```

---

## 🚀 Bonnes Pratiques

### Pour les Développeurs

1. **Authentification** :
   - Toujours vérifier l'authentification avec `@login_required`
   - Utiliser `@admin_required` pour les routes admin
   - Valider les permissions avant les opérations sensibles

2. **Validation des Données** :
   - Valider toutes les entrées utilisateur
   - Utiliser des types de données appropriés
   - Vérifier les contraintes (ex: `end_hour > start_hour`)

3. **Gestion des Erreurs** :
   - Retourner des codes HTTP appropriés
   - Inclure des messages d'erreur clairs
   - Logger les erreurs pour le débogage

4. **Performance** :
   - Utiliser `joinedload` pour éviter le problème N+1
   - Optimiser les requêtes de base de données
   - Limiter la taille des réponses

5. **Sécurité** :
   - Ne jamais exposer de données sensibles
   - Valider les tokens et permissions
   - Utiliser HTTPS en production

6. **Documentation** :
   - Documenter toutes les routes API
   - Inclure des exemples de requêtes et réponses
   - Maintenir la documentation à jour

### Pour les Clients API

1. **Authentification** :
   - Conserver le cookie de session pour les requêtes authentifiées
   - Utiliser les tokens ICS pour l'export sans session

2. **Gestion des Erreurs** :
   - Gérer tous les codes HTTP possibles
   - Afficher des messages d'erreur utilisateur
   - Implémenter des mécanismes de retry pour les erreurs temporaires

3. **Rate Limiting** :
   - Implémenter un rate limiting côté client
   - Respecter les limites de l'API

4. **Cache** :
   - Mettre en cache les réponses quand c'est approprié
   - Respecter les en-têtes Cache-Control

5. **Logging** :
   - Logger les requêtes et réponses pour le débogage
   - Ne pas logger de données sensibles

---

## 📝 Historique des Changements

| Version | Date | Auteur | Changements |
|---------|------|--------|-------------|
| 1.0.0 | Juin 2026 | Vibe Code | Création initiale de la documentation API |

---

## 📞 Contact

Pour toute question concernant l'API :
- Ouvrir une **Issue** sur GitHub
- Ouvrir une **Discussion** sur GitHub
- Contactez l'équipe via les canaux officiels

---

> **⚠️ Note importante** : Cette API est en développement actif. Les endpoints et les schémas de données peuvent changer sans préavis. Vérifiez régulièrement les mises à jour.

---

*Documentation générée pour Leviia Schedule - API REST*
