"""
Tests pour les routes admin de sauvegarde (app/routes/admin_backup_routes.py).
"""

import pytest


def make_sqlite_file(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)


@pytest.fixture(autouse=True)
def _isolate_backup_env(tmp_path, monkeypatch):
    """Isolate the local backup directory and disable S3, so these tests
    never touch the real repo / the real dev database."""
    monkeypatch.delenv("BACKUP_S3_ENABLED", raising=False)
    monkeypatch.setenv("BACKUP_LOCAL_DIR", str(tmp_path / "backups"))


class TestBackupsDashboard:
    def test_dashboard_get(self, logged_in_client):
        response = logged_in_client.get("/admin/backups")
        assert response.status_code == 200
        assert b"Sauvegardes" in response.data

    def test_dashboard_unauthenticated(self, client):
        response = client.get("/admin/backups", follow_redirects=True)
        assert b"Connexion" in response.data

    def test_dashboard_lists_local_backups(self, logged_in_client, tmp_path):
        local_dir = tmp_path / "backups"
        local_dir.mkdir(exist_ok=True)
        (local_dir / "kairos_backup_1.sqlite.gz").write_bytes(b"x")

        response = logged_in_client.get("/admin/backups")

        assert response.status_code == 200
        assert b"kairos_backup_1.sqlite.gz" in response.data


class TestBackupsCreate:
    def test_create_without_database_redirects_with_error(self, logged_in_client):
        response = logged_in_client.post("/admin/backups/create", follow_redirects=True)
        assert response.status_code == 200

    def test_create_with_database_succeeds(
        self, logged_in_client, tmp_path, monkeypatch
    ):
        db_path = tmp_path / "source" / "app.db"
        make_sqlite_file(db_path)
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
        monkeypatch.setenv("BACKUP_ENABLED", "true")

        response = logged_in_client.post("/admin/backups/create", follow_redirects=True)

        assert response.status_code == 200
        assert b"succ\xc3\xa8s" in response.data or b"success" in response.data.lower()


class TestBackupsCleanup:
    def test_cleanup_redirects(self, logged_in_client):
        response = logged_in_client.post(
            "/admin/backups/cleanup", follow_redirects=True
        )
        assert response.status_code == 200
        assert b"Nettoyage" in response.data


class TestBackupsDownloadLocal:
    def test_download_existing_backup(self, logged_in_client, tmp_path):
        local_dir = tmp_path / "backups"
        local_dir.mkdir(exist_ok=True)
        backup_file = local_dir / "kairos_backup_1.sqlite.gz"
        backup_file.write_bytes(b"fake backup content")

        response = logged_in_client.get(
            "/admin/backups/download/local/kairos_backup_1.sqlite.gz"
        )

        assert response.status_code == 200
        assert response.data == b"fake backup content"

    def test_download_missing_backup_returns_404(self, logged_in_client):
        response = logged_in_client.get(
            "/admin/backups/download/local/kairos_backup_missing.sqlite.gz"
        )
        assert response.status_code == 404

    def test_download_path_traversal_returns_404(self, logged_in_client):
        response = logged_in_client.get(
            "/admin/backups/download/local/kairos_backup_x/../../etc/passwd"
        )
        assert response.status_code == 404


class TestBackupsDownloadS3:
    def test_download_when_s3_disabled_returns_404(self, logged_in_client):
        response = logged_in_client.get("/admin/backups/download/s3/some/key.gz")
        assert response.status_code == 404
