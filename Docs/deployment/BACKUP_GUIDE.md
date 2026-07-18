# Automated Backup Guide - Kairos

> **📖 Complete documentation for database backups**

This guide explains how to configure and use the automated backup system for Kairos.

## 📋 Table of Contents

1. [Introduction](#-introduction)
2. [Features](#-features)
3. [Prerequisites](#-prerequisites)
4. [Installation](#-installation)
5. [Configuration](#-configuration)
   - [Environment variables](#environment-variables)
   - [JSON configuration file](#json-configuration-file)
   - [AWS S3 configuration](#aws-s3-configuration)
   - [MinIO configuration](#minio-configuration)
6. [Usage](#-usage)
   - [Local backup](#local-backup)
   - [S3 backup](#s3-backup)
   - [Full backup](#full-backup)
   - [List of backups](#list-of-backups)
   - [Restoration](#restoration)
   - [Cleanup](#cleanup)
7. [Automation with Cron](#-automation-with-cron)
8. [Automation with Systemd](#-automation-with-systemd)
9. [Admin interface](#️-admin-interface)
10. [Docker](#-docker)
11. [Security](#-security)
12. [Troubleshooting](#-troubleshooting)
13. [Configuration examples](#-configuration-examples)

---

## 🎯 Introduction

The Kairos automated backup system allows you to:

- **Back up locally** the SQLite database
- **Store on S3 or S3-compatible storage** (AWS S3, MinIO, DigitalOcean Spaces, etc.)
- **Compress** backups to save space
- **Verify the integrity** of backups
- **Automatically clean up** old backups
- **Restore** a backup when needed

> **⚠️ IMPORTANT**: Backups are essential to protect your data. Configure them before putting the application into production.

---

## ✨ Features

| Feature | Description | Enabled by default |
|---------------|-------------|-------------------|
| Local backup | Copy of the SQLite file | ✅ Yes |
| S3 backup | Upload to S3 storage | ❌ No |
| Compression | GZIP compression | ✅ Yes |
| Verification | Integrity check | ✅ Yes |
| Automatic cleanup | Deletion of old backups | ❌ No |
| Restoration | Restore from a backup | ✅ Yes |
| Logging | Detailed logs | ✅ Yes |

---

## 📦 Prerequisites

### For local backup
- Python 3.8+
- Write access to the filesystem

### For S3 backup
- Python 3.8+
- `boto3` library:
  ```bash
  pip install boto3
  ```
- An S3 account (AWS, MinIO, or another compatible service)
- Access credentials (Access Key and Secret Key)

---

## 🚀 Installation

### 1. Install dependencies

```bash
# Install base dependencies
make install

# Install boto3 for S3 backups
pip install boto3
```

### 2. Verify the installation

```bash
# Test the backup script
python scripts/backup_database.py --help
```

---

## ⚙️ Configuration

### Environment variables

The backup system uses the following environment variables:

#### General configuration

| Variable | Description | Default value |
|----------|-------------|-------------------|
| `BACKUP_ENABLED` | Enable/disable backups (opt-in) | `false` |
| `BACKUP_LOCAL_ENABLED` | Enable local backup | `true` |
| `BACKUP_S3_ENABLED` | Enable S3 backup | `false` |
| `BACKUP_LOG_LEVEL` | Logging level | `INFO` |
| `BACKUP_LOG_FILE` | Log file | `None` |

#### Local backup

| Variable | Description | Default value |
|----------|-------------|-------------------|
| `BACKUP_LOCAL_DIR` | Backup folder | `backups` |
| `BACKUP_PREFIX` | File prefix | `kairos_backup` |
| `BACKUP_COMPRESS` | Compress backups | `true` |
| `BACKUP_VERIFY` | Verify integrity | `true` |

#### S3 backup

| Variable | Description | Default value |
|----------|-------------|-------------------|
| `BACKUP_S3_BUCKET` | S3 bucket name | `None` |
| `BACKUP_S3_ENDPOINT` | S3 endpoint (for S3-compatible services) | `None` |
| `BACKUP_S3_REGION` | S3 region | `None` |
| `BACKUP_S3_ACCESS_KEY` | S3 access key | `None` |
| `BACKUP_S3_SECRET_KEY` | S3 secret key | `None` |
| `BACKUP_S3_PREFIX` | Prefix within the bucket | `kairos` |
| `BACKUP_S3_USE_SSL` | Use SSL | `true` |

#### Retention

| Variable | Description | Default value |
|----------|-------------|-------------------|
| `BACKUP_RETENTION_DAYS` | Number of days to keep | `30` |
| `BACKUP_MAX_BACKUPS` | Maximum number of backups | `30` |

#### Email notifications

| Variable | Description | Default value |
|----------|-------------|-------------------|
| `BACKUP_NOTIFY_ON_SUCCESS` | Email on success | `false` |
| `BACKUP_NOTIFY_ON_FAILURE` | Email on failure | `true` |
| `BACKUP_NOTIFICATION_EMAIL` | Alert recipient | `None` |

Reuses the SMTP configuration from email notifications (see
[`reference/ENVIRONMENT_VARIABLES.md`](../reference/ENVIRONMENT_VARIABLES.md#-configuration-des-notifications)) -
so it's also subject to `NOTIFICATIONS_ENABLED`.

### JSON configuration file

You can create a JSON configuration file instead of using environment variables:

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
  "s3_prefix": "kairos",
  "s3_use_ssl": true,
  "retention_days": 30,
  "max_backups": 30,
  "compress": true,
  "verify_backup": true,
  "backup_prefix": "kairos_backup",
  "log_level": "INFO"
}
```

Usage with a configuration file:

```bash
python scripts/backup_database.py --config /chemin/vers/config.json
```

### AWS S3 configuration

```bash
# Environment variables for AWS S3
export BACKUP_S3_ENABLED=true
export BACKUP_S3_BUCKET=mon-bucket-aws
export BACKUP_S3_REGION=eu-west-1
export BACKUP_S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
export BACKUP_S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### MinIO configuration

```bash
# Environment variables for MinIO
export BACKUP_S3_ENABLED=true
export BACKUP_S3_BUCKET=kairos-backups
export BACKUP_S3_ENDPOINT=http://localhost:9000
export BACKUP_S3_ACCESS_KEY=minioadmin
export BACKUP_S3_SECRET_KEY=minioadmin
export BACKUP_S3_USE_SSL=false
```

---

## 🎮 Usage

### Local backup

Creates a local backup of the database:

```bash
# Method 1: Use the script directly
python scripts/backup_database.py --local

# Method 2: Use the Makefile (equivalent to --local --verify)
make backup

# With verification
python scripts/backup_database.py --local --verify

# With verification and cleanup
python scripts/backup_database.py --local --verify --cleanup
```

**Expected output:**
```
============================================================
Kairos - Database backup
============================================================
INFO - Database detected: /path/to/instance/app.db
INFO - Creating local backup: backups/kairos_backup_20240101_120000.db.gz
INFO - Local backup created: backups/kairos_backup_20240101_120000.db.gz
INFO - Verification successful (SHA256: abc123...)

============================================================
BACKUP RESULTS:
============================================================
✓ Local backup: Local backup created: backups/kairos_backup_20240101_120000.db.gz
  Verification: Verification successful (SHA256: abc123...)
```

### S3 backup

Creates a local + S3 backup:

```bash
# Local + S3 backup
python scripts/backup_database.py --local --s3

# Full backup (local + S3 + verification + cleanup)
python scripts/backup_database.py --local --s3 --verify --cleanup
```

> The Makefile only wraps the local backup by default (`make backup`) and the
> restore (`make backup-restore`) - the S3/cleanup/list combinations
> below are invoked directly via `scripts/backup_database.py`.

**Expected output:**
```
============================================================
Kairos - Database backup
============================================================
INFO - Database detected: /path/to/instance/app.db
INFO - Creating local backup: backups/kairos_backup_20240101_120000.db.gz
INFO - Local backup created: backups/kairos_backup_20240101_120000.db.gz
INFO - Verification successful (SHA256: abc123...)
INFO - Uploading to S3: mon-bucket/kairos/kairos_backup_20240101_120000.db.gz
INFO - S3 upload successful: mon-bucket/kairos/kairos_backup_20240101_120000.db.gz (123456 bytes)

============================================================
BACKUP RESULTS:
============================================================
✓ Local backup: Local backup created: backups/kairos_backup_20240101_120000.db.gz
  Verification: Verification successful (SHA256: abc123...)
✓ S3 backup: S3 upload successful: mon-bucket/kairos/kairos_backup_20240101_120000.db.gz (123456 bytes)
```

### List of backups

List all available backups:

```bash
# List backups
python scripts/backup_database.py --list
```

**Expected output:**
```
============================================================
LOCAL BACKUPS:
============================================================
  kairos_backup_20240101_120000.db.gz (123456 bytes, 2024-01-01T12:00:00)
  kairos_backup_20231231_120000.db.gz (123456 bytes, 2023-12-31T12:00:00)

============================================================
S3 BACKUPS:
============================================================
  kairos/kairos_backup_20240101_120000.db.gz (123456 bytes, 2024-01-01T12:00:00)
  kairos/kairos_backup_20231231_120000.db.gz (123456 bytes, 2023-12-31T12:00:00)
```

### Restoration

Restore a backup:

```bash
# Restore from a local file
python scripts/backup_database.py --restore backups/kairos_backup_20240101.db.gz

# Restore from S3
python scripts/backup_database.py --restore s3://mon-bucket/kairos/kairos_backup_20240101.db.gz

# With Makefile (specify the file)
make backup-restore BACKUP=backups/kairos_backup_20240101.db.gz
```

> **⚠️ WARNING**: Restoring overwrites the current database. Make sure you have a recent backup before restoring.

**Expected output:**
```
INFO - Decompressing backups/kairos_backup_20240101.db.gz
INFO - Restore successful: /path/to/instance/app.db (123456 bytes)
Restore completed successfully!
```

### Cleanup

Clean up old backups:

```bash
# Clean up local and S3 backups
python scripts/backup_database.py --cleanup

# Clean up local backups only
python scripts/backup_database.py --local --cleanup
```

---

## 📅 Automation with Cron

### Basic configuration

To automate backups with cron, add an entry to your crontab:

```bash
# Edit the crontab
crontab -e
```

### Cron examples

#### Daily backup at 2 AM

```bash
# Daily local backup
0 2 * * * /chemin/vers/kairos/venv/bin/python /chemin/vers/kairos/scripts/backup_database.py --local --verify --cleanup >> /var/log/kairos-backup.log 2>&1
```

#### Daily backup with S3

```bash
# Daily local + S3 backup
0 2 * * * /chemin/vers/kairos/venv/bin/python /chemin/vers/kairos/scripts/backup_database.py --local --s3 --verify --cleanup >> /var/log/kairos-backup.log 2>&1
```

#### Weekly backup on Sunday at 3 AM

```bash
# Weekly backup
0 3 * * 0 /chemin/vers/kairos/venv/bin/python /chemin/vers/kairos/scripts/backup_database.py --local --s3 --verify --cleanup >> /var/log/kairos-backup.log 2>&1
```

#### Monthly backup on the 1st of the month at 4 AM

```bash
# Monthly backup
0 4 1 * * /chemin/vers/kairos/venv/bin/python /chemin/vers/kairos/scripts/backup_database.py --local --s3 --verify --cleanup >> /var/log/kairos-backup.log 2>&1
```

### Configuring environment variables in cron

To use environment variables in cron, you have several options:

#### Option 1: Define the variables in the crontab

```bash
0 2 * * * BACKUP_S3_ENABLED=true BACKUP_S3_BUCKET=mon-bucket /chemin/vers/kairos/venv/bin/python /chemin/vers/kairos/scripts/backup_database.py --local --s3 >> /var/log/kairos-backup.log 2>&1
```

#### Option 2: Use a .env file

Create a file `/etc/kairos-backup.env`:

```bash
BACKUP_ENABLED=true
BACKUP_LOCAL_ENABLED=true
BACKUP_S3_ENABLED=true
BACKUP_S3_BUCKET=mon-bucket
BACKUP_S3_ACCESS_KEY=ma-cle-access
BACKUP_S3_SECRET_KEY=ma-cle-secrete
BACKUP_S3_REGION=eu-west-1
```

Then edit your crontab:

```bash
0 2 * * * source /etc/kairos-backup.env && /chemin/vers/kairos/venv/bin/python /chemin/vers/kairos/scripts/backup_database.py --local --s3 >> /var/log/kairos-backup.log 2>&1
```

#### Option 3: Create a wrapper script

Create a file `/usr/local/bin/kairos-backup`:

```bash
#!/bin/bash

# Load environment variables
export BACKUP_ENABLED=true
export BACKUP_LOCAL_ENABLED=true
export BACKUP_S3_ENABLED=true
export BACKUP_S3_BUCKET=mon-bucket
export BACKUP_S3_ACCESS_KEY=ma-cle-access
export BACKUP_S3_SECRET_KEY=ma-cle-secrete
export BACKUP_S3_REGION=eu-west-1

# Run the backup
/chemin/vers/kairos/venv/bin/python /chemin/vers/kairos/scripts/backup_database.py --local --s3 --verify --cleanup >> /var/log/kairos-backup.log 2>&1
```

Make the script executable:

```bash
chmod +x /usr/local/bin/kairos-backup
```

Then in crontab:

```bash
0 2 * * * /usr/local/bin/kairos-backup
```

---

## 🔧 Automation with Systemd

For systems using systemd (Ubuntu, Debian, CentOS, etc.), you can create a service and a timer.

### 1. Create a service file

Create `/etc/systemd/system/kairos-backup.service`:

```ini
[Unit]
Description=Kairos Database Backup
After=network.target

[Service]
Type=oneshot
User=appuser
Group=appgroup
EnvironmentFile=/etc/kairos-backup.env
ExecStart=/chemin/vers/kairos/venv/bin/python /chemin/vers/kairos/scripts/backup_database.py --local --s3 --verify --cleanup
WorkingDirectory=/chemin/vers/kairos
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 2. Create the environment file

Create `/etc/kairos-backup.env`:

```bash
BACKUP_ENABLED=true
BACKUP_LOCAL_ENABLED=true
BACKUP_S3_ENABLED=true
BACKUP_S3_BUCKET=mon-bucket
BACKUP_S3_ACCESS_KEY=ma-cle-access
BACKUP_S3_SECRET_KEY=ma-cle-secrete
BACKUP_S3_REGION=eu-west-1
```

### 3. Create a timer for daily backups

Create `/etc/systemd/system/kairos-backup.timer`:

```ini
[Unit]
Description=Timer for Kairos backups

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### 4. Enable the service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable the timer
sudo systemctl enable kairos-backup.timer
sudo systemctl start kairos-backup.timer

# Check the status
sudo systemctl status kairos-backup.timer

# View the logs
sudo journalctl -u kairos-backup.service -f
```

### 5. Run manually

```bash
# Run a backup manually
sudo systemctl start kairos-backup.service

# Check the status
sudo systemctl status kairos-backup.service
```

---

## 🖥️ Admin interface

In addition to the command-line script, a dashboard is
available at `/admin/backups` (restricted to admin accounts):

- Overview of the active configuration (enabled state, local folder, S3 bucket, retention)
- List of local and S3 backups (name, size, date)
- **Create a backup now** button (refused if `BACKUP_ENABLED=false`,
  same safeguard as the cron script)
- **Clean up expired backups** button (applies `BACKUP_RETENTION_DAYS`/`BACKUP_MAX_BACKUPS`)
- Downloading a backup: local files are served
  directly, S3 files are downloaded server-side to a
  temporary file then streamed to the browser (no presigned URL
  exposed directly)

Reading (listing/downloading) remains possible even if
`BACKUP_ENABLED=false` - only the creation of new backups is
blocked by this variable.

---

## 🐳 Docker

If you deploy with `docker/docker-compose.yml`, set
`BACKUP_ENABLED=true` in `docker/.env` so that `crond` (already
used for email reminders) also starts the daily backup
job (schedule in `docker/crontabs/appuser`, 3 AM). For local backups
to survive container recreation, set
`BACKUP_LOCAL_DIR=/app/data/backups` (the `./data:/app/data` volume
is already mounted - no additional volume needed). See
[`deployment/docker.md`](docker.md) for integration details.

---

## 🔒 Security

### Security best practices

1. **Protect your S3 credentials**
   - Never store credentials in source code
   - Use environment variables or secured configuration files
   - Limit IAM permissions to the strict minimum

2. **Restrict access to backups**
   - Store backups in a private bucket
   - Use restrictive bucket policies
   - On the admin interface side, only admin accounts
     (`@admin_required`) can list/create/download backups

3. **Use HTTPS**
   - Enable `BACKUP_S3_USE_SSL=true` (enabled by default)

4. **Key rotation**
   - Rotate your S3 access keys regularly
   - Use IAM Roles for AWS if possible

5. **Local backups**
   - Store local backups in a secured folder
   - Restrict folder permissions: `chmod 700 backups/`

### IAM configuration for AWS S3

Example of a minimal IAM policy for backups:

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
        "arn:aws:s3:::mon-bucket/kairos/*"
      ]
    }
  ]
}
```

---

## 🐛 Troubleshooting

### Common issues

#### 1. "Unable to find the database"

**Cause:** The script cannot find the SQLite file.

**Solutions:**
- Check that the database exists: `ls instance/app.db`
- Explicitly set the path: `export DATABASE_URL=sqlite:///chemin/vers/app.db`
- Run the script from the project root

#### 2. "boto3 not installed"

**Solution:**
```bash
pip install boto3
```

#### 3. "Missing S3 credentials"

**Solution:**
- Check that `BACKUP_S3_ACCESS_KEY` and `BACKUP_S3_SECRET_KEY` are set
- Check that the variables are accessible in the runtime environment

#### 4. "Bucket not found"

**Solutions:**
- Check that the bucket exists
- Check that you have permission to access the bucket
- Check that the region is correct

#### 5. "Access denied to the bucket"

**Solutions:**
- Check IAM permissions
- Check the bucket policy
- Check that the credentials are correct

#### 6. "Verification error"

**Solutions:**
- Check that the backup file is not corrupted
- Try without compression: `BACKUP_COMPRESS=false`
- Check available disk space

### Logging

To enable detailed logging:

```bash
# DEBUG log level
export BACKUP_LOG_LEVEL=DEBUG

# Log file
export BACKUP_LOG_FILE=/var/log/kairos-backup.log

# Run with logging
python scripts/backup_database.py --local --s3 --verify
```

### Test the S3 connection

```python
import boto3

# Test the connection
s3 = boto3.client(
    's3',
    endpoint_url='votre-endpoint',
    aws_access_key_id='votre-access-key',
    aws_secret_access_key='votre-secret-key',
    region_name='votre-region'
)

# List buckets
response = s3.list_buckets()
print("Buckets:", [b['Name'] for b in response['Buckets']])
```

---

## 📝 Configuration examples

### Minimal configuration (local only)

```bash
# .env or environment variables
export BACKUP_ENABLED=true
export BACKUP_LOCAL_ENABLED=true
export BACKUP_LOCAL_DIR=/var/backups/kairos
export BACKUP_RETENTION_DAYS=30
```

### Full configuration (AWS S3)

```bash
# .env or environment variables
export BACKUP_ENABLED=true
export BACKUP_LOCAL_ENABLED=true
export BACKUP_S3_ENABLED=true
export BACKUP_LOCAL_DIR=/var/backups/kairos
export BACKUP_S3_BUCKET=kairos-backups-prod
export BACKUP_S3_REGION=eu-west-1
export BACKUP_S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
export BACKUP_S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export BACKUP_S3_PREFIX=production
export BACKUP_RETENTION_DAYS=90
export BACKUP_MAX_BACKUPS=60
export BACKUP_COMPRESS=true
export BACKUP_VERIFY=true
export BACKUP_LOG_LEVEL=INFO
export BACKUP_LOG_FILE=/var/log/kairos-backup.log
```

### MinIO configuration

```bash
# .env or environment variables
export BACKUP_ENABLED=true
export BACKUP_LOCAL_ENABLED=true
export BACKUP_S3_ENABLED=true
export BACKUP_LOCAL_DIR=/var/backups/kairos
export BACKUP_S3_BUCKET=kairos-backups
export BACKUP_S3_ENDPOINT=http://minio.local:9000
export BACKUP_S3_ACCESS_KEY=minioadmin
export BACKUP_S3_SECRET_KEY=minioadmin
export BACKUP_S3_USE_SSL=false
export BACKUP_S3_PREFIX=kairos
export BACKUP_RETENTION_DAYS=30
```

### DigitalOcean Spaces configuration

```bash
# .env or environment variables
export BACKUP_ENABLED=true
export BACKUP_LOCAL_ENABLED=true
export BACKUP_S3_ENABLED=true
export BACKUP_LOCAL_DIR=/var/backups/kairos
export BACKUP_S3_BUCKET=kairos-backups
export BACKUP_S3_ENDPOINT=https://nyc3.digitaloceanspaces.com
export BACKUP_S3_REGION=nyc3
export BACKUP_S3_ACCESS_KEY=DO00ABCDEFGHIJKLMNOP
export BACKUP_S3_SECRET_KEY=abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH
export BACKUP_S3_PREFIX=kairos
export BACKUP_RETENTION_DAYS=30
```

---

## 📚 Additional documentation

- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [Cron Documentation](https://www.freebsd.org/cgi/man.cgi?crontab)
- [Systemd Timers](https://www.freedesktop.org/software/systemd/man/systemd.timer.html)

---

## 🙏 Support

For any questions or issues, refer to:

1. The [Troubleshooting](#-troubleshooting) section of this guide
2. The backup script logs
3. Open an issue on the GitHub repository

---

> **⚠️ REMINDER**: Always test your backup and restore process before relying on an automated backup system in production.
