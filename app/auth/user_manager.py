"""
Gestion des utilisateurs pour l'authentification OIDC.

Ce module gère la synchronisation des utilisateurs entre le fournisseur OIDC
et la base de données locale.
"""

import logging
from app import db
from app.models import User, Group


logger = logging.getLogger(__name__)


class UserManager:
    """Classe pour gérer les utilisateurs OIDC."""
    
    def __init__(self):
        """Initialise le gestionnaire d'utilisateurs."""
        pass
    
    def sync_user_from_oidc(self, user_data):
        """
        Synchronise un utilisateur depuis les données OIDC.
        
        Args:
            user_data: Dictionnaire contenant les informations utilisateur OIDC
                     (email, name, username, groups, roles)
        
        Returns:
            User: L'utilisateur synchronisé ou créé
        """
        if not user_data or 'email' not in user_data:
            logger.error("Données utilisateur OIDC invalides: email manquant")
            return None
        
        email = user_data['email']
        name = user_data.get('name', email.split('@')[0])
        username = user_data.get('username', email)
        
        # Chercher l'utilisateur existant par email
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Mettre à jour les informations de l'utilisateur existant
            logger.info(f"Mise à jour de l'utilisateur OIDC existant: {email}")
            
            # Mettre à jour le nom si différent
            if user.name != name:
                user.name = name
            
            # Mettre à jour le groupe par défaut si nécessaire
            if not user.group_id:
                default_group = Group.query.filter_by(name="Defaut").first()
                if default_group:
                    user.group_id = default_group.id
            
            # Synchroniser les groupes si configuré
            if OIDCConfig.GROUPS_CLAIM and 'groups' in user_data:
                self._sync_user_groups(user, user_data['groups'])
            
            # Synchroniser les rôles si configuré
            if OIDCConfig.ROLES_CLAIM and 'roles' in user_data:
                self._sync_user_roles(user, user_data['roles'])
            
            db.session.commit()
            return user
        else:
            # Créer un nouvel utilisateur
            logger.info(f"Création d'un nouvel utilisateur OIDC: {email}")
            
            # Trouver le groupe par défaut
            default_group = Group.query.filter_by(name="Defaut").first()
            group_id = default_group.id if default_group else 1
            
            # Créer l'utilisateur
            user = User(
                name=name,
                email=email,
                group_id=group_id,
                is_admin=False  # Par défaut, les utilisateurs OIDC ne sont pas admin
            )
            
            # Note: On ne définit pas de mot de passe pour les utilisateurs OIDC
            # car ils s'authentifient via OIDC
            user.password_hash = None
            
            db.session.add(user)
            db.session.commit()
            
            # Synchroniser les groupes si configuré
            if OIDCConfig.GROUPS_CLAIM and 'groups' in user_data:
                self._sync_user_groups(user, user_data['groups'])
            
            # Synchroniser les rôles si configuré
            if OIDCConfig.ROLES_CLAIM and 'roles' in user_data:
                self._sync_user_roles(user, user_data['roles'])
            
            logger.info(f"Nouvel utilisateur OIDC créé: {email} (ID: {user.id})")
            return user
    
    def _sync_user_groups(self, user, oidc_groups):
        """
        Synchronise les groupes de l'utilisateur avec les groupes OIDC.
        
        Args:
            user: Utilisateur à synchroniser
            oidc_groups: Liste des groupes OIDC de l'utilisateur
        """
        if not isinstance(oidc_groups, list):
            oidc_groups = [oidc_groups]
        
        # Pour l'instant, on ne fait que logger les groupes OIDC
        # Dans une implémentation complète, on pourrait:
        # 1. Créer des groupes locaux correspondant aux groupes OIDC
        # 2. Associer l'utilisateur à ces groupes
        logger.info(f"Groupes OIDC pour {user.email}: {oidc_groups}")
        
        # Note: L'application gère les groupes localement via l'interface admin
        # Les groupes OIDC peuvent être utilisés pour des autorisations supplémentaires
    
    def _sync_user_roles(self, user, oidc_roles):
        """
        Synchronise les rôles de l'utilisateur avec les rôles OIDC.
        
        Args:
            user: Utilisateur à synchroniser
            oidc_roles: Liste des rôles OIDC de l'utilisateur
        """
        if not isinstance(oidc_roles, list):
            oidc_roles = [oidc_roles]
        
        # Vérifier si l'utilisateur a le rôle admin
        if 'admin' in [role.lower() for role in oidc_roles]:
            user.is_admin = True
            logger.info(f"Rôle admin attribué à {user.email} via OIDC")
        
        logger.info(f"Rôles OIDC pour {user.email}: {oidc_roles}")
        
        # Note: Les rôles sont gérés localement par l'application
        # Les rôles OIDC peuvent être utilisés pour des autorisations supplémentaires
    
    def get_or_create_user_by_email(self, email, name=None):
        """
        Récupère ou crée un utilisateur par email.
        
        Args:
            email: Email de l'utilisateur
            name: Nom de l'utilisateur (optionnel)
        
        Returns:
            User: L'utilisateur trouvé ou créé
        """
        user = User.query.filter_by(email=email).first()
        
        if user:
            return user
        
        # Créer un nouvel utilisateur
        if not name:
            name = email.split('@')[0]
        
        # Trouver le groupe par défaut
        default_group = Group.query.filter_by(name="Defaut").first()
        group_id = default_group.id if default_group else 1
        
        user = User(
            name=name,
            email=email,
            group_id=group_id,
            is_admin=False
        )
        
        db.session.add(user)
        db.session.commit()
        
        return user
