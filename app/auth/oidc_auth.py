"""
Authentification OIDC/SSO pour Leviia Schedule utilisant Authlib.

Ce module implémente l'authentification via OpenID Connect avec des fournisseurs
comme Keycloak, Okta, Auth0, etc. en utilisant la bibliothèque Authlib.

Authlib est une bibliothèque moderne et maintenue pour l'authentification OIDC,
remplaçant l'ancienne bibliothèque flask-oidc.
"""

import logging
from flask import redirect, url_for, session, current_app, flash
from flask_login import login_user, logout_user
from authlib.integrations.flask_client import OAuth
from authlib.oauth2.rfc6749 import OAuth2Token
from datetime import datetime, timedelta
from config_oidc import OIDCConfig
import json

logger = logging.getLogger(__name__)


class OIDCAuthLib:
    """Classe pour gérer l'authentification OIDC avec Authlib."""
    
    def __init__(self, app=None):
        """Initialise l'authentification OIDC avec Authlib."""
        self.app = app
        self.oauth = None
        self.oidc_client = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialise l'application Flask."""
        self.app = app
        self.oauth = OAuth(app)
        self._configure_oauth()
    
    def _configure_oauth(self):
        """Configure le client OAuth/OIDC."""
        if not self.oauth:
            logger.warning("OAuth n'est pas initialisé, impossible de configurer OIDC")
            return
            
        if not OIDCConfig.is_configured():
            logger.warning("OIDC n'est pas configuré, saut de la configuration OAuth. Vérifiez que OIDC_ENABLED=true, OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET et OIDC_REDIRECT_URI sont définis.")
            return
        
        try:
            # Enregistrer le client OIDC avec découverte automatique
            # Authlib va automatiquement charger les endpoints depuis le document de découverte
            issuer_url = OIDCConfig.ISSUER.rstrip('/')
            server_metadata_url = f"{issuer_url}/.well-known/openid-configuration"
            
            logger.info(f"Tentative de configuration OIDC avec issuer: {issuer_url}")
            logger.info(f"URL de découverte: {server_metadata_url}")
            
            # Tester si l'URL de découverte est accessible
            import requests
            try:
                response = requests.get(server_metadata_url, timeout=5)
                response.raise_for_status()
                logger.info("Document de découverte OIDC accessible")
            except requests.RequestException as e:
                logger.error(f"Impossible d'accéder au document de découverte OIDC: {e}")
                logger.error(f"Vérifiez que OIDC_ISSUER={issuer_url} est correct et accessible depuis ce conteneur")
                logger.error(f"Si vous utilisez Docker, assurez-vous que le service oidc-mock est démarré et accessible via le nom de service Docker")
                return

            self.oidc_client = self.oauth.register(
                name='oidc',
                server_metadata_url=server_metadata_url,
                client_kwargs={
                    'scope': OIDCConfig.SCOPE,
                },
            )
            
            # Mettre à jour les informations du client avec les credentials
            self.oidc_client.client_id = OIDCConfig.CLIENT_ID
            self.oidc_client.client_secret = OIDCConfig.CLIENT_SECRET
            
            logger.info("Client OIDC Authlib configuré avec succès")
            logger.debug(f"Client ID: {OIDCConfig.CLIENT_ID}")
            logger.debug(f"Issuer: {OIDCConfig.ISSUER}")
            logger.debug(f"Scope: {OIDCConfig.SCOPE}")
            logger.debug(f"Server metadata URL: {server_metadata_url}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la configuration OAuth: {e}")
            self.oidc_client = None
    
    def get_authorization_url(self, state=None, nonce=None):
        """Génère l'URL d'autorisation OIDC."""
        if not self.oidc_client:
            logger.error("Client OIDC non configuré. Vérifiez que la configuration OIDC est correcte.")
            return None
        
        try:
            # Générer un state et un nonce si non fournis
            if state is None:
                state = self._generate_state()
            if nonce is None:
                nonce = self._generate_nonce()
            
            # Stocker le state et le nonce dans la session
            session['oidc_state'] = state
            session['oidc_nonce'] = nonce
            
            # Utiliser l'endpoint d'autorisation découvert automatiquement
            # Authlib charge les endpoints depuis le document de découverte
            authorize_endpoint = self.oidc_client.authorize_url
            
            from urllib.parse import urlencode
            
            params = {
                'response_type': 'code',
                'client_id': OIDCConfig.CLIENT_ID,
                'redirect_uri': OIDCConfig.REDIRECT_URI,
                'scope': OIDCConfig.SCOPE,
                'state': state,
                'nonce': nonce,
            }
            
            return f"{authorize_endpoint}?{urlencode(params)}"
                
        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'URL d'autorisation: {e}")
            return None
    
    def _generate_state(self):
        """Génère un state aléatoire."""
        import secrets
        return secrets.token_urlsafe(32)
    
    def _generate_nonce(self):
        """Génère un nonce aléatoire."""
        import secrets
        return secrets.token_urlsafe(32)
    
    def exchange_code_for_token(self, code):
        """
        Échange le code d'autorisation contre un token OIDC.
        """
        if not self.oidc_client:
            logger.error("Client OIDC non configuré")
            return None
        
        try:
            logger.info("Échange du code contre un token OIDC")
            
            # Utiliser requests pour échanger le code directement
            # car nous ne sommes pas dans un contexte de requête Flask
            import requests
            
            token_endpoint = self.oidc_client.access_token_url
            
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
            
            response = requests.post(token_endpoint, data=data, headers=headers, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            
            logger.info("Token OIDC obtenu avec succès")
            return token_data
                
        except Exception as e:
            logger.error(f"Erreur lors de l'échange du code contre un token: {e}")
            return None
    
    def get_user_info(self, access_token):
        """Récupère les informations utilisateur depuis le fournisseur OIDC."""
        if not self.oidc_client:
            logger.error("Client OIDC non configuré")
            return None
        
        try:
            logger.info("Récupération des informations utilisateur OIDC")
            
            # Utiliser le client OIDC pour récupérer les informations utilisateur
            # Authlib's parse_id_token peut être utilisé pour décoder le token
            # Mais pour userinfo, nous devons faire une requête HTTP
            import requests
            
            userinfo_endpoint = self.oidc_client.userinfo_endpoint
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json',
            }
            
            response = requests.get(userinfo_endpoint, headers=headers, timeout=10)
            response.raise_for_status()
            
            user_info = response.json()
            
            logger.info("Informations utilisateur OIDC récupérées avec succès")
            logger.debug(f"User info: {user_info}")
            return user_info
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations utilisateur: {e}")
            return None
    
    def verify_token(self, token_data):
        """Vérifie la validité du token OIDC."""
        if not token_data:
            return False
        
        # Vérifier l'expiration
        expires_at = token_data.get('expires_at')
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
        # Vérifier l'état
        state = request.args.get('state')
        if not state or state != session.get('oidc_state'):
            logger.error("State OIDC invalide")
            flash("Erreur d'authentification: state invalide", "danger")
            return None
        
        # Vérifier le code
        code = request.args.get('code')
        if not code:
            error = request.args.get('error', 'Code manquant')
            error_description = request.args.get('error_description', '')
            logger.error(f"Erreur OIDC: {error} - {error_description}")
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
oidc_auth = OIDCAuthLib()
OIDCAuth = OIDCAuthLib
