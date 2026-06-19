"""
Décorateurs pour la gestion des rôles et permissions.
"""
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user, login_required


def admin_required(f):
    """
    Décorateur pour vérifier que l'utilisateur est administrateur.
    Redirige vers la page d'accueil avec un message si non autorisé.
    """
    @login_required
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('❌ Accès refusé : vous devez être administrateur.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """
    Décorateur générique pour vérifier que l'utilisateur a un rôle spécifique.
    
    Args:
        *roles: Liste des rôles autorisés (ex: 'admin', 'user')
    
    Utilisation:
        @role_required('admin')
        def admin_route():
            ...
    """
    def decorator(f):
        @login_required
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Pour l'instant, on gère admin vs user
            # L'admin a tous les droits
            if 'admin' in roles and current_user.is_admin:
                return f(*args, **kwargs)
            
            # Si user est requis et l'utilisateur est connecté
            if 'user' in roles and current_user.is_authenticated:
                return f(*args, **kwargs)
            
            flash('Acces refuse : permissions insuffisantes.', 'danger')
            return redirect(url_for('index'))
        return decorated_function
    return decorator


def user_can_edit(user_id):
    """
    Décorateur pour vérifier que l'utilisateur peut éditer une ressource.
    L'admin peut tout éditer, un utilisateur normal ne peut éditer que ses propres ressources.
    
    Args:
        user_id: L'ID de l'utilisateur propriétaire de la ressource
    
    Utilisation:
        @user_can_edit('user_id')
        def edit_shift(user_id):
            ...
    """
    def decorator(f):
        @login_required
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Récupérer l'user_id depuis les args ou kwargs
            func_user_id = None
            
            # Chercher dans kwargs d'abord
            if user_id in kwargs:
                func_user_id = kwargs[user_id]
            # Sinon chercher dans args (positionnel)
            elif len(args) > 0:
                # Si user_id est un index
                if isinstance(user_id, int):
                    if user_id < len(args):
                        func_user_id = args[user_id]
                # Si user_id est un nom de paramètre
                else:
                    # On ne peut pas savoir la position, donc on utilise kwargs
                    pass
            
            # Si on n'a pas trouvé l'user_id, on autorise (cas des routes sans user_id)
            if func_user_id is None:
                return f(*args, **kwargs)
            
            # Vérifier les permissions
            if current_user.is_admin or current_user.id == func_user_id:
                return f(*args, **kwargs)
            
            flash('❌ Accès refusé : vous ne pouvez modifier que vos propres données.', 'danger')
            return redirect(url_for('index'))
        return decorated_function
    return decorator


def user_can_delete(resource_type, user_id_param='user_id'):
    """
    Décorateur pour vérifier que l'utilisateur peut supprimer une ressource.
    
    Args:
        resource_type: Type de ressource ('shift', 'oncall', 'leave')
        user_id_param: Nom du paramètre contenant l'user_id
    
    Utilisation:
        @user_can_delete('shift', 'user_id')
        def delete_shift(shift_id):
            ...
    """
    def decorator(f):
        @login_required
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Pour les routes de suppression, on vérifie l'user_id de la ressource
            # On suppose que la fonction va récupérer la ressource et vérifier son user_id
            # On ne peut pas faire la vérification ici sans accéder à la DB
            # Donc on laisse la vérification dans la route elle-même
            return f(*args, **kwargs)
        return decorated_function
    return decorator
