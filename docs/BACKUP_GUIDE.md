# Guide de Sauvegarde Automatique - Leviia Schedule

> **📖 Documentation complète pour la sauvegarde de la base de données**

Ce guide explique comment configurer et utiliser le système de sauvegarde automatique pour Leviia Schedule.

## 📋 Table des matières

1. [Introduction](#-introduction)
2. [Fonctionnalités](#-fonctionnalités)
3. [Prérequis](#-prérequis)
4. [Installation](#-installation)
5. [Configuration](#-configuration)
   - [Variables d'environnement](#variables-denvironnement)
   - [Fichier de configuration JSON](#fichier-de-configuration-json)
   - [Configuration pour AWS S3](#configuration-pour-aws-s3)
   - [Configuration pour MinIO](#configuration-pour-minio)
6. [Utilisation](#-utilisation)
   - [Sauvegarde locale](#sauvegarde-locale)
   - [Sauvegarde S3](#sauvegarde-s3)
   - [Sauvegarde complète](#sauvegarde-complète)
   - [Liste des sauvegardes](#liste-des-sauvegardes)
   - [Restauration](#restauration)
   - [Nettoyage](#nettoyage)
7. [Automatisation avec Cron](#-automatisation-avec-cron)
8. [Automatisation avec Systemd](#-automatisation-avec-systemd)
9. [Sécurité](#-sécurité)
10. [Dépannage](#-dépannage)
11. [Exemples de configuration](#-exemples-de-configuration)

---

## 🎯 Introduction

Le système de sauvegarde automatique de Leviia Schedule permet de :

- **Sauvegarder localement** la base de données SQLite
- **Stocker sur S3 ou S3-compatible** (AWS S3, MinIO, DigitalOcean Spaces, etc.)
- **Compresser** les sauvegardes pour économiser de l'espace
- **Vérifier l'intégrité** des sauvegardes
- **Nettoyer automatiquement** les anciennes sauvegardes
- **Restaurer** une sauvegarde en cas de besoin

> **⚠️ IMPORTANT** : Les sauvegardes sont essentielles pour protéger vos données. Configurez-les avant de mettre l'application en production.

---

## ✨ Fonctionnalités

| Fonctionnalité | Description | Activé par défaut |
|---------------|-------------|-------------------|
| Sauvegarde locale | Copie du fichier SQLite | ✅ Oui |
| Sauvegarde S3 | Upload vers un stockage S3 | ❌ Non |
| Compression | Compression GZIP | ✅ Oui |
| Vérification | Vérification de l'intégrité | ✅ Oui |
| Nettoyage automatique | Suppression des anciennes sauvegardes | ❌ Non |
| Restauration | Restauration depuis une sauvegarde | ✅ Oui |
| Logging | Journaux détaillés | ✅ Oui |

---

## 📦 Prérequis

### Pour la sauvegarde locale
- Python 3.8+
- Accès en écriture au système de fichiers

### Pour la sauvegarde S3
- Python 3.8+
- Bibliothèque `boto3` :
  ```bash
  pip install boto3
  ```
- Un compte S3 (AWS, MinIO, ou autre compatible)
- Des identifiants d'accès (Access Key et Secret Key)

---

## 🚀 Installation

### 1. Installer les dépendances

```bash
# Installer les dépendances de base
make install

# Installer boto3 pour les sauvegardes S3
make install-boto3
# ou
pip install boto3
```

### 2. Vérifier l'installation

```bash
# Tester le script de sauvegarde
python scripts/backup_database.py --help
```

---

## ⚙️ Configuration

### Variables d'environnement

Le système de sauvegarde utilise les variables d'environnement suivantes :

#### Configuration générale

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `BACKUP_ENABLED` | Activer/désactiver les sauvegardes | `true` |
| `BACKUP_LOCAL_ENABLED` | Activer la sauvegarde locale | `true` |
| `BACKUP_S3_ENABLED` | Activer la sauvegarde S3 | `false` |
| `BACKUP_LOG_LEVEL` | Niveau de logging | `INFO` |
| `BACKUP_LOG_FILE` | Fichier de log | `None` |

#### Sauvegarde locale

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `BACKUP_LOCAL_DIR` | Dossier de sauvegarde | `backups` |
| `BACKUP_PREFIX` | Préfixe des fichiers | `leviia_backup` |
| `BACKUP_COMPRESS` | Compresser les sauvegardes | `true` |
| `BACKUP_VERIFY` | Vérifier l'intégrité | `true` |

#### Sauvegarde S3

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `BACKUP_S3_BUCKET` | Nom du bucket S3 | `None` |
| `BACKUP_S3_ENDPOINT` | Endpoint S3 (pour S3-compatible) | `None` |
| `BACKUP_S3_REGION` | Région S3 | `None` |
| `BACKUP_S3_ACCESS_KEY` | Clé d'accès S3 | `None` |
| `BACKUP_S3_SECRET_KEY` | Clé secrète S3 | `None` |
| `BACKUP_S3_PREFIX` | Préfixe dans le bucket | `leviia-schedule` |
| `BACKUP_S3_USE_SSL` | Utiliser SSL | `true` |

#### Rétention

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `BACKUP_RETENTION_DAYS` | Nombre de jours à conserver | `30` |
| `BACKUP_MAX_BACKUPS` | Nombre maximum de sauvegardes | `30` |

#### Chiffrement (optionnel)

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `BACKUP_ENCRYPT` | Chiffrer les sauvegardes | `false` |
| `BACKUP_ENCRYPTION_KEY` | Clé de chiffrement | `None` |

### Fichier de configuration JSON

Vous pouvez créer un fichier de configuration JSON au lieu d'utiliser les variables d'environnement :

```json
{
  "enabled": true,
  "local_enabled": true,
  "local_dir": "backups",
  "s3_enabled": true,
  "s3_bucket": "mon-bucket-s3",
  "s3_endpoint": "https://s3.fr-par.scw.cloud",
  "s3_region": "fr-par",
  "s3_access_key": "votre-access-key",
  "s3_secret_key": "votre-secret-key",
  "s3_prefix": "leviia-schedule",
  "s3_use_ssl": true,
  "retention_days": 30,
  "max_backups": 30,
  "compress": true,
  "encrypt": false,
  "verify_backup": true,
  "backup_prefix": "leviia_backup",
  "log_level": "INFO"
}
```

Utilisation avec un fichier de configuration :

```bash
python scripts/backup_database.py --config /chemin/vers/config.json
```

### Configuration pour AWS S3

```bash
# Variables d'environnement pour AWS S3
export BACKUP_S3_ENABLED=true
export BACKUP_S3_BUCKET=mon-bucket-aws
export BACKUP_S3_REGION=eu-west-1
export BACKUP_S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
export BACKUP_S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### Configuration pour MinIO

```bash
# Variables d'environnement pour MinIO
export BACKUP_S3_ENABLED=true
export BACKUP_S3_BUCKET=leviia-backups
export BACKUP_S3_ENDPOINT=http://localhost:9000
export BACKUP_S3_ACCESS_KEY=minioadmin
export BACKUP_S3_SECRET_KEY=minioadmin
export BACKUP_S3_USE_SSL=false
```

---

## 🎮 Utilisation

### Sauvegarde locale

Crée une sauvegarde locale de la base de données :

```bash
# Méthode 1: Utiliser le script directement
python scripts/backup_database.py --local

# Méthode 2: Utiliser Makefile
make backup-local

# Avec vérification
python scripts/backup_database.py --local --verify

# Avec vérification et nettoyage
python scripts/backup_database.py --local --verify --cleanup
```

**Sortie attendue :**
```
============================================================
Leviia Schedule - Sauvegarde de la base de données
============================================================
INFO - Base de données détectée: /chemin/vers/instance/app.db
INFO - Création de la sauvegarde locale: backups/leviia_backup_20240101_120000.db.gz
INFO - Sauvegarde locale créée: backups/leviia_backup_20240101_120000.db.gz
INFO - Vérification réussie (SHA256: abc123...)

============================================================
RÉSULTATS DE LA SAUVEGARDE:
============================================================
✓ Sauvegarde locale: Sauvegarde locale créée: backups/leviia_backup_20240101_120000.db.gz
  Vérification: Vérification réussie (SHA256: abc123...)
```

### Sauvegarde S3

Crée une sauvegarde locale + S3 :

```bash
# Sauvegarde locale + S3
python scripts/backup_database.py --local --s3

# Avec Makefile
make backup-s3

# Sauvegarde complète (local + S3 + vérification + nettoyage)
python scripts/backup_database.py --local --s3 --verify --cleanup

# Avec Makefile
make backup-full
```

**Sortie attendue :**
```
============================================================
Leviia Schedule - Sauvegarde de la base de données
============================================================
INFO - Base de données détectée: /chemin/vers/instance/app.db
INFO - Création de la sauvegarde locale: backups/leviia_backup_20240101_120000.db.gz
INFO - Sauvegarde locale créée: backups/leviia_backup_20240101_120000.db.gz
INFO - Vérification réussie (SHA256: abc123...)
INFO - Upload vers S3: mon-bucket/leviia-schedule/leviia_backup_20240101_120000.db.gz
INFO - Upload S3 réussi: mon-bucket/leviia-schedule/leviia_backup_20240101_120000.db.gz (123456 octets)

============================================================
RÉSULTATS DE LA SAUVEGARDE:
============================================================
✓ Sauvegarde locale: Sauvegarde locale créée: backups/leviia_backup_20240101_120000.db.gz
  Vérification: Vérification réussie (SHA256: abc123...)
✓ Sauvegarde S3: Upload S3 réussi: mon-bucket/leviia-schedule/leviia_backup_20240101_120000.db.gz (123456 octets)
```

### Liste des sauvegardes

Lister toutes les sauvegardes disponibles :

```bash
# Lister les sauvegardes
python scripts/backup_database.py --list

# Avec Makefile
make backup-list
```

**Sortie attendue :**
```
============================================================
SAUVEGARDES LOCALES:
============================================================
  leviia_backup_20240101_120000.db.gz (123456 octets, 2024-01-01T12:00:00)
  leviia_backup_20231231_120000.db.gz (123456 octets, 2023-12-31T12:00:00)

============================================================
SAUVEGARDES S3:
============================================================
  leviia-schedule/leviia_backup_20240101_120000.db.gz (123456 octets, 2024-01-01T12:00:00)
  leviia-schedule/leviia_backup_20231231_120000.db.gz (123456 octets, 2023-12-31T12:00:00)
```

### Restauration

Restaurer une sauvegarde :

```bash
# Restaurer depuis un fichier local
python scripts/backup_database.py --restore backups/leviia_backup_20240101.db.gz

# Restaurer depuis S3
python scripts/backup_database.py --restore s3://mon-bucket/leviia-schedule/leviia_backup_20240101.db.gz

# Avec Makefile (spécifier le fichier)
make backup-restore BACKUP=backups/leviia_backup_20240101.db.gz
```

> **⚠️ ATTENTION** : La restauration écrase la base de données actuelle. Assurez-vous d'avoir une sauvegarde récente avant de restaurer.

**Sortie attendue :**
```
INFO - Décompression de backups/leviia_backup_20240101.db.gz
INFO - Restauration réussie: /chemin/vers/instance/app.db (123456 octets)
Restauration terminée avec succès!
```

### Nettoyage

Nettoyer les anciennes sauvegardes :

```bash
# Nettoyer les sauvegardes locales et S3
python scripts/backup_database.py --cleanup

# Avec Makefile
make backup-cleanup

# Nettoyer uniquement les sauvegardes locales
python scripts/backup_database.py --local --cleanup
```

---

## 📅 Automatisation avec Cron

### Configuration de base

Pour automatiser les sauvegardes avec cron, ajoutez une entrée à votre crontab :

```bash
# Éditer le crontab
crontab -e
```

### Exemples de cron

#### Sauvegarde quotidienne à 2h du matin

```bash
# Sauvegarde locale quotidienne
0 2 * * * /chemin/vers/leviia-schedule/venv/bin/python /chemin/vers/leviia-schedule/scripts/backup_database.py --local --verify --cleanup >> /var/log/leviia-backup.log 2>&1
```

#### Sauvegarde quotidienne avec S3

```bash
# Sauvegarde locale + S3 quotidienne
0 2 * * * /chemin/vers/leviia-schedule/venv/bin/python /chemin/vers/leviia-schedule/scripts/backup_database.py --local --s3 --verify --cleanup >> /var/log/leviia-backup.log 2>&1
```

#### Sauvegarde hebdomadaire le dimanche à 3h

```bash
# Sauvegarde hebdomadaire
0 3 * * 0 /chemin/vers/leviia-schedule/venv/bin/python /chemin/vers/leviia-schedule/scripts/backup_database.py --local --s3 --verify --cleanup >> /var/log/leviia-backup.log 2>&1
```

#### Sauvegarde mensuelle le 1er du mois à 4h

```bash
# Sauvegarde mensuelle
0 4 1 * * /chemin/vers/leviia-schedule/venv/bin/python /chemin/vers/leviia-schedule/scripts/backup_database.py --local --s3 --verify --cleanup >> /var/log/leviia-backup.log 2>&1
```

### Configuration des variables d'environnement dans cron

Pour utiliser les variables d'environnement dans cron, vous avez plusieurs options :

#### Option 1: Définir les variables dans le crontab

```bash
0 2 * * * BACKUP_S3_ENABLED=true BACKUP_S3_BUCKET=mon-bucket /chemin/vers/leviia-schedule/venv/bin/python /chemin/vers/leviia-schedule/scripts/backup_database.py --local --s3 >> /var/log/leviia-backup.log 2>&1
```

#### Option 2: Utiliser un fichier .env

Créez un fichier `/etc/leviia-backup.env` :

```bash
BACKUP_ENABLED=true
BACKUP_LOCAL_ENABLED=true
BACKUP_S3_ENABLED=true
BACKUP_S3_BUCKET=mon-bucket
BACKUP_S3_ACCESS_KEY=ma-cle-access
BACKUP_S3_SECRET_KEY=ma-cle-secrete
BACKUP_S3_REGION=eu-west-1
```

Puis modifiez votre crontab :

```bash
0 2 * * * source /etc/leviia-backup.env && /chemin/vers/leviia-schedule/venv/bin/python /chemin/vers/leviia-schedule/scripts/backup_database.py --local --s3 >> /var/log/leviia-backup.log 2>&1
```

#### Option 3: Créer un script wrapper

Créez un fichier `/usr/local/bin/leviia-backup` :

```bash
#!/bin/bash

# Charger les variables d'environnement
export BACKUP_ENABLED=true
export BACKUP_LOCAL_ENABLED=true
export BACKUP_S3_ENABLED=true
export BACKUP_S3_BUCKET=mon-bucket
export BACKUP_S3_ACCESS_KEY=ma-cle-access
export BACKUP_S3_SECRET_KEY=ma-cle-secrete
export BACKUP_S3_REGION=eu-west-1

# Exécuter la sauvegarde
/chemin/vers/leviia-schedule/venv/bin/python /chemin/vers/leviia-schedule/scripts/backup_database.py --local --s3 --verify --cleanup >> /var/log/leviia-backup.log 2>&1
```

Rendre le script exécutable :

```bash
chmod +x /usr/local/bin/leviia-backup
```

Puis dans crontab :

```bash
0 2 * * * /usr/local/bin/leviia-backup
```

---

## 🔧 Automatisation avec Systemd

Pour les systèmes utilisant systemd (Ubuntu, Debian, CentOS, etc.), vous pouvez créer un service et un timer.

### 1. Créer un fichier de service

Créez `/etc/systemd/system/leviia-backup.service` :

```ini
[Unit]
Description=Leviia Schedule Database Backup
After=network.target

[Service]
Type=oneshot
User=appuser
Group=appgroup
EnvironmentFile=/etc/leviia-backup.env
ExecStart=/chemin/vers/leviia-schedule/venv/bin/python /chemin/vers/leviia-schedule/scripts/backup_database.py --local --s3 --verify --cleanup
WorkingDirectory=/chemin/vers/leviia-schedule
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 2. Créer le fichier d'environnement

Créez `/etc/leviia-backup.env` :

```bash
BACKUP_ENABLED=true
BACKUP_LOCAL_ENABLED=true
BACKUP_S3_ENABLED=true
BACKUP_S3_BUCKET=mon-bucket
BACKUP_S3_ACCESS_KEY=ma-cle-access
BACKUP_S3_SECRET_KEY=ma-cle-secrete
BACKUP_S3_REGION=eu-west-1
```

### 3. Créer un timer pour les sauvegardes quotidiennes

Créez `/etc/systemd/system/leviia-backup.timer` :

```ini
[Unit]
Description=Timer pour les sauvegardes Leviia Schedule

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### 4. Activer le service

```bash
# Recharger systemd
sudo systemctl daemon-reload

# Activer le timer
sudo systemctl enable leviia-backup.timer
sudo systemctl start leviia-backup.timer

# Vérifier le statut
sudo systemctl status leviia-backup.timer

# Voir les logs
sudo journalctl -u leviia-backup.service -f
```

### 5. Exécuter manuellement

```bash
# Exécuter une sauvegarde manuellement
sudo systemctl start leviia-backup.service

# Voir le statut
sudo systemctl status leviia-backup.service
```

---

## 🔒 Sécurité

### Bonnes pratiques de sécurité

1. **Protégez vos identifiants S3**
   - Ne stockez jamais les identifiants dans le code source
   - Utilisez des variables d'environnement ou des fichiers de configuration sécurisés
   - Limitez les permissions IAM au strict minimum

2. **Chiffrez les sauvegardes** (optionnel)
   - Activez `BACKUP_ENCRYPT=true`
   - Définissez une clé de chiffrement forte : `BACKUP_ENCRYPTION_KEY`

3. **Limitez l'accès aux sauvegardes**
   - Stockez les sauvegardes dans un bucket privé
   - Utilisez des politiques de bucket restrictives

4. **Utilisez HTTPS**
   - Activez `BACKUP_S3_USE_SSL=true` (activé par défaut)

5. **Rotation des clés**
   - Changez régulièrement vos clés d'accès S3
   - Utilisez IAM Roles pour AWS si possible

6. **Sauvegardes locales**
   - Stockez les sauvegardes locales dans un dossier sécurisé
   - Limitez les permissions du dossier : `chmod 700 backups/`

### Configuration IAM pour AWS S3

Exemple de politique IAM minimale pour les sauvegardes :

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::mon-bucket",
        "arn:aws:s3:::mon-bucket/leviia-schedule/*"
      ]
    }
  ]
}
```

---

## 🐛 Dépannage

### Problèmes courants

#### 1. "Impossible de trouver la base de données"

**Cause :** Le script ne trouve pas le fichier SQLite.

**Solutions :**
- Vérifiez que la base de données existe : `ls instance/app.db`
- Définissez explicitement le chemin : `export DATABASE_URL=sqlite:///chemin/vers/app.db`
- Exécutez le script depuis la racine du projet

#### 2. "boto3 non installé"

**Solution :**
```bash
pip install boto3
```

#### 3. "Identifiants S3 manquants"

**Solution :**
- Vérifiez que `BACKUP_S3_ACCESS_KEY` et `BACKUP_S3_SECRET_KEY` sont définis
- Vérifiez que les variables sont accessibles dans l'environnement d'exécution

#### 4. "Bucket introuvable"

**Solutions :**
- Vérifiez que le bucket existe
- Vérifiez que vous avez les permissions pour accéder au bucket
- Vérifiez que la région est correcte

#### 5. "Accès refusé au bucket"

**Solutions :**
- Vérifiez les permissions IAM
- Vérifiez la politique du bucket
- Vérifiez que les identifiants sont corrects

#### 6. "Erreur de vérification"

**Solutions :**
- Vérifiez que le fichier de sauvegarde n'est pas corrompu
- Essayez sans compression : `BACKUP_COMPRESS=false`
- Vérifiez l'espace disque disponible

### Journalisation

Pour activer le logging détaillé :

```bash
# Niveau de log DEBUG
export BACKUP_LOG_LEVEL=DEBUG

# Fichier de log
export BACKUP_LOG_FILE=/var/log/leviia-backup.log

# Exécuter avec logging
python scripts/backup_database.py --local --s3 --verify
```

### Tester la connexion S3

```python
import boto3

# Tester la connexion
s3 = boto3.client(
    's3',
    endpoint_url='votre-endpoint',
    aws_access_key_id='votre-access-key',
    aws_secret_access_key='votre-secret-key',
    region_name='votre-region'
)

# Lister les buckets
response = s3.list_buckets()
print("Buckets:", [b['Name'] for b in response['Buckets']])
```

---

## 📝 Exemples de configuration

### Configuration minimale (locale uniquement)

```bash
# .env ou variables d'environnement
export BACKUP_ENABLED=true
export BACKUP_LOCAL_ENABLED=true
export BACKUP_LOCAL_DIR=/var/backups/leviia
export BACKUP_RETENTION_DAYS=30
```

### Configuration complète (AWS S3)

```bash
# .env ou variables d'environnement
export BACKUP_ENABLED=true
export BACKUP_LOCAL_ENABLED=true
export BACKUP_S3_ENABLED=true
export BACKUP_LOCAL_DIR=/var/backups/leviia
export BACKUP_S3_BUCKET=leviia-backups-prod
export BACKUP_S3_REGION=eu-west-1
export BACKUP_S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
export BACKUP_S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export BACKUP_S3_PREFIX=production
export BACKUP_RETENTION_DAYS=90
export BACKUP_MAX_BACKUPS=60
export BACKUP_COMPRESS=true
export BACKUP_VERIFY=true
export BACKUP_LOG_LEVEL=INFO
export BACKUP_LOG_FILE=/var/log/leviia-backup.log
```

### Configuration pour MinIO

```bash
# .env ou variables d'environnement
export BACKUP_ENABLED=true
export BACKUP_LOCAL_ENABLED=true
export BACKUP_S3_ENABLED=true
export BACKUP_LOCAL_DIR=/var/backups/leviia
export BACKUP_S3_BUCKET=leviia-backups
export BACKUP_S3_ENDPOINT=http://minio.local:9000
export BACKUP_S3_ACCESS_KEY=minioadmin
export BACKUP_S3_SECRET_KEY=minioadmin
export BACKUP_S3_USE_SSL=false
export BACKUP_S3_PREFIX=leviia
export BACKUP_RETENTION_DAYS=30
```

### Configuration pour DigitalOcean Spaces

```bash
# .env ou variables d'environnement
export BACKUP_ENABLED=true
export BACKUP_LOCAL_ENABLED=true
export BACKUP_S3_ENABLED=true
export BACKUP_LOCAL_DIR=/var/backups/leviia
export BACKUP_S3_BUCKET=leviia-backups
export BACKUP_S3_ENDPOINT=https://nyc3.digitaloceanspaces.com
export BACKUP_S3_REGION=nyc3
export BACKUP_S3_ACCESS_KEY=DO00ABCDEFGHIJKLMNOP
export BACKUP_S3_SECRET_KEY=abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH
export BACKUP_S3_PREFIX=leviia
export BACKUP_RETENTION_DAYS=30
```

---

## 📚 Documentation supplémentaire

- [Documentation AWS S3](https://docs.aws.amazon.com/s3/)
- [Documentation boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [Cron Documentation](https://www.freebsd.org/cgi/man.cgi?crontab)
- [Systemd Timers](https://www.freedesktop.org/software/systemd/man/systemd.timer.html)

---

## 🙏 Support

Pour toute question ou problème, consultez :

1. La section [Dépannage](#-dépannage) de ce guide
2. Les logs du script de sauvegarde
3. Ouvrez une issue sur le dépôt GitHub

---

> **⚠️ RAPPEL** : Testez toujours votre processus de sauvegarde et de restauration avant de dépendre d'un système de sauvegarde automatique en production.
