"""
Authentification OIDC/SSO pour Leviia Schedule.

Ce module implémente l'authentification via OpenID Connect avec des fournisseurs
comme Keycloak, Okta, Auth0, etc.
"""

import logging
from flask import redirect, url_for, session, current_app, flash
from flask_login import login_user, logout_user
import requests
import json
from datetime import datetime, timedelta
from config_oidc import OIDCConfig

logger = logging.getLogger(__name__)


class OIDCAuth:
    """Classe pour gérer l'authentification OIDC."""
    
    def __init__(self, app=None):
        """Initialise l'authentification OIDC."""
        self.app = app
        self.discovery_document = None
        self.authorization_endpoint = None
        self.token_endpoint = None
        self.userinfo_endpoint = None
        self.jwks_uri = None
        self._load_discovery_document()
    
    def _load_discovery_document(self):
        """Charge le document de découverte OIDC."""
        if not OIDCConfig.is_configured():
            logger.info("OIDC n'est pas configuré, saut du chargement du document de découverte")
            return
        
        try:
            issuer_url = OIDCConfig.ISSUER.rstrip('/')
            discovery_url = f"{issuer_url}/.well-known/openid-configuration"
            
            logger.info(f"Chargement du document de découverte OIDC depuis: {discovery_url}")
            
            response = requests.get(discovery_url, timeout=10)
            response.raise_for_status()
            
            self.discovery_document = response.json()
            
            # Extraire les endpoints
            self.authorization_endpoint = self.discovery_document.get('authorization_endpoint')
            self.token_endpoint = self.discovery_document.get('token_endpoint')
            self.userinfo_endpoint = self.discovery_document.get('userinfo_endpoint')
            self.jwks_uri = self.discovery_document.get('jwks_uri')
            
            logger.info("Document de découverte OIDC chargé avec succès")
            logger.debug(f"Authorization endpoint: {self.authorization_endpoint}")
            logger.debug(f"Token endpoint: {self.token_endpoint}")
            logger.debug(f"Userinfo endpoint: {self.userinfo_endpoint}")
            
        except requests.RequestException as e:
            logger.error(f"Erreur lors du chargement du document de découverte OIDC: {e}")
            self.discovery_document = None
            self.authorization_endpoint = None
            self.token_endpoint = None
            self.userinfo_endpoint = None
            self.jwks_uri = None
        except json.JSONDecodeError as e:
            logger.error(f"Erreur lors du décodage du document de découverte OIDC: {e}")
            self.discovery_document = None
    
    def get_authorization_url(self, state=None, nonce=None):
        """Génère l'URL d'autorisation OIDC."""
        if not self.authorization_endpoint:
            logger.error("Authorization endpoint non disponible")
            return None
        
        from urllib.parse import urlencode
        
        # Générer un state et un nonce si non fournis
        if state is None:
            state = self._generate_state()
        if nonce is None:
            nonce = self._generate_nonce()
        
        # Stocker le state et le nonce dans la session
        session['oidc_state'] = state
        session['oidc_nonce'] = nonce
        
        params = {
            'response_type': 'code',
            'client_id': OIDCConfig.CLIENT_ID,
            'redirect_uri': OIDCConfig.REDIRECT_URI,
            'scope': OIDCConfig.SCOPE,
            'state': state,
            'nonce': nonce,
        }
        
        return f"{self.authorization_endpoint}?{urlencode(params)}"
    
    def _generate_state(self):
        """Génère un state aléatoire."""
        import secrets
        return secrets.token_urlsafe(32)
    
    def _generate_nonce(self):
        """Génère un nonce aléatoire."""
        import secrets
        return secrets.token_urlsafe(32)
    
    def exchange_code_for_token(self, code):
        """Échange le code d'autorisation contre un token OIDC."""
        if not self.token_endpoint:
            logger.error("Token endpoint non disponible")
            return None
        
        try:
            data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': OIDCConfig.REDIRECT_URI,
                'client_id': OIDCConfig.CLIENT_ID,
                'client_secret': OIDCConfig.CLIENT_SECRET,
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            
            logger.info("Échange du code contre un token OIDC")
            
            response = requests.post(self.token_endpoint, data=data, headers=headers, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            
            logger.info("Token OIDC obtenu avec succès")
            
            return token_data
            
        except requests.RequestException as e:
            logger.error(f"Erreur lors de l'échange du code contre un token: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Erreur lors du décodage de la réponse du token: {e}")
            return None
    
    def get_user_info(self, access_token):
        """Récupère les informations utilisateur depuis le fournisseur OIDC."""
        if not self.userinfo_endpoint:
            logger.error("Userinfo endpoint non disponible")
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json',
            }
            
            logger.info("Récupération des informations utilisateur OIDC")
            
            response = requests.get(self.userinfo_endpoint, headers=headers, timeout=10)
            response.raise_for_status()
            
            user_info = response.json()
            
            logger.info("Informations utilisateur OIDC récupérées avec succès")
            logger.debug(f"User info: {user_info}")
            
            return user_info
            
        except requests.RequestException as e:
            logger.error(f"Erreur lors de la récupération des informations utilisateur: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Erreur lors du décodage des informations utilisateur: {e}")
            return None
    
    def verify_token(self, token_data):
        """Vérifie la validité du token OIDC."""
        # Implémentation simplifiée - dans une vraie application, 
        # vous devriez vérifier la signature, l'expiration, etc.
        
        if not token_data:
            return False
        
        # Vérifier l'expiration
        expires_at = token_data.get('exp')
        if expires_at:
            import time
            if time.time() > expires_at:
                logger.warning("Token OIDC expiré")
                return False
        
        return True
    
    def extract_user_info_from_token(self, token_data, user_info=None):
        """Extrait les informations utilisateur du token OIDC."""
        user_data = {}
        
        # Si user_info est fourni, l'utiliser
        if user_info:
            # Extraire l'email
            email_claim = OIDCConfig.EMAIL_CLAIM
            if email_claim in user_info:
                user_data['email'] = user_info[email_claim]
            
            # Extraire le nom
            name_claim = OIDCConfig.NAME_CLAIM
            if name_claim in user_info:
                user_data['name'] = user_info[name_claim]
            
            # Extraire le nom d'utilisateur
            username_claim = OIDCConfig.USERNAME_CLAIM
            if username_claim in user_info:
                user_data['username'] = user_info[username_claim]
            
            # Extraire les groupes si configuré
            groups_claim = OIDCConfig.GROUPS_CLAIM
            if groups_claim and groups_claim in user_info:
                user_data['groups'] = user_info[groups_claim]
            
            # Extraire les rôles si configuré
            roles_claim = OIDCConfig.ROLES_CLAIM
            if roles_claim and roles_claim in user_info:
                user_data['roles'] = user_info[roles_claim]
        
        # Sinon, essayer d'extraire depuis le token lui-même
        elif token_data:
            # Décoder le payload du token (sans vérification de signature)
            import base64
            import json
            
            id_token = token_data.get('id_token') or token_data.get('access_token')
            if id_token:
                try:
                    # Décoder le payload (partie du milieu du JWT)
                    parts = id_token.split('.')
                    if len(parts) >= 2:
                        # Ajouter un padding si nécessaire
                        payload = parts[1]
                        payload += '=' * (4 - len(payload) % 4)
                        decoded = base64.urlsafe_b64decode(payload)
                        token_payload = json.loads(decoded)
                        
                        # Extraire les informations
                        email_claim = OIDCConfig.EMAIL_CLAIM
                        if email_claim in token_payload:
                            user_data['email'] = token_payload[email_claim]
                        
                        name_claim = OIDCConfig.NAME_CLAIM
                        if name_claim in token_payload:
                            user_data['name'] = token_payload[name_claim]
                        
                        username_claim = OIDCConfig.USERNAME_CLAIM
                        if username_claim in token_payload:
                            user_data['username'] = token_payload[username_claim]
                        
                        groups_claim = OIDCConfig.GROUPS_CLAIM
                        if groups_claim and groups_claim in token_payload:
                            user_data['groups'] = token_payload[groups_claim]
                        
                        roles_claim = OIDCConfig.ROLES_CLAIM
                        if roles_claim and roles_claim in token_payload:
                            user_data['roles'] = token_payload[roles_claim]
                            
                except Exception as e:
                    logger.error(f"Erreur lors du décodage du token: {e}")
        
        return user_data
    
    def handle_oauth_callback(self, request):
        """Gère le callback OIDC après l'authentification."""
        from flask import request as flask_request
        
        # Vérifier l'état
        state = flask_request.args.get('state')
        if not state or state != session.get('oidc_state'):
            logger.error("State OIDC invalide")
            flash("Erreur d'authentification: state invalide", "danger")
            return None
        
        # Vérifier le code
        code = flask_request.args.get('code')
        if not code:
            error = flask_request.args.get('error', 'Code manquant')
            logger.error(f"Erreur OIDC: {error}")
            flash(f"Erreur d'authentification: {error}", "danger")
            return None
        
        # Échanger le code contre un token
        token_data = self.exchange_code_for_token(code)
        if not token_data:
            logger.error("Échec de l'échange du code contre un token")
            flash("Erreur d'authentification: échec de l'échange du code", "danger")
            return None
        
        # Vérifier le token
        if not self.verify_token(token_data):
            logger.error("Token OIDC invalide")
            flash("Erreur d'authentification: token invalide", "danger")
            return None
        
        # Récupérer les informations utilisateur
        access_token = token_data.get('access_token')
        user_info = None
        if access_token:
            user_info = self.get_user_info(access_token)
        
        # Extraire les informations utilisateur
        user_data = self.extract_user_info_from_token(token_data, user_info)
        
        if not user_data or 'email' not in user_data:
            logger.error("Impossible d'extraire l'email de l'utilisateur OIDC")
            flash("Erreur d'authentification: impossible de récupérer l'email", "danger")
            return None
        
        return user_data
    
    def login_user(self, user_data):
        """Connecte un utilisateur OIDC."""
        from app.models import User, Group
        from app import db
        from app.auth.user_manager import UserManager
        
        user_manager = UserManager()
        
        # Synchroniser ou créer l'utilisateur
        user = user_manager.sync_user_from_oidc(user_data)
        
        if user:
            login_user(user)
            logger.info(f"Utilisateur OIDC connecté: {user.email}")
            return user
        else:
            logger.error(f"Impossible de synchroniser l'utilisateur OIDC: {user_data}")
            return None


# Instance globale
oidc_auth = OIDCAuth()
