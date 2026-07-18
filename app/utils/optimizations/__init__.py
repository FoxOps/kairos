"""
Optimizations module for Kairos.

Only one active decorator: eager_load, used by the dashboard to avoid
N+1 by loading SQLAlchemy relationships in a single query (has no
effect on a function that already returns a materialized list rather
than a Query - removed from the admin routes list_users/
list_shift_types/list_groups for that reason).

Usage:
    from app.utils.optimizations import eager_load

    @eager_load(User, ['group'])
    def get_user_with_group(user_id):
        return db.session.get(User, user_id)
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
    Decorator to eagerly load relationships (avoid N+1).

    Args:
        model_class: Model class
        relationships: List of relationships to load
        strategy: Loading strategy ('joinedload' or 'selectinload')

    Example:
        @eager_load(User, ['shifts', 'on_calls', 'leaves'])
        def get_user(user_id):
            return db.session.get(User, user_id)
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Call the function to get the query or the result
            result = f(*args, **kwargs)

            # If it's a query, apply eager loading
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

            # If it's a model instance, load the relationships
            if isinstance(result, model_class):
                if relationships:
                    for rel in relationships:
                        getattr(result, rel)  # This triggers lazy loading
                return result

            return result

        return wrapped

    return decorator


__all__ = ["eager_load"]
