"""Routes pour la gestion de l'internationalisation (i18n)."""

from flask import Blueprint, request, make_response, redirect, url_for, session
from flask_babel import gettext as _
from app import app

# Créer un Blueprint pour les routes i18n
i18n_bp = Blueprint('i18n', __name__, url_prefix='/i18n')


@i18n_bp.route('/set_language/<lang>')
def set_language(lang):
    """Définit la langue de l'utilisateur."""
    # Vérifier que la langue est supportée
    from config import Config
    
    if lang not in Config.LANGUAGES:
        lang = Config.BABEL_DEFAULT_LOCALE
    
    # Stocker la langue dans la session
    session['language'] = lang
    
    # Rediriger vers la page précédente ou vers l'accueil
    referrer = request.referrer
    if referrer:
        return redirect(referrer)
    else:
        return redirect(url_for('index'))


@i18n_bp.route('/language/<lang>')
def language_redirect(lang):
    """Redirige vers la page d'accueil avec la langue spécifiée."""
    # Vérifier que la langue est supportée
    from config import Config
    
    if lang not in Config.LANGUAGES:
        lang = Config.BABEL_DEFAULT_LOCALE
    
    # Créer une réponse de redirection
    response = make_response(redirect(url_for('index')))
    response.set_cookie('language', lang, max_age=31536000)  # 1 an
    
    return response


def get_locale():
    """Détermine la locale à utiliser pour l'utilisateur."""
    from config import Config
    
    # Vérifier d'abord la session
    if 'language' in session:
        return session['language']
    
    # Puis vérifier les cookies
    if request.cookies.get('language'):
        return request.cookies.get('language')
    
    # Puis vérifier l'en-tête Accept-Language du navigateur
    if request.accept_languages:
        best = request.accept_languages.best_match(Config.LANGUAGES)
        if best:
            return best
    
    # Enfin, retourner la langue par défaut
    return Config.BABEL_DEFAULT_LOCALE


# Enregistrer le Blueprint
app.register_blueprint(i18n_bp)
