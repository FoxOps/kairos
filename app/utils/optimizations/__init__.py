"""
Module d'optimisations pour Leviia Schedule.

Un seul décorateur actif : eager_load, utilisé par les routes admin
(shift_type, user, group) et le dashboard pour éviter le N+1 en chargeant
les relations SQLAlchemy en une seule requête.

Utilisation :
    from app.utils.optimizations import eager_load

    @eager_load(User, ['group'])
    def get_user_with_group(user_id):
        return User.query.get(user_id)
"""

from collections.abc import Callable
from functools import wraps

from sqlalchemy.orm import Query, joinedload, selectinload


def eager_load(
    model_class: type,
    relationships: list[str] | None = None,
    strategy: str = "joinedload",
):
    """
    Décorateur pour charger les relations de manière eager (éviter le N+1).

    Args:
        model_class: Classe du modèle
        relationships: Liste des relations à charger
        strategy: Stratégie de chargement ('joinedload' ou 'selectinload')

    Exemple:
        @eager_load(User, ['shifts', 'on_calls', 'leaves'])
        def get_user(user_id):
            return User.query.get(user_id)
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Appeler la fonction pour obtenir la requête ou le résultat
            result = f(*args, **kwargs)

            # Si c'est une requête, appliquer le eager loading
            if isinstance(result, Query):
                if relationships:
                    for rel in relationships:
                        if strategy == "selectinload":
                            result = result.options(
                                selectinload(getattr(model_class, rel))
                            )
                        else:
                            result = result.options(
                                joinedload(getattr(model_class, rel))
                            )
                return result

            # Si c'est un objet modèle, charger les relations
            if isinstance(result, model_class):
                if relationships:
                    for rel in relationships:
                        getattr(result, rel)  # Cela déclenche le lazy loading
                return result

            return result

        return wrapped

    return decorator


__all__ = ["eager_load"]
