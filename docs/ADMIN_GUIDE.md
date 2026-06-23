# 🛡️ Guide Administrateur - Leviia Schedule

> **Version** : 1.0.0 | **Dernière mise à jour** : Juin 2026
> **Public** : Administrateurs Leviia Schedule uniquement

---

## 📋 Table des Matières

1. [🎯 Rôle de l'Administrateur](#-rôle-de-ladministrateur)
2. [🔐 Gestion de la Sécurité](#-gestion-de-la-sécurité)
3. [👥 Gestion Avancée des Utilisateurs](#-gestion-avancée-des-utilisateurs)
4. [🏢 Architecture des Groupes](#-architecture-des-groupes)
5. [⚙️ Configuration des Types de Shifts](#️-configuration-des-types-de-shifts)
6. [📊 Tableau de Bord et Statistiques](#-tableau-de-bord-et-statistiques)
7. [⚡ Automatisation Complète](#-automatisation-complète)
8. [🔧 Configuration Technique](#-configuration-technique)
9. [📤 Export et Intégrations](#-export-et-intégrations)
10. [🎨 Personnalisation](#-personnalisation)
11. [🔄 Maintenance et Sauvegardes](#-maintenance-et-sauvegardes)
12. [🚨 Gestion des Erreurs](#-gestion-des-erreurs)

---

## 🎯 Rôle de l'Administrateur

### Responsabilités

En tant qu'administrateur Leviia Schedule, vous êtes responsable de :

- ✅ **Gestion des utilisateurs** : Création, modification, suppression
- ✅ **Configuration des groupes** : Organisation et permissions
- ✅ **Paramétrage des shifts** : Types de shifts et règles métiers
- ✅ **Planification** : Shifts, astreintes, congés
- ✅ **Automatisation** : Configuration et supervision
- ✅ **Sécurité** : Gestion des accès et des permissions
- ✅ **Maintenance** : Sauvegardes et mises à jour

### Bonnes Pratiques

1. **Sécurité** : Changez toujours le mot de passe par défaut
2. **Sauvegardes** : Effectuez des sauvegardes régulières de la base de données
3. **Tests** : Testez les modifications dans un environnement de développement
4. **Documentation** : Documentez les configurations spécifiques
5. **Audit** : Vérifiez régulièrement les logs et les activités

---

## 🔐 Gestion de la Sécurité

### Sécurité des Comptes

#### Mot de passe par défaut

**⚠️ CRITIQUE** : Le compte administrateur par défaut a les identifiants :
- Email : `admin@leviia.local`
- Mot de passe : `admin123`

**Action immédiate** : Changez ce mot de passe dès la première connexion.

#### Politique de mots de passe

Recommandations :
- Minimum 12 caractères
- Mélange de majuscules, minuscules, chiffres et symboles
- Pas de mots du dictionnaire
- Unique pour chaque utilisateur

#### Réinitialisation des mots de passe

Pour réinitialiser le mot de passe d'un utilisateur :

1. Allez dans **Admin** > **Utilisateurs**
2. Cliquez sur **Modifier** pour l'utilisateur concerné
3. Entrez un nouveau mot de passe dans le champ **Mot de passe**
4. **Enregistrer**

> 💡 **Astuce** : Vous pouvez laisser le champ vide pour conserver le mot de passe actuel.

### Gestion des Permissions

#### Rôles

| Rôle | Accès |
|------|--------|
| **Administrateur** | Accès complet à toutes les fonctionnalités |
| **Utilisateur** | Accès limité à son propre planning et congés |

#### Permissions par groupe

| Permission | Description |
|------------|-------------|
| **Participe au planning** | Les membres peuvent avoir des shifts attribués |
| **Participe aux astreintes** | Les membres peuvent être en astreinte |

### Sécurité de l'Application

#### Variables d'environnement sensibles

| Variable | Sensibilité | Recommandation |
|----------|-------------|----------------|
| `SECRET_KEY` | ⭐⭐⭐⭐⭐ CRITIQUE | Générer une clé aléatoire de 32 octets |
| `SQLALCHEMY_DATABASE_URI` | ⭐⭐⭐⭐ Élevée | Utiliser des identifiants DB sécurisés |
| `LOGIN_DISABLED` | ⭐⭐⭐ Moyenne | Ne JAMAIS activer en production |

#### Générer une clé secrète sécurisée

```bash
# Méthode 1 : Python
python -c "import secrets; print(secrets.token_hex(32))"

# Méthode 2 : OpenSSL
openssl rand -hex 32
```

#### Désactiver l'authentification (DÉVELOPPEMENT UNIQUEMENT)

Dans `config.py` :
```python
LOGIN_DISABLED = True
```

> ⚠️ **DANGER** : Ne jamais utiliser cette option en production !

### Audit et Journalisation

#### Activer le logging avancé

Dans `config.py` :
```python
import logging
LOG_LEVEL = logging.DEBUG
```

#### Fichiers de log

Les logs sont disponibles dans la console. Pour les rediriger vers un fichier :

```bash
# Linux/macOS
python run.py > leviia.log 2>&1 &

# Windows
python run.py > leviia.log 2>&1
```

---

## 👥 Gestion Avancée des Utilisateurs

### Import/Export des Utilisateurs

> 📌 **Fonctionnalité à venir** : L'import/export CSV des utilisateurs sera disponible dans une future version.

### Gestion en Masse

#### Supprimer tous les utilisateurs d'un groupe

1. Allez dans **Admin** > **Utilisateurs**
2. Filtrez par groupe
3. Pour chaque utilisateur, cliquez sur **Supprimer**

> ⚠️ **Attention** : Vous devez d'abord supprimer les shifts, astreintes et congés associés.

#### Changer le groupe de plusieurs utilisateurs

1. Allez dans **Admin** > **Utilisateurs**
2. Cliquez sur **Modifier** pour chaque utilisateur
3. Changez le groupe
4. **Enregistrer**

### Utilisateurs Système

| Utilisateur | Rôle | Description |
|-------------|------|-------------|
| `admin@leviia.local` | Administrateur | Compte par défaut, doit être renommé |

### Bonnes Pratiques

1. **Nommage** : Utilisez des emails professionnels
2. **Groupes** : Organisez les utilisateurs par équipe/département
3. **Permissions** : Donnez uniquement les permissions nécessaires
4. **Audit** : Vérifiez régulièrement la liste des utilisateurs

---

## 🏢 Architecture des Groupes

### Stratégie de Groupement

#### Exemple 1 : Par Département

```
Groupe: Développement
├── Participe au planning: ✅
├── Participe aux astreintes: ✅
└── Utilisateurs: Jean, Marie, Pierre

Groupe: Support
├── Participe au planning: ✅
├── Participe aux astreintes: ✅
└── Utilisateurs: Sophie, Thomas

Groupe: Direction
├── Participe au planning: ❌
├── Participe aux astreintes: ❌
└── Utilisateurs: Monsieur Dupont
```

#### Exemple 2 : Par Type de Contrat

```
Groupe: Temps Plein
├── Participe au planning: ✅
├── Participe aux astreintes: ✅
└── Utilisateurs: ...

Groupe: Temps Partiel
├── Participe au planning: ✅
├── Participe aux astreintes: ❌
└── Utilisateurs: ...

Groupe: Stagiaires
├── Participe au planning: ✅
├── Participe aux astreintes: ❌
└── Utilisateurs: ...
```

### Migration des Utilisateurs

Pour déplacer un utilisateur vers un autre groupe :

1. Vérifiez que le nouveau groupe a les bonnes permissions
2. Allez dans **Admin** > **Utilisateurs**
3. Cliquez sur **Modifier** pour l'utilisateur
4. Changez le groupe
5. **Enregistrer**

> ⚠️ **Attention** : Si le nouvel groupe n'a pas la permission de participer au planning, l'utilisateur perdra ses shifts.

---

## ⚙️ Configuration des Types de Shifts

### Types de Shifts par Défaut

| Nom | Libellé | Heure Début | Heure Fin | Durée |
|-----|---------|--------------|-----------|-------|
| `morning` | Matin | 8h00 | 12h00 | 4h |
| `afternoon` | Après-midi | 12h00 | 18h00 | 6h |
| `evening` | Soirée | 18h00 | 22h00 | 4h |

### Créer un Type de Shift Personnalisé

#### Exemple 1 : Shift de Nuit

1. **Admin** > **Types de Shifts** > **Ajouter**
2. Nom : `night`
3. Libellé : `Nuit`
4. Heure de début : `22`
5. Heure de fin : `6`
6. **Enregistrer**

> ⚠️ **Attention** : Un shift qui passe minuit doit avoir une heure de fin > heure de début (ex: 22 à 6 = 22 à 30 pour 8h).

#### Exemple 2 : Shift Court

1. **Admin** > **Types de Shifts** > **Ajouter**
2. Nom : `short_morning`
3. Libellé : `Matin Court`
4. Heure de début : `9`
5. Heure de fin : `12`
6. **Enregistrer**

### Modifier un Type de Shift

1. **Admin** > **Types de Shifts**
2. Cliquez sur **Modifier** pour le type de shift
3. Modifiez les champs nécessaires
4. **Enregistrer**

> ⚠️ **Attention** : La modification d'un type de shift affecte tous les shifts existants qui l'utilisent.

### Supprimer un Type de Shift

1. **Admin** > **Types de Shifts**
2. Cliquez sur **Supprimer** pour le type de shift
3. Confirmez

> ⚠️ **Attention** : Vous ne pouvez pas supprimer un type de shift utilisé dans des shifts existants.

### Bonnes Pratiques

1. **Nommage** : Utilisez des noms courts et descriptifs (sans espaces)
2. **Libellés** : Utilisez des libellés clairs pour l'interface
3. **Chevauchement** : Évitez les chevauchements d'horaires
4. **Couverture** : Assurez-vous que tous les créneaux nécessaires sont couverts

---

## 📊 Tableau de Bord et Statistiques

### Vue d'Ensemble

Le tableau de bord administrateur affiche :

- **Utilisateurs** : Nombre total d'utilisateurs
- **Groupes** : Nombre total de groupes
- **Shifts** : Nombre total de shifts planifiés
- **Astreintes** : Nombre total d'astreintes
- **Congés** : Nombre total de congés

### Statistiques Avancées

> 📌 **À venir** : Des graphiques et rapports détaillés seront ajoutés.

### Accès Rapide

Depuis le tableau de bord, vous pouvez accéder à :
- **Utilisateurs** : Gestion complète des utilisateurs
- **Groupes** : Configuration des groupes
- **Types de Shifts** : Paramétrage des types de shifts
- **Automatisation** : Configuration de l'automatisation

---

## ⚡ Automatisation Complète

### Architecture de l'Automatisation

Leviia Schedule propose plusieurs niveaux d'automatisation :

```
┌─────────────────────────────────────────────────┐
│                AUTOMATISATION                     │
├─────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐          │
│  │  Astreintes   │    │    Shifts     │          │
│  │  (On-Call)    │    │              │          │
│  └──────────────┘    └──────────────┘          │
│         │                   │                 │
│         ▼                   ▼                 │
│  ┌─────────────────────────────────────────┐  │
│  │         Génération Complète              │  │
│  │   (Astreintes + Shifts en une fois)       │  │
│  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Configuration des Astreintes Automatiques

#### Étape 1 : Définir l'ordre de rotation

1. Allez dans **Admin** > **Automatisation** > **Génération complète**
2. Pour chaque utilisateur éligible :
   - ✅ **Inclure dans la rotation** : Cochez pour inclure
   - **Position** : Définissez l'ordre (1 = premier)
3. Cliquez sur **Enregistrer l'ordre**

Exemple d'ordre de rotation :
```
Position 1: Jean Dupont
Position 2: Marie Martin
Position 3: Pierre Durand
Position 4: Sophie Leroy
```

#### Étape 2 : Configurer la période

1. **Date de début** : Premier vendredi de la période
2. **Date de fin** : Dernier jour de la période
3. Cliquez sur **Simuler** pour prévisualiser

#### Étape 3 : Générer

1. Vérifiez le résultat de la simulation
2. Cliquez sur **Générer** pour créer les astreintes

### Configuration des Shifts Automatiques

#### Étape 1 : Définir les besoins quotidiens

1. Allez dans **Admin** > **Automatisation** > **Shifts**
2. Pour chaque jour (lundi à vendredi) :
   - **Matin** : Nombre de personnes nécessaires
   - **Après-midi** : Nombre de personnes nécessaires
   - **Soirée** : Nombre de personnes nécessaires

Exemple de configuration :
```
Lundi:
  - Matin: 2 personnes
  - Après-midi: 2 personnes
  - Soirée: 1 personne

Mardi à Vendredi: Même configuration
```

#### Étape 2 : Configurer la période

1. **Date de début** : Premier jour de la période
2. **Date de fin** : Dernier jour de la période
3. Cliquez sur **Simuler** pour prévisualiser

#### Étape 3 : Générer

1. Vérifiez le résultat de la simulation
2. Cliquez sur **Générer** pour créer les shifts

### Génération Complète (Astreintes + Shifts)

Pour générer tout en une seule opération :

1. Allez dans **Admin** > **Automatisation** > **Génération complète**
2. Configurez l'ordre de rotation des astreintes
3. Sélectionnez la période
4. Cliquez sur **Simuler**
5. Vérifiez que tout est correct
6. Cliquez sur **Générer**

> 💡 **Astuce** : La génération complète prend en compte les astreintes pour éviter les conflits avec les shifts.

### Rafraîchir les Shifts

Si vous avez modifié manuellement des astreintes :

1. Allez dans **Admin** > **Automatisation** > **Rafraîchir les shifts**
2. Sélectionnez la période à recalculer
3. Cliquez sur **Rafraîchir**

> ⚠️ **Attention** : Cette action supprimera tous les shifts existants pour la période sélectionnée !

### Règles Métiers

#### Règles par défaut pour les astreintes

```python
{
    "rotation_order": [1, 2, 3, 4],  # Ordre des utilisateurs
    "duration_days": 7,              # Durée en jours
    "start_hour": 21,               # Heure de début (21h = 9 PM)
    "end_hour": 7,                 # Heure de fin (7h = 7 AM)
    "start_day": 4                 # Jour de la semaine (4 = Vendredi)
}
```

#### Règles par défaut pour les shifts

```python
{
    "daily_requirements": {
        "monday": {"morning": 2, "afternoon": 2, "evening": 1},
        "tuesday": {"morning": 2, "afternoon": 2, "evening": 1},
        "wednesday": {"morning": 2, "afternoon": 2, "evening": 1},
        "thursday": {"morning": 2, "afternoon": 2, "evening": 1},
        "friday": {"morning": 2, "afternoon": 2, "evening": 1}
    },
    "weekend_excluded": True
}
```

### Personnalisation des Règles

Vous pouvez personnaliser les règles dans le fichier de configuration ou via l'interface d'automatisation.

---

## 🔧 Configuration Technique

### Fichier de Configuration

Le fichier `config.py` contient la configuration principale :

```python
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ta-cle-secrete-ici'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOGIN_DISABLED = False
```

### Variables d'Environnement

| Variable | Description | Valeur par défaut | Recommandation |
|----------|-------------|------------------|----------------|
| `SECRET_KEY` | Clé secrète pour la sécurité | Aléatoire | ⭐⭐⭐⭐⭐ Générer une clé forte |
| `SQLALCHEMY_DATABASE_URI` | URI de la base de données | `sqlite:///app.db` | Utiliser PostgreSQL en production |
| `LOGIN_DISABLED` | Désactive l'authentification | `False` | ❌ Ne JAMAIS activer en production |
| `LOG_LEVEL` | Niveau de journalisation | `INFO` | `DEBUG` pour le développement |

### Configuration de la Base de Données

#### SQLite (Par défaut)

```python
SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
```

- **Avantages** : Simple, pas de serveur requis
- **Inconvénients** : Pas adapté pour la production, pas de concurrency

#### PostgreSQL (Recommandé pour la production)

```python
SQLALCHEMY_DATABASE_URI = 'postgresql://user:password@localhost/leviia'
```

- **Avantages** : Robuste, scalable, support de la concurrency
- **Inconvénients** : Requiert un serveur PostgreSQL

#### MySQL/MariaDB

```python
SQLALCHEMY_DATABASE_URI = 'mysql://user:password@localhost/leviia'
```

- **À venir** : Support complet dans une future version

### Configuration du Serveur

#### Développement (Flask intégré)

```bash
python run.py
```

- **Port** : 5000
- **Host** : localhost
- **Debug** : Activé

#### Production (Gunicorn + Nginx)

1. Installer Gunicorn :
   ```bash
   pip install gunicorn
   ```

2. Créer un fichier `wsgi.py` :
   ```python
   from app import app
   
   if __name__ == "__main__":
       app.run()
   ```

3. Lancer Gunicorn :
   ```bash
   gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
   ```

4. Configurer Nginx comme reverse proxy

---

## 📤 Export et Intégrations

### Export ICS

#### Configuration

L'export ICS est disponible via l'URL :
```
/export/shifts?scope={scope}&token={token}
```

**Paramètres** :
- `scope` : `my` (planning personnel) ou `all` (tous les plannings)
- `token` : Token ICS de l'utilisateur

#### Générer un token ICS

1. **Admin** > **Utilisateurs** > Sélectionnez un utilisateur
2. **Profil** > **Token ICS**
3. **Générer un nouveau token**
4. Copiez le token

#### Intégration avec Google Calendar

1. Dans Google Calendar : **Paramètres** > **Ajouter un calendrier** > **À partir d'une URL**
2. Collez l'URL : `http://votre-serveur/export/shifts?scope=my&token=VOTRE_TOKEN`
3. **Ajouter un calendrier**

#### Intégration avec Outlook

1. Dans Outlook : **Fichier** > **Paramètres du compte** > **Paramètres du compte**
2. **Nouveau** > **Calendrier Internet**
3. Collez l'URL
4. **Suivant**

### API REST (À venir)

> 📌 **Fonctionnalité prévue** : Une API REST publique sera disponible dans la version 0.8.

### Webhooks (À venir)

> 📌 **Fonctionnalité prévue** : Les webhooks seront disponibles dans la version 0.8.

---

## 🎨 Personnalisation

### Personnalisation de l'Interface

#### Logo et Favicon

Remplacez les fichiers dans `app/templates/` :
- `favicon.ico` : Favicon de l'application
- (À venir) : Logo dans le header

#### CSS Personnalisé

1. Créez un fichier `app/static/css/custom.css`
2. Ajoutez vos styles personnalisés
3. Le fichier sera automatiquement chargé

### Personnalisation des Emails (À venir)

> 📌 **Fonctionnalité prévue** : La personnalisation des emails sera disponible dans la version 0.7.

### Personnalisation des Règles Métiers

Vous pouvez personnaliser les règles métiers dans :
- `app/utils/automation.py` : Règles d'automatisation
- `app/utils/helpers.py` : Fonctions de validation
- `app/utils/decorators.py` : Décorateurs personnalisés

---

## 🔄 Maintenance et Sauvegardes

### Sauvegarde de la Base de Données

#### SQLite

```bash
# Sauvegarder
cp instance/app.db instance/app.db.backup-$(date +%Y%m%d)

# Restaurer
cp instance/app.db.backup-20260615 instance/app.db
```

#### PostgreSQL

```bash
# Sauvegarder
pg_dump leviia > leviia-backup-$(date +%Y%m%d).sql

# Restaurer
psql leviia < leviia-backup-20260615.sql
```

### Sauvegarde Automatique

Créez un script de sauvegarde automatique :

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/leviia"
DATE=$(date +%Y%m%d)

mkdir -p $BACKUP_DIR
cp instance/app.db $BACKUP_DIR/app.db.backup-$DATE

# Garder seulement les 7 derniers jours
find $BACKUP_DIR -name "app.db.backup-*" -mtime +7 -delete
```

Puis ajoutez une tâche cron :

```bash
# Tous les jours à minuit
0 0 * * * /chemin/vers/backup.sh
```

### Mise à Jour de l'Application

1. Sauvegardez la base de données
2. Sauvegardez le fichier `config.py`
3. Mettez à jour le code :
   ```bash
   git pull origin main
   ```
4. Installez les nouvelles dépendances :
   ```bash
   pip install -r requirements.txt
   ```
5. Redémarrez l'application

### Nettoyage

#### Supprimer les données obsolètes

1. **Shifts passés** : Supprimez les shifts anciens pour améliorer les performances
2. **Astreintes passées** : Supprimez les astreintes terminées
3. **Congés passés** : Supprimez les congés terminés

#### Optimisation de la Base de Données

Pour SQLite :
```bash
# Réorganiser la base de données
sqlite3 instance/app.db "VACUUM;"
```

Pour PostgreSQL :
```bash
# Réorganiser et analyser
psql leviia -c "VACUUM ANALYZE;"
```

---

## 🚨 Gestion des Erreurs

### Erreurs Courantes et Solutions

#### Erreur : "Impossible de supprimer... des données sont associées"

**Cause** : Vous essayez de supprimer un élément qui a des dépendances.

**Solution** : Supprimez d'abord les données associées (shifts, astreintes, congés).

#### Erreur : "Format de date invalide"

**Cause** : La date n'est pas au format `AAAA-MM-JJ`.

**Solution** : Utilisez le format `2026-06-15`.

#### Erreur : "L'astreinte doit commencer un vendredi"

**Cause** : Vous essayez de créer une astreinte qui ne commence pas un vendredi.

**Solution** : Sélectionnez un vendredi comme date de début.

#### Erreur : "Email ou mot de passe incorrect"

**Cause** : Identifiants invalides.

**Solution** : Vérifiez votre email et mot de passe. Utilisez la réinitialisation si nécessaire.

#### Erreur 500 : Erreur serveur

**Cause** : Problème interne du serveur.

**Solution** :
1. Vérifiez les logs de l'application
2. Vérifiez que la base de données est accessible
3. Redémarrez l'application
4. Contactez le support si le problème persiste

### Logs et Dépannage

#### Activer le mode debug

Dans `run.py` :
```python
app.run(debug=True)
```

#### Voir les logs

```bash
# Lancer l'application avec logs
python run.py
```

#### Problèmes de Base de Données

**Symptôme** : L'application ne démarre pas, erreurs de connexion.

**Solutions** :
1. Vérifiez que le fichier `instance/app.db` existe
2. Vérifiez les permissions : `chmod 666 instance/app.db`
3. Vérifiez que SQLite est installé
4. Pour PostgreSQL, vérifiez que le serveur est en cours d'exécution

---

## 📚 Ressources pour Administrateurs

### Documentation

- [📖 Guide Utilisateur Complet](USER_GUIDE.md)
- [🚀 Guide de Démarrage Rapide](QUICK_START.md)
- [🗺️ Feuille de Route](ROADMAP.md)
- [📋 README Technique](../README.md)

### Outils

- **SQLite Browser** : [https://sqlitebrowser.org/](https://sqlitebrowser.org/)
- **PostgreSQL Admin** : pgAdmin, DBeaver
- **Monitoring** : Prometheus, Grafana (pour la production)

### Communautés

- **GitHub Issues** : [https://github.com/FoxOps/leviia-schedule/issues](https://github.com/FoxOps/leviia-schedule/issues)
- **GitHub Discussions** : [https://github.com/FoxOps/leviia-schedule/discussions](https://github.com/FoxOps/leviia-schedule/discussions)

---

## 📝 Checklist Administrateur

### Après l'Installation

- [ ] Changer le mot de passe administrateur par défaut
- [ ] Configurer les groupes nécessaires
- [ ] Ajouter les utilisateurs
- [ ] Configurer les types de shifts
- [ ] Tester l'application
- [ ] Configurer les sauvegardes automatiques

### Mensuellement

- [ ] Vérifier les sauvegardes
- [ ] Vérifier les logs pour les erreurs
- [ ] Mettre à jour l'application
- [ ] Vérifier l'espace disque
- [ ] Auditer les utilisateurs et permissions

### Trimestriellement

- [ ] Tester la restauration des sauvegardes
- [ ] Optimiser la base de données
- [ ] Revoir les règles d'automatisation
- [ ] Mettre à jour la documentation

---

## 📞 Support Administrateur

### Contacter le Support

1. **Issues GitHub** : Pour les bugs et demandes de fonctionnalités
2. **Discussions GitHub** : Pour les questions générales
3. **Documentation** : Consultez ce guide et les autres documents

### Informations à Fournir

Lors de la signalisation d'un problème, fournissez :
- Version de l'application
- Type de base de données
- Étapes pour reproduire
- Logs d'erreur
- Capture d'écran (si applicable)

---

> **⚠️ Rappel** : En tant qu'administrateur, vous êtes responsable de la sécurité et de la bonne utilisation de l'application.

---

*© 2026 Leviia Schedule - Tous droits réservés selon la licence CeCILL v2.1*
