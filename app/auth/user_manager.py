"""
Gestion des utilisateurs pour l'authentification OIDC.

Ce module gère la synchronisation des utilisateurs entre le fournisseur OIDC
et la base de données locale de Leviia Schedule.
"""

import logging
from app.models import User, Group
from app import db
from config_oidc import OIDCConfig

logger = logging.getLogger(__name__)


class UserManager:
    """Classe pour gérer les utilisateurs OIDC."""
    
    def sync_user_from_oidc(self, user_data):
        """Synchronise un utilisateur depuis les données OIDC.
        
        Args:
            user_data: Dictionnaire contenant les informations utilisateur OIDC
            
        Returns:
            User: L'utilisateur synchronisé ou None en cas d'erreur
        """
        if not user_data or 'email' not in user_data:
            logger.error("Données utilisateur OIDC invalides: email manquant")
            return None
        
        email = user_data['email']
        name = user_data.get('name', '')
        username = user_data.get('username', email.split('@')[0])
        
        # Chercher l'utilisateur existant par email
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Mettre à jour l'utilisateur existant
            user.name = name or user.name
            user.username = username or user.username
            
            # Si l'utilisateur n'a pas de mot de passe (utilisateur OIDC), ne pas le modifier
            if not user.password_hash:
                pass  # Les utilisateurs OIDC n'ont pas de mot de passe local
            
            # Synchroniser les groupes si configuré
            if OIDCConfig.GROUPS_CLAIM and 'groups' in user_data:
                self._sync_user_groups(user, user_data['groups'])
            
            # Synchroniser les rôles si configuré
            if OIDCConfig.ROLES_CLAIM and 'roles' in user_data:
                self._sync_user_roles(user, user_data['roles'])
            
            db.session.commit()
            logger.info(f"Mise à jour de l'utilisateur OIDC existant: {email}")
            return user
        else:
            # Créer un nouvel utilisateur
            # Pour les utilisateurs OIDC, on ne définit pas de mot de passe
            # car ils s'authentifient via OIDC
            user = User(
                email=email,
                name=name,
                username=username,
                is_admin=False  # Par défaut, les utilisateurs OIDC ne sont pas admin
            )
            
            # Trouver le groupe par défaut
            default_group = Group.query.filter_by(name="Defaut").first()
            if default_group:
                user.group_id = default_group.id
            
            # Synchroniser les groupes si configuré
            if OIDCConfig.GROUPS_CLAIM and 'groups' in user_data:
                self._sync_user_groups(user, user_data['groups'])
            
            # Synchroniser les rôles si configuré
            if OIDCConfig.ROLES_CLAIM and 'roles' in user_data:
                self._sync_user_roles(user, user_data['roles'])
            
            db.session.add(user)
            db.session.commit()
            logger.info(f"Nouvel utilisateur OIDC créé: {email} (ID: {user.id})")
            return user
    
    def _sync_user_groups(self, user, oidc_groups):
        """Synchronise les groupes de l'utilisateur avec les groupes OIDC.
        
        Args:
            user: Utilisateur à synchroniser
            oidc_groups: Liste des groupes OIDC de l'utilisateur
        """
        if not isinstance(oidc_groups, list):
            oidc_groups = [oidc_groups]
        
        # Pour l'instant, on ne fait que logger les groupes OIDC
        # 1. Créer des groupes locaux correspondant aux groupes OIDC
        logger.info(f"Groupes OIDC pour {user.email}: {oidc_groups}")
        
        # Les groupes OIDC peuvent être utilisés pour des autorisations supplémentaires
    
    def _sync_user_roles(self, user, oidc_roles):
        """Synchronise les rôles de l'utilisateur avec les rôles OIDC.
        
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
        
        # Les rôles OIDC peuvent être utilisés pour des autorisations supplémentaires
