# 📖 Guide Utilisateur Complet - Leviia Schedule

> **Version** : 1.0.0 - Documentation Utilisateur
> **Dernière mise à jour** : Juin 2026
> **Application** : Leviia Schedule v1.0.0 (Développement)

---

## 📋 Table des Matières

1. [🎯 Introduction](#-introduction)
2. [📥 Installation et Configuration](#-installation-et-configuration)
3. [🔐 Authentification](#-authentification)
4. [🏠 Interface Utilisateur](#-interface-utilisateur)
5. [👥 Gestion des Utilisateurs](#-gestion-des-utilisateurs)
6. [🏢 Gestion des Groupes](#-gestion-des-groupes)
7. [⚙️ Gestion des Types de Shifts](#️-gestion-des-types-de-shifts)
8. [📅 Gestion des Shifts](#-gestion-des-shifts)
9. [🚨 Gestion des Astreintes (On-Call)](#-gestion-des-astreintes-on-call)
10. [🏖️ Gestion des Congés](#-gestion-des-congés)
11. [📤 Export ICS et Intégration Calendrier](#-export-ics-et-intégration-calendrier)
12. [⚡ Automatisation Avancée](#-automatisation-avancée)
13. [📊 Tableau de Bord Administrateur](#-tableau-de-bord-administrateur)
14. [❓ FAQ et Dépannage](#-faq-et-dépannage)
15. [📞 Support et Contact](#-support-et-contact)

---

## 🎯 Introduction

### Qu'est-ce que Leviia Schedule ?

**Leviia Schedule** est une application web complète de gestion des plannings, des astreintes et des congés conçue pour les équipes et organisations. Elle permet de :

- ✅ **Gérer les utilisateurs** : Création, modification et organisation en groupes
- ✅ **Planifier les shifts** : Attribution des horaires de travail aux membres de l'équipe
- ✅ **Organiser les astreintes** : Planification des rotations d'astreinte (on-call)
- ✅ **Gérer les congés** : Saisie et visualisation des périodes d'absence
- ✅ **Exporter les données** : Intégration avec Google Calendar, Outlook, etc.
- ✅ **Automatiser** : Génération automatique des plannings selon des règles métiers

### Public Cible

- **Administrateurs** : Gestion complète de l'application, des utilisateurs et des configurations
- **Responsables d'équipe** : Planification des shifts et des astreintes
- **Utilisateurs standards** : Consultation de leur planning, gestion de leurs congés

### Prérequis Techniques

| Élément | Requirement |
|---------|-------------|
| **Navigateur** | Chrome, Firefox, Edge, Safari (versions récentes) |
| **JavaScript** | Activé |
| **Cookies** | Activés |
| **Résolution** | 1280x720 minimum (recommandé) |

---

## 📥 Installation et Configuration

### Installation Locale (Pour les développeurs)

#### 1. Cloner le dépôt

```bash
git clone https://github.com/FoxOps/leviia-schedule.git
cd leviia-schedule
```

#### 2. Créer un environnement virtuel

```bash
# Sur Linux/macOS
python -m venv venv
source venv/bin/activate

# Sur Windows
python -m venv venv
venv\Scripts\activate
```

#### 3. Installer les dépendances

```bash
pip install -r requirements.txt
python scripts/download_vendor_assets.py
```

#### 4. Configurer l'application

Copiez le fichier d'exemple, qui contient déjà des valeurs de
développement fonctionnelles (dont `DEFAULT_ADMIN_PASSWORD=admin123`,
sans quoi un mot de passe admin aléatoire non affiché serait généré) :

```bash
cp .env.example .env
```

Variables à connaître pour une première installation (toutes déjà
présentes dans `.env.example`, à ajuster si besoin) :

```bash
# Clé secrète (générer une nouvelle pour chaque installation)
SECRET_KEY=votre-cle-secrete-ici

# Configuration de la base de données (SQLite par défaut)
DATABASE_URL=sqlite:///app.db

# Désactiver l'authentification (UNIQUEMENT pour le développement)
LOGIN_DISABLED=false
```

Pour générer une clé secrète sécurisée :

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Liste complète des variables : voir
[`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md).

#### 5. Démarrer l'application

```bash
python run.py
```

> **Note** : La première exécution créera automatiquement (voir
> `run.py::create_default_data`) :
> - Un utilisateur administrateur par défaut
>   (email `DEFAULT_ADMIN_EMAIL`, mot de passe `DEFAULT_ADMIN_PASSWORD` —
>   `admin@leviia.local` / `admin123` avec les valeurs de `.env.example`)
> - Un groupe par défaut
> - Les types de shifts par défaut (matin, après-midi, soirée)

L'application sera accessible à l'adresse : **http://localhost:5000**

### Configuration Avancée

#### Utiliser PostgreSQL

1. Installez PostgreSQL et créez une base de données :
   ```bash
   sudo apt-get install postgresql postgresql-contrib
   sudo -u postgres createdb leviia
   sudo -u postgres createuser leviia_user
   ```

2. Modifiez la configuration dans `.env` :
   ```bash
   DATABASE_URL=postgresql://leviia_user:password@localhost/leviia
   ```

3. Installez le driver PostgreSQL :
   ```bash
   pip install psycopg2-binary
   ```

Voir aussi [`deployment/DEPLOYMENT_ADVANCED.md`](../deployment/DEPLOYMENT_ADVANCED.md)
pour une configuration PostgreSQL de production complète.

#### Variables d'environnement

| Variable | Description | Valeur par défaut |
|----------|-------------|------------------|
| `SECRET_KEY` | Clé secrète pour la sécurité | Générée aléatoirement si absente |
| `DATABASE_URL` | URI de la base de données | `sqlite:///app.db` |
| `LOGIN_DISABLED` | Désactive l'authentification (dev uniquement) | `false` |
| `LOG_LEVEL` | Niveau de journalisation | `INFO` |

Liste complète : [`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md).

---

## 🔐 Authentification

### Première Connexion

1. Accédez à l'application via votre navigateur : **http://localhost:5000**
2. Connectez-vous avec les identifiants par défaut :
   - **Email** : `admin@leviia.local`
   - **Mot de passe** : `admin123`

> ⚠️ **IMPORTANT** : Changez immédiatement le mot de passe après la première connexion.

### Connexion

1. Cliquez sur le lien **"Connexion"** ou accédez directement à `/login`
2. Entrez votre email et votre mot de passe
3. Cliquez sur **"Se connecter"**
4. Cochez **"Se souvenir de moi"** pour rester connecté (optionnel)

### Déconnexion

1. Cliquez sur votre nom d'utilisateur dans le menu de navigation
2. Sélectionnez **"Déconnexion"**

### Mot de passe oublié

> ⚠️ **Fonctionnalité non implémentée** : Contactez l'administrateur pour réinitialiser votre mot de passe.

### Gestion du Profil

#### Consulter son profil

1. Cliquez sur votre nom d'utilisateur dans le menu
2. Sélectionnez **"Profil"**
3. Vous verrez vos informations personnelles :
   - Nom
   - Email
   - Groupe
   - Rôle (Administrateur/Utilisateur)

#### Mettre à jour son profil

1. Allez dans **"Profil"** > **"Modifier le profil"**
2. Modifiez les champs souhaités :
   - **Nom** : Votre nom complet
   - **Email** : Votre adresse email
   - **Mot de passe actuel** : Obligatoire pour changer de mot de passe
   - **Nouveau mot de passe** : Nouveau mot de passe (optionnel)
   - **Confirmer le mot de passe** : Confirmation du nouveau mot de passe
3. Cliquez sur **"Enregistrer"**

#### Générer un Token ICS

Pour exporter votre planning vers un calendrier externe :

1. Allez dans **"Profil"** > **"Token ICS"**
2. Cliquez sur **"Générer un nouveau token"**
3. Copiez le token généré
4. Utilisez-le dans l'URL d'export : `/export/shifts?scope=my&token=VOTRE_TOKEN`

> 💡 **Conseil** : Gardez votre token secret. Il permet d'accéder à vos données de planning.

---

## 🏠 Interface Utilisateur

### Structure de l'interface

```
┌─────────────────────────────────────────────────────────────┐
│  🔹 Leviia Schedule    [Accueil] [Planning] [Astreintes] [Congés] │
├─────────────────────────────────────────────────────────────┤
│  🏠 Accueil │ 📅 Planning │ 🚨 Astreintes │ 🏖️ Congés          │
├─────────────────────────────────────────────────────────────┤
│                                                                 │
│                    CONTENU PRINCIPAL                           │
│                                                                 │
├─────────────────────────────────────────────────────────────┤
│  © 2026 Leviia Schedule | Utilisateur: Jean Dupont [Déconnexion]│
└─────────────────────────────────────────────────────────────┘
```

### Menu de Navigation

| Élément | Description | Accès |
|---------|-------------|-------|
| **Accueil** | Tableau de bord avec calendrier | Tous |
| **Planning** | Liste et gestion des shifts | Tous |
| **Astreintes** | Liste et gestion des astreintes | Tous |
| **Congés** | Liste et gestion des congés | Tous |
| **Admin** | Tableau de bord administrateur | Admin seulement |

### Barre d'outils

- **Notifications** : Affiche les messages et alertes
- **Profil** : Accès à votre profil utilisateur
- **Déconnexion** : Quitter l'application

---

## 👥 Gestion des Utilisateurs

> ⚠️ **Réservé aux administrateurs**

### Lister les utilisateurs

1. Allez dans **Admin** > **Utilisateurs**
2. Vous verrez la liste de tous les utilisateurs avec :
   - Nom
   - Email
   - Groupe
   - Rôle (Admin/Utilisateur)
   - Nombre de shifts, astreintes et congés
3. Utilisez la barre de recherche pour filtrer les utilisateurs

### Ajouter un utilisateur

1. Allez dans **Admin** > **Utilisateurs** > **Ajouter**
2. Remplissez le formulaire :
   - **Nom** (obligatoire) : Nom complet de l'utilisateur
   - **Email** (obligatoire) : Adresse email unique
   - **Groupe** (obligatoire) : Sélectionnez un groupe existant
   - **Mot de passe** (optionnel) : Laissez vide pour un mot de passe par défaut (`password123`)
   - **Administrateur** : Cochez pour donner les droits admin
3. Cliquez sur **"Enregistrer"**

> 💡 **Conseil** : Si vous ne spécifiez pas de mot de passe, l'utilisateur devra le changer à sa première connexion.

### Modifier un utilisateur

1. Allez dans **Admin** > **Utilisateurs**
2. Cliquez sur l'icône **✏️ Modifier** à côté de l'utilisateur
3. Modifiez les champs souhaités
4. Cliquez sur **"Enregistrer"**

### Supprimer un utilisateur

1. Allez dans **Admin** > **Utilisateurs**
2. Cliquez sur l'icône **🗑️ Supprimer** à côté de l'utilisateur
3. Confirmez la suppression

> ⚠️ **Attention** : Vous ne pouvez pas supprimer un utilisateur qui a des shifts, astreintes ou congés associés. Supprimez d'abord ses données.

---

## 🏢 Gestion des Groupes

> ⚠️ **Réservé aux administrateurs**

### À quoi servent les groupes ?

Les groupes permettent de :
- Organiser les utilisateurs par équipe ou département
- Appliquer des règles spécifiques à certains groupes
- Contrôler quels utilisateurs participent aux shifts et aux astreintes

### Lister les groupes

1. Allez dans **Admin** > **Groupes**
2. Vous verrez la liste de tous les groupes avec :
   - Nom
   - Participation au planning (Shifts)
   - Participation aux astreintes
   - Nombre d'utilisateurs

### Ajouter un groupe

1. Allez dans **Admin** > **Groupes** > **Ajouter**
2. Remplissez le formulaire :
   - **Nom** (obligatoire) : Nom du groupe
   - **Participe au planning** : Cochez si les membres peuvent avoir des shifts
   - **Participe aux astreintes** : Cochez si les membres peuvent être en astreinte
3. Cliquez sur **"Enregistrer"**

### Modifier un groupe

1. Allez dans **Admin** > **Groupes**
2. Cliquez sur l'icône **✏️ Modifier** à côté du groupe
3. Modifiez les champs souhaités
4. Cliquez sur **"Enregistrer"**

### Supprimer un groupe

1. Allez dans **Admin** > **Groupes**
2. Cliquez sur l'icône **🗑️ Supprimer** à côté du groupe
3. Confirmez la suppression

> ⚠️ **Attention** : Vous ne pouvez pas supprimer un groupe qui contient des utilisateurs. Déplacez d'abord les utilisateurs vers un autre groupe.

---

## ⚙️ Gestion des Types de Shifts

> ⚠️ **Réservé aux administrateurs**

### Qu'est-ce qu'un type de shift ?

Un type de shift définit :
- Un nom unique (ex: `morning`, `afternoon`, `evening`)
- Un libellé affiché (ex: "Matin", "Après-midi", "Soirée")
- Une heure de début (ex: 8 pour 8h00)
- Une heure de fin (ex: 12 pour 12h00)

### Types de shifts par défaut

L'application crée automatiquement 3 types de shifts :

| Nom | Libellé | Heure de début | Heure de fin |
|-----|---------|----------------|--------------|
| `morning` | Matin | 8h00 | 12h00 |
| `afternoon` | Après-midi | 12h00 | 18h00 |
| `evening` | Soirée | 18h00 | 22h00 |

### Lister les types de shifts

1. Allez dans **Admin** > **Types de Shifts**
2. Vous verrez la liste de tous les types de shifts configurés

### Ajouter un type de shift

1. Allez dans **Admin** > **Types de Shifts** > **Ajouter**
2. Remplissez le formulaire :
   - **Nom** (obligatoire) : Identifiant unique (sans espaces, ex: `night`)
   - **Libellé** (obligatoire) : Nom affiché (ex: "Nuit")
   - **Heure de début** (obligatoire) : Heure entre 0 et 23
   - **Heure de fin** (obligatoire) : Heure entre 0 et 23, doit être > heure de début
3. Cliquez sur **"Enregistrer"**

### Modifier un type de shift

1. Allez dans **Admin** > **Types de Shifts**
2. Cliquez sur l'icône **✏️ Modifier** à côté du type de shift
3. Modifiez les champs souhaités
4. Cliquez sur **"Enregistrer"**

### Supprimer un type de shift

1. Allez dans **Admin** > **Types de Shifts**
2. Cliquez sur l'icône **🗑️ Supprimer** à côté du type de shift
3. Confirmez la suppression

> ⚠️ **Attention** : Vous ne pouvez pas supprimer un type de shift qui est utilisé dans des shifts existants. Supprimez d'abord les shifts qui l'utilisent.

---

## 📅 Gestion des Shifts

### Qu'est-ce qu'un shift ?

Un shift représente une période de travail attribuée à un utilisateur pour une journée spécifique. Il contient :
- Un utilisateur
- Un type de shift (matin, après-midi, soirée)
- Une date
- Une heure de début et de fin

### Visualiser le planning

#### Méthode 1 : Calendrier interactif (Page d'accueil)

1. Allez sur la page **Accueil**
2. Vous verrez un calendrier avec :
   - **Shifts** : Affichés en bleu
   - **Astreintes** : Affichées en rouge
   - **Congés** : Affichés en vert
3. Naviguez entre les mois en utilisant les flèches
4. Cliquez sur un événement pour plus de détails

#### Méthode 2 : Liste des shifts

1. Allez dans **Planning**
2. Vous verrez la liste de tous les shifts avec :
   - Date
   - Utilisateur
   - Type de shift
   - Heure de début et de fin
3. Utilisez la pagination pour naviguer
4. Utilisez le filtre de recherche pour trouver des shifts spécifiques

### Ajouter un shift (Administrateur)

1. Allez dans **Planning** > **Ajouter un shift**
2. Remplissez le formulaire :
   - **Utilisateur** (obligatoire) : Sélectionnez un utilisateur éligible
   - **Type de shift** (obligatoire) : Sélectionnez un type de shift
   - **Date de début** (obligatoire) : Date de début de la période
   - **Date de fin** (obligatoire) : Date de fin de la période
3. Cliquez sur **"Enregistrer"**

> 💡 **Astuce** : Vous pouvez ajouter des shifts pour une période de plusieurs jours. L'application créera automatiquement un shift pour chaque jour ouvré (lundi-vendredi) dans la période.

### Ajouter un shift pour un seul jour

1. Allez dans **Planning** > **Ajouter un shift**
2. Sélectionnez la même date pour le début et la fin
3. Choisissez l'utilisateur et le type de shift
4. Cliquez sur **"Enregistrer"**

### Modifier un shift

**Administrateur uniquement.** Sur le calendrier de la page d'accueil,
activez le **mode édition** puis glissez-déposez le shift vers sa
nouvelle date/heure, ou redimensionnez-le pour changer sa durée. Le
changement est enregistré immédiatement (pas de bouton "Enregistrer"
séparé).

Il n'existe pas de formulaire de modification dédié (pas de page
"Modifier ce shift") — seul le glisser-déposer sur le calendrier permet
une modification directe. Sinon, supprimez le shift et créez-en un
nouveau via **Planning > Ajouter un shift**.

### Supprimer un shift

1. Allez dans **Planning**
2. Trouvez le shift à supprimer
3. Cliquez sur l'icône **🗑️ Supprimer**
4. Confirmez la suppression

### Supprimer plusieurs shifts

#### Supprimer tous les shifts d'un utilisateur

1. Allez dans **Planning**
2. Cliquez sur **"Supprimer tous les shifts de [Nom]"**
3. Confirmez la suppression

#### Supprimer tous les shifts d'une journée

1. Allez dans **Planning**
2. Cliquez sur **"Supprimer tous les shifts du [Date]"**
3. Confirmez la suppression

#### Supprimer tous les shifts d'une semaine

1. Allez dans **Planning**
2. Cliquez sur **"Supprimer tous les shifts de la semaine du [Date]"**
3. Confirmez la suppression

#### Supprimer TOUS les shifts

1. Allez dans **Planning**
2. Cliquez sur **"Supprimer tous les shifts"**
3. Confirmez la suppression

> ⚠️ **Attention** : Cette action est irréversible !

---

## 🚨 Gestion des Astreintes (On-Call)

### Qu'est-ce qu'une astreinte ?

Une astreinte (on-call) est une période pendant laquelle un utilisateur est responsable et joignable en dehors des heures de travail normales. Dans Leviia Schedule :

- Les astreintes commencent **le vendredi à 21h00**
- Les astreintes se terminent **le vendredi suivant à 07h00** (soit 7 jours - 14 heures)
- Chaque utilisateur éligible peut être en astreinte

### Visualiser les astreintes

#### Méthode 1 : Calendrier interactif (Page d'accueil)

1. Allez sur la page **Accueil**
2. Les astreintes sont affichées en **rouge** dans le calendrier
3. Passez votre souris sur une astreinte pour voir les détails

#### Méthode 2 : Liste des astreintes

1. Allez dans **Astreintes**
2. Vous verrez la liste de toutes les astreintes avec :
   - Période (date de début à date de fin)
   - Utilisateur responsable
   - Durée
3. Utilisez la pagination pour naviguer

### Ajouter une astreinte (Administrateur)

1. Allez dans **Astreintes** > **Ajouter une astreinte**
2. Remplissez le formulaire :
   - **Utilisateur** (obligatoire) : Sélectionnez un utilisateur éligible (membre d'un groupe participant aux astreintes)
   - **Date de début** (obligatoire) : **Doit être un vendredi** (l'application vérifie cela)
3. Cliquez sur **"Enregistrer"**

> 💡 **Astuce** : L'application calcule automatiquement la date de fin (7 jours après le vendredi 21h00, soit le vendredi suivant à 07h00).

### Modifier une astreinte

**Administrateur uniquement.** Comme pour les shifts : activez le mode
édition sur le calendrier de la page d'accueil, puis glissez-déposez
l'astreinte. Pas de formulaire de modification dédié — sinon, supprimez
et recréez-la via **Astreintes > Ajouter une astreinte**.

### Supprimer une astreinte

1. Allez dans **Astreintes**
2. Trouvez l'astreinte à supprimer
3. Cliquez sur l'icône **🗑️ Supprimer**
4. Confirmez la suppression

### Supprimer plusieurs astreintes

#### Supprimer toutes les astreintes d'un utilisateur

1. Allez dans **Astreintes**
2. Cliquez sur **"Supprimer toutes les astreintes de [Nom]"**
3. Confirmez la suppression

#### Supprimer TOUTES les astreintes

1. Allez dans **Astreintes**
2. Cliquez sur **"Supprimer toutes les astreintes"**
3. Confirmez la suppression

> ⚠️ **Attention** : Cette action est irréversible !

---

## 🏖️ Gestion des Congés

### Qu'est-ce qu'un congé ?

Un congé représente une période d'absence d'un utilisateur. Il peut s'agir de :
- Congés payés
- Congés maladie
- RTT
- Autres types d'absences

### Visualiser les congés

#### Méthode 1 : Calendrier interactif (Page d'accueil)

1. Allez sur la page **Accueil**
2. Les congés sont affichés en **vert** dans le calendrier
3. Passez votre souris sur un congé pour voir les détails

#### Méthode 2 : Liste des congés

1. Allez dans **Congés**
2. Vous verrez la liste de tous les congés avec :
   - Période (date de début à date de fin)
   - Utilisateur
   - Durée
3. Utilisez la pagination pour naviguer

### Ajouter un congé

#### Pour soi-même (Tous les utilisateurs)

1. Allez dans **Congés** > **Ajouter un congé**
2. Remplissez le formulaire :
   - **Utilisateur** : Votre nom (préselectionné)
   - **Date de début** (obligatoire) : Première journée de congé
   - **Date de fin** (obligatoire) : Dernière journée de congé
3. Cliquez sur **"Enregistrer"**

#### Pour un autre utilisateur (Administrateur)

1. Allez dans **Congés** > **Ajouter un congé**
2. Sélectionnez l'utilisateur concerné
3. Remplissez les dates de début et de fin
4. Cliquez sur **"Enregistrer"**

> ⚠️ **Restriction** : Les utilisateurs non-administrateurs ne peuvent ajouter des congés que pour eux-mêmes.

### Règles de validation des congés

L'application vérifie automatiquement :
- ✅ La date de début doit être antérieure ou égale à la date de fin
- ❌ Impossible d'ajouter un congé qui chevauche un **autre congé existant**
  du même utilisateur

Aucune autre restriction n'est appliquée par l'application : les congés
dans le passé sont acceptés, et un congé peut tout à fait chevaucher un
shift ou une astreinte déjà planifiés.

> 💡 **Important** : si un congé chevauche des shifts existants,
> l'application **rééquilibre automatiquement le planning** (les shifts
> concernés sont recalculés/réassignés) plutôt que de bloquer la
> création du congé. Un message indique le nombre de shifts recalculés
> après l'ajout.

### Modifier un congé

Le glisser-déposer sur le calendrier (mode édition) n'est activé que
pour les administrateurs, y compris pour les congés d'un utilisateur
normal. Il n'y a pas de formulaire de modification dédié : pour changer
les dates d'un congé, supprimez-le et créez-en un nouveau via
**Congés > Ajouter un congé**.

### Supprimer un congé

1. Allez dans **Congés**
2. Trouvez le congé à supprimer
3. Cliquez sur l'icône **🗑️ Supprimer**
4. Confirmez la suppression

> ⚠️ **Restriction** : Vous ne pouvez supprimer que vos propres congés, sauf si vous êtes administrateur.

---

## 📤 Export ICS et Intégration Calendrier

### Qu'est-ce que l'export ICS ?

Le format **iCalendar (ICS)** est un standard pour échanger des informations de calendrier. Il permet d'importer vos plannings Leviia Schedule dans :
- Google Calendar
- Microsoft Outlook
- Apple Calendar
- Mozilla Thunderbird
- Et bien d'autres...

### Exporter votre planning personnel

#### Étape 1 : Générer un token ICS

1. Connectez-vous à Leviia Schedule
2. Allez dans **Profil** > **Token ICS**
3. Cliquez sur **"Générer un nouveau token"**
4. Copiez le token généré

#### Étape 2 : Obtenir l'URL d'export

Votre URL d'export personnelle est :
```
http://votre-serveur:5000/export/shifts?scope=my&token=VOTRE_TOKEN
```

Remplacez :
- `votre-serveur` : L'adresse de votre instance Leviia Schedule
- `VOTRE_TOKEN` : Le token que vous avez généré

### Exporter d'autres données

Leviia Schedule permet également d'exporter :

#### Exporter les astreintes
```
http://votre-serveur:5000/export/oncall?scope=my&token=VOTRE_TOKEN
```

#### Exporter les congés
```
http://votre-serveur:5000/export/leaves?scope=my&token=VOTRE_TOKEN
```

#### Exporter tout (Administrateur)
```
# Tous les shifts
http://votre-serveur:5000/export/shifts?scope=all&token=VOTRE_TOKEN_ADMIN

# Toutes les astreintes
http://votre-serveur:5000/export/oncall?scope=all&token=VOTRE_TOKEN_ADMIN

# Tous les congés
http://votre-serveur:5000/export/leaves?scope=all&token=VOTRE_TOKEN_ADMIN
```

#### Étape 3 : Importer dans votre calendrier

##### Google Calendar

1. Ouvrez Google Calendar
2. Cliquez sur l'icône **⚙️ Paramètres** (en haut à droite)
3. Sélectionnez **"Paramètres"**
4. Allez dans **"Calendriers"** > **"Ajouter un calendrier"** > **"À partir d'une URL"**
5. Collez votre URL d'export Leviia Schedule
6. Cliquez sur **"Ajouter un calendrier"**

> 💡 **Astuce** : Les mises à jour de votre planning Leviia Schedule seront automatiquement synchronisées avec Google Calendar (toutes les 12 heures par défaut).

##### Microsoft Outlook

1. Ouvrez Outlook
2. Allez dans **Fichier** > **Paramètres du compte** > **Paramètres du compte**
3. Cliquez sur **"Nouveau"** > **"Calendrier Internet"**
4. Collez votre URL d'export Leviia Schedule
5. Cliquez sur **"Suivant"** et suivez les instructions

##### Apple Calendar (macOS)

1. Ouvrez l'application Calendrier
2. Allez dans **Fichier** > **Nouveau calendrier** > **Calendrier par abonnement**
3. Collez votre URL d'export Leviia Schedule
4. Cliquez sur **"S'abonner"**

### Exporter tous les plannings (Administrateur)

En tant qu'administrateur, vous pouvez exporter les plannings de tous les utilisateurs :

```
http://votre-serveur:5000/export/shifts?scope=all&token=VOTRE_TOKEN_ADMIN
```

> ⚠️ **Attention** : Cette URL donne accès à TOUS les plannings. Gardez-la secrète !

### Mise à jour automatique

Les fichiers ICS sont générés dynamiquement à chaque requête. Cela signifie que :
- ✅ Les modifications sont immédiatement visibles
- ✅ Pas besoin de régénérer manuellement le fichier
- ✅ Votre calendrier externe reste toujours à jour

### Problèmes courants

| Problème | Solution |
|----------|----------|
| Le calendrier ne se met pas à jour | Attendez 12-24h ou forcez la synchronisation dans votre application de calendrier |
| L'URL ne fonctionne pas | Vérifiez que votre token est correct et que vous êtes connecté |
| Erreur d'authentification | Régénérez votre token ICS |
| Aucun événement n'apparaît | Vérifiez que vous avez des shifts, astreintes ou congés planifiés |

---

## ⚡ Automatisation Avancée

> ⚠️ **Réservé aux administrateurs**

### Introduction à l'automatisation

Leviia Schedule propose un système d'automatisation puissant pour générer automatiquement :
- **Les astreintes** : Selon un ordre de rotation personnalisable
- **Les shifts** : Selon des règles métiers configurables

### Tableau de bord de l'automatisation

1. Allez dans **Admin** > **Automatisation**
2. Vous verrez :
   - L'état actuel de l'automatisation
   - Le nombre de shifts et astreintes générés
   - Les utilisateurs éligibles
   - Les règles actuelles

### Génération automatique des astreintes

#### Configurer l'ordre de rotation

1. Allez dans **Admin** > **Automatisation** > **Génération complète**
2. Vous verrez la liste des utilisateurs éligibles aux astreintes
3. Pour chaque utilisateur :
   - **Inclure dans la rotation** : Cochez pour inclure l'utilisateur
   - **Position** : Définissez l'ordre de passage (1 = premier, 2 = deuxième, etc.)
4. Cliquez sur **"Enregistrer l'ordre"** pour sauvegarder

#### Générer des astreintes automatiquement

1. Allez dans **Admin** > **Automatisation** > **Génération complète**
2. Sélectionnez la période :
   - **Date de début** : Premier vendredi de la période
   - **Date de fin** : Dernier jour de la période
3. Cliquez sur **"Simuler"** pour voir un aperçu (dry run)
4. Vérifiez que le résultat vous convient
5. Cliquez sur **"Générer"** pour créer les astreintes

> 💡 **Astuce** : Utilisez toujours le mode **"Simuler"** avant de générer pour vérifier que la configuration est correcte.

### Génération automatique des shifts

#### Configurer les règles de shifts

1. Allez dans **Admin** > **Automatisation** > **Shifts**
2. Configurez les besoins quotidiens :
   - **Lundi** : Nombre de personnes par type de shift
   - **Mardi** : Nombre de personnes par type de shift
   - **Mercredi** : Nombre de personnes par type de shift
   - **Jeudi** : Nombre de personnes par type de shift
   - **Vendredi** : Nombre de personnes par type de shift
3. Pour chaque jour et chaque type de shift (matin, après-midi, soirée), indiquez le nombre de personnes nécessaires

Exemple de configuration :
```
Lundi :
  - Matin : 2 personnes
  - Après-midi : 2 personnes
  - Soirée : 1 personne

Mardi :
  - Matin : 2 personnes
  - Après-midi : 2 personnes
  - Soirée : 1 personne
```

#### Générer des shifts automatiquement

1. Allez dans **Admin** > **Automatisation** > **Shifts**
2. Sélectionnez la période :
   - **Date de début** : Premier jour de la période
   - **Date de fin** : Dernier jour de la période
3. Cliquez sur **"Simuler"** pour voir un aperçu
4. Vérifiez que le résultat vous convient
5. Cliquez sur **"Générer"** pour créer les shifts

### Génération complète (Astreintes + Shifts)

Pour générer à la fois les astreintes et les shifts en une seule opération :

1. Allez dans **Admin** > **Automatisation** > **Génération complète**
2. Configurez l'ordre de rotation des astreintes
3. Sélectionnez la période
4. Cliquez sur **"Simuler"** pour voir un aperçu
5. Cliquez sur **"Générer"** pour créer les astreintes et les shifts

> 💡 **Astuce** : La génération complète prend en compte les astreintes pour éviter les conflits avec les shifts.

### Rafraîchir les shifts existants

Si vous avez modifié manuellement des astreintes et que vous souhaitez recalculer les shifts :

1. Allez dans **Admin** > **Automatisation** > **Rafraîchir les shifts**
2. Sélectionnez la période à recalculer
3. Cliquez sur **"Rafraîchir"**
4. L'application supprimera les shifts existants pour la période et les recréera

> ⚠️ **Attention** : Cette action supprimera tous les shifts existants pour la période sélectionnée !

### Règles métiers par défaut

Leviia Schedule utilise les règles suivantes par défaut :

#### Pour les astreintes :
- Rotation dans l'ordre de la liste des utilisateurs éligibles
- Chaque astreinte dure 7 jours (du vendredi 21h au vendredi suivant 07h)
- Un utilisateur ne peut pas être en astreinte deux semaines de suite

#### Pour les shifts :
- 2 personnes par shift (matin, après-midi, soirée)
- Du lundi au vendredi uniquement
- Répartition équitable entre les utilisateurs éligibles
- Respect des congés et des astreintes

---

## 📊 Tableau de Bord Administrateur

> ⚠️ **Réservé aux administrateurs**

### Accéder au tableau de bord

1. Connectez-vous avec un compte administrateur
2. Cliquez sur **Admin** dans le menu de navigation

### Vue d'ensemble

Le tableau de bord affiche :
- **Nombre d'utilisateurs** : Total des utilisateurs enregistrés
- **Nombre de groupes** : Total des groupes créés
- **Nombre de shifts** : Total des shifts planifiés
- **Nombre d'astreintes** : Total des astreintes planifiées
- **Nombre de congés** : Total des congés enregistrés

### Statistiques avancées

> 📌 **À venir** : Des graphiques et statistiques détaillées seront ajoutés dans les prochaines versions.

### Gestion rapide

Depuis le tableau de bord, vous pouvez accéder rapidement à :
- **Utilisateurs** : Gérer les comptes utilisateurs
- **Groupes** : Gérer les groupes d'utilisateurs
- **Types de Shifts** : Configurer les types de shifts
- **Automatisation** : Configurer et lancer l'automatisation

---

## ❓ FAQ et Dépannage

Déplacé dans un document dédié : [`FAQ.md`](FAQ.md) (questions
fréquentes, messages d'erreur courants, problèmes techniques).

---

## 📞 Support et Contact

### Obtenir de l'aide

1. **Consultez ce guide** : La plupart des questions sont répondues ici
2. **Vérifiez les FAQ** : Section dédiée aux questions fréquentes
3. **Contactez votre administrateur** : Pour les problèmes spécifiques à votre instance

### Signaler un bug

Pour signaler un bug :

1. **Vérifiez qu'il n'est pas déjà signalé** : Consultez les [Issues GitHub](https://github.com/FoxOps/leviia-schedule/issues)
2. **Préparez les informations suivantes** :
   - Version de l'application
   - Étapes pour reproduire le bug
   - Comportement attendu
   - Comportement réel
   - Captures d'écran (si applicable)
   - Logs d'erreur (si applicable)
3. **Ouvrez une Issue** : [Créer une nouvelle Issue](https://github.com/FoxOps/leviia-schedule/issues/new)

### Demander une fonctionnalité

Pour demander une nouvelle fonctionnalité :

1. **Vérifiez qu'elle n'est pas déjà prévue** : Consultez la [Feuille de Route](../../ROADMAP.md)
2. **Ouvrez une Discussion** : [Créer une nouvelle Discussion](https://github.com/FoxOps/leviia-schedule/discussions/new)
3. **Décrivez votre besoin** : Expliquez en détail la fonctionnalité souhaitée et son utilité

### Contribuer au projet

Les contributions sont les bienvenues ! Voir la section "Contribution" du
[README](../../README.md#-contribution) pour la marche à suivre (fork,
branche, commit, Pull Request).

---

## 📚 Ressources Additionnelles

- [README.md](../../README.md) - Documentation technique et installation
- [ROADMAP.md](../../ROADMAP.md) - Feuille de route du développement
- [Rapport Phase 4 : Amélioration des tests](../../report/Phase%204%3A%20AM%C3%89LIORATION%20DES%20TESTS.md) - État des tests et de la couverture
- [LICENSE](../../LICENSE) - Licence CeCILL v2.1
- [Dépôt GitHub](https://github.com/FoxOps/leviia-schedule) - Code source et issues

---

## 📝 Historique des Versions

| Version | Date | Auteur | Changements |
|---------|------|--------|-------------|
| 1.0.0 | Juin 2026 | Vibe Code | Création initiale du guide utilisateur |

---

> **⚠️ Rappel : Version de développement**
> Ce logiciel est fourni "tel quel", sans garantie d'aucune sorte.
> **Utilisez-le à vos propres risques.**

---

*Document généré pour Leviia Schedule - Tous droits réservés selon la licence CeCILL v2.1*
