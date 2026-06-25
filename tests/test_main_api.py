"""
Tests pour les endpoints API de main.py
Couvre les routes API non testées précédemment.
"""

import pytest
import json
from datetime import datetime, timedelta, date


class TestAPIGetShifts:
    """Tests pour GET /api/shifts."""

    def test_returns_json(self, logged_in_client):
        """Test que /api/shifts retourne du JSON."""
        response = logged_in_client.get('/api/shifts')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_returns_list(self, logged_in_client):
        """Test que /api/shifts retourne une liste."""
        response = logged_in_client.get('/api/shifts')
        data = json.loads(response.data)
        assert isinstance(data, list)


class TestAPIGetUsers:
    """Tests pour GET /api/users."""

    def test_returns_json(self, logged_in_client):
        """Test que /api/users retourne du JSON."""
        response = logged_in_client.get('/api/users')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_returns_list(self, logged_in_client):
        """Test que /api/users retourne une liste."""
        response = logged_in_client.get('/api/users')
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_returns_user_data(self, logged_in_client):
        """Test que /api/users retourne les données des utilisateurs."""
        response = logged_in_client.get('/api/users')
        data = json.loads(response.data)
        if data:
            user = data[0]
            assert 'id' in user
            assert 'name' in user
            assert 'email' in user


class TestAPIGetShiftTypes:
    """Tests pour GET /api/shift-types."""

    def test_returns_json(self, logged_in_client):
        """Test que /api/shift-types retourne du JSON."""
        response = logged_in_client.get('/api/shift-types')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

    def test_returns_list(self, logged_in_client):
        """Test que /api/shift-types retourne une liste."""
        response = logged_in_client.get('/api/shift-types')
        data = json.loads(response.data)
        assert isinstance(data, list)


class TestAPICreateShift:
    """Tests pour POST /api/shifts."""

    def test_requires_admin(self, logged_in_client):
        """Test que POST /api/shifts nécessite admin."""
        response = logged_in_client.post('/api/shifts', json={})
        assert response.status_code in [302, 403]

    def test_requires_data(self, logged_in_admin_client):
        """Test que POST /api/shifts nécessite des données."""
        response = logged_in_admin_client.post('/api/shifts', json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_missing_fields(self, logged_in_admin_client):
        """Test que POST /api/shifts échoue avec des champs manquants."""
        response = logged_in_admin_client.post('/api/shifts', json={
            'userId': 1
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False


class TestAPIUpdateShift:
    """Tests pour PATCH /api/shifts/<id>."""

    def test_requires_admin(self, logged_in_client):
        """Test que PATCH /api/shifts/<id> nécessite admin."""
        response = logged_in_client.patch('/api/shifts/1', json={})
        assert response.status_code in [302, 403]

    def test_nonexistent_shift(self, logged_in_admin_client):
        """Test que PATCH /api/shifts/<id> retourne 404 pour un shift inexistant."""
        response = logged_in_admin_client.patch('/api/shifts/99999', json={})
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False


class TestAPIDeleteShift:
    """Tests pour DELETE /api/shifts/<id>."""

    def test_requires_admin(self, logged_in_client):
        """Test que DELETE /api/shifts/<id> nécessite admin."""
        response = logged_in_client.delete('/api/shifts/1')
        assert response.status_code in [302, 403]

    def test_nonexistent_shift(self, logged_in_admin_client):
        """Test que DELETE /api/shifts/<id> retourne 404 pour un shift inexistant."""
        response = logged_in_admin_client.delete('/api/shifts/99999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
