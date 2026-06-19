"""
Tests pour les routes Flask.
"""
import pytest
from datetime import datetime, timedelta
from app.models import Shift, OnCall, Leave, User, Group


class TestRolePermissions:
    """Tests pour les permissions basées sur les rôles."""
    
    def test_decorators_import(self):
        """Test que les décorateurs peuvent être importés."""
        from app.utils.decorators import admin_required, role_required
        assert callable(admin_required)
        assert callable(role_required)
    
    def test_models_have_is_admin(self):
        """Test que le modèle User a le champ is_admin."""
        from app.models import User
        assert hasattr(User, 'is_admin')


class TestShiftRoutes:
    """Tests pour les routes des shifts."""


class TestShiftRoutes:
    """Tests pour les routes des shifts."""
    
    def test_add_shift_get(self, client, test_user):
        """Test l'affichage du formulaire d'ajout de shift."""
        response = client.get('/schedule/add')
        assert response.status_code == 200
        assert b'Ajouter un shift' in response.data
    
    def test_add_shift_post_valid(self, client, test_user):
        """Test l'ajout d'un shift valide."""
        data = {
            'user_id': test_user.id,
            'shift_type': 'morning',
            'start_date': '2023-12-01',
            'end_date': '2023-12-01'
        }
        response = client.post('/schedule/add', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b'Shifts ajout' in response.data and b'succes' in response.data
        
        # Verifier que le shift a ete ajoute
        shifts = Shift.query.filter_by(user_id=test_user.id).all()
        assert len(shifts) == 1
    
    def test_add_shift_post_invalid_dates(self, client, test_user):
        """Test l'ajout d'un shift avec des dates invalides."""
        data = {
            'user_id': test_user.id,
            'shift_type': 'morning',
            'start_date': '2023-12-02',  # Samedi
            'end_date': '2023-12-02'
        }
        response = client.post('/schedule/add', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b'les shifts ne peuvent etre ajoutes que du lundi au vendredi' in response.data
    
    def test_delete_shift_post(self, client, test_shift):
        """Test la suppression d'un shift."""
        response = client.post(f'/schedule/delete/{test_shift.id}', follow_redirects=True)
        assert response.status_code == 200
        assert b'Shift supprime' in response.data and b'succes' in response.data
        
        # Verifier que le shift a ete supprime
        shift = Shift.query.get(test_shift.id)
        assert shift is None


class TestOnCallRoutes:
    """Tests pour les routes des astreintes."""
    
    def test_add_oncall_get(self, client, test_user):
        """Test l'affichage du formulaire d'ajout d'astreinte."""
        response = client.get('/oncall/add')
        assert response.status_code == 200
        assert b'Ajouter une astreinte' in response.data
    
    def test_add_oncall_post_valid(self, client, test_user):
        """Test l'ajout d'une astreinte valide."""
        data = {
            'user_id': test_user.id,
            'start_date': '2023-12-01'  # Vendredi
        }
        response = client.post('/oncall/add', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b'Astreinte ajoutee' in response.data and b'succes' in response.data
        
        # Verifier que l'astreinte a ete ajoutee
        on_calls = OnCall.query.filter_by(user_id=test_user.id).all()
        assert len(on_calls) == 1
    
    def test_add_oncall_post_invalid_day(self, client, test_user):
        """Test l'ajout d'une astreinte un jour invalide."""
        data = {
            'user_id': test_user.id,
            'start_date': '2023-12-02'  # Samedi
        }
        response = client.post('/oncall/add', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b"L astreinte doit commencer un vendredi" in response.data
    
    def test_delete_oncall_post(self, client, test_oncall):
        """Test la suppression d'une astreinte."""
        response = client.post(f'/oncall/delete/{test_oncall.id}', follow_redirects=True)
        assert response.status_code == 200
        assert b'Astreinte supprimee' in response.data and b'succes' in response.data
        
        # Verifier que l'astreinte a ete supprimee
        oncall = OnCall.query.get(test_oncall.id)
        assert oncall is None


class TestLeaveRoutes:
    """Tests pour les routes des conges."""
    
    def test_add_leave_get(self, client, test_user):
        """Test l'affichage du formulaire d'ajout de conge."""
        response = client.get('/leave/add')
        assert response.status_code == 200
        assert b'Ajouter un conge' in response.data
    
    def test_add_leave_post_valid(self, client, test_user):
        """Test l'ajout d'un conge valide."""
        data = {
            'user_id': test_user.id,
            'start_date': '2023-12-20',
            'end_date': '2023-12-25',
            'reason': 'Test Leave'
        }
        response = client.post('/leave/add', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b'Conge ajoute' in response.data and b'succes' in response.data
        
        # Verifier que le conge a ete ajoute
        leaves = Leave.query.filter_by(user_id=test_user.id).all()
        assert len(leaves) == 1
    
    def test_add_leave_post_invalid_dates(self, client, test_user):
        """Test l'ajout d'un conge avec des dates invalides."""
        data = {
            'user_id': test_user.id,
            'start_date': '2023-12-25',
            'end_date': '2023-12-20',  # Date de fin avant la date de debut
            'reason': 'Test Leave'
        }
        response = client.post('/leave/add', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b'La date de debut doit etre anterieure a la date de fin' in response.data
    
    def test_delete_leave_post(self, client, test_leave):
        """Test la suppression d'un conge."""
        response = client.post(f'/leave/delete/{test_leave.id}', follow_redirects=True)
        assert response.status_code == 200
        assert b'Conge supprime' in response.data and b'succes' in response.data
        
        # Verifier que le conge a ete supprime
        leave = Leave.query.get(test_leave.id)
        assert leave is None


class TestAdminRoutes:
    """Tests pour les routes admin."""
    
    def test_list_groups(self, client):
        """Test l'affichage de la liste des groupes."""
        response = client.get('/admin/groups')
        assert response.status_code == 200
        assert b'Gestion des groupes' in response.data
    
    def test_add_group_post_valid(self, client):
        """Test l'ajout d'un groupe valide."""
        data = {
            'name': 'Nouveau Groupe',
            'is_part_of_schedule': 'on',
            'is_part_of_oncall': 'on'
        }
        response = client.post('/admin/groups/add', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b'Groupe ajoute' in response.data and b'succes' in response.data
        
        # Verifier que le groupe a ete ajoute
        group = Group.query.filter_by(name='Nouveau Groupe').first()
        assert group is not None
    
    def test_add_group_post_invalid(self, client):
        """Test l'ajout d'un groupe sans nom."""
        data = {
            'name': '',
            'is_part_of_schedule': 'on',
            'is_part_of_oncall': 'on'
        }
        response = client.post('/admin/groups/add', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b'Le nom du groupe est obligatoire' in response.data
    
    def test_delete_group_post(self, client, test_group):
        """Test la suppression d'un groupe."""
        response = client.post(f'/admin/groups/delete/{test_group.id}', follow_redirects=True)
        assert response.status_code == 200
        assert b'Groupe supprime' in response.data and b'succes' in response.data
        
        # Verifier que le groupe a ete supprime
        group = Group.query.get(test_group.id)
        assert group is None
    
    def test_list_users(self, client):
        """Test l'affichage de la liste des utilisateurs."""
        response = client.get('/admin/users')
        assert response.status_code == 200
        assert b'Gestion des utilisateurs' in response.data
    
    def test_add_user_post_valid(self, client, test_group):
        """Test l'ajout d'un utilisateur valide."""
        data = {
            'name': 'Nouvel Utilisateur',
            'email': 'nouvel@example.com',
            'group_id': test_group.id
        }
        response = client.post('/admin/users/add', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b'Utilisateur ajoute' in response.data and b'succes' in response.data
        
        # Verifier que l'utilisateur a ete ajoute
        user = User.query.filter_by(email='nouvel@example.com').first()
        assert user is not None
    
    def test_delete_user_post(self, client, test_user):
        """Test la suppression d'un utilisateur."""
        response = client.post(f'/admin/users/delete/{test_user.id}', follow_redirects=True)
        assert response.status_code == 200
        assert b'Utilisateur supprime' in response.data and b'succes' in response.data
        
        # Verifier que l'utilisateur a ete supprime
        user = User.query.get(test_user.id)
        assert user is None
