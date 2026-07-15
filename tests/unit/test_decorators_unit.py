"""
Tests unitaires pour les décorateurs sans contexte Flask.
"""

from unittest.mock import Mock

from app.auth.decorators import admin_required, user_owns_resource


class TestAdminRequiredDecorator:
    """Tests unitaires pour admin_required."""

    def test_admin_required_decorator_structure(self):
        """Test que admin_required est un décorateur valide."""

        @admin_required
        def test_function():
            return "test"

        assert callable(test_function)
        assert hasattr(test_function, "__name__")
        assert test_function.__name__ == "test_function"

    def test_admin_required_preserves_docstring(self):
        """Test que admin_required préserve le docstring."""

        @admin_required
        def test_function():
            """Ceci est un docstring."""
            pass

        assert test_function.__doc__ == "Ceci est un docstring."

    def test_admin_required_preserves_function_name(self):
        """Test que admin_required préserve le nom de la fonction."""

        @admin_required
        def my_function():
            pass

        assert my_function.__name__ == "my_function"


class TestUserOwnsResourceDecorator:
    """Tests unitaires pour user_owns_resource."""

    def test_user_owns_resource_decorator_structure(self):
        """Test que user_owns_resource est un décorateur valide."""
        # Créer un mock pour le modèle
        MockModel = Mock()

        @user_owns_resource(MockModel, "resource_id")
        def test_function(resource_id):
            return "test"

        assert callable(test_function)

    def test_user_owns_resource_preserves_metadata(self):
        """Test que user_owns_resource préserve les métadonnées."""
        MockModel = Mock()

        @user_owns_resource(MockModel, "resource_id")
        def test_function(resource_id):
            """Test docstring."""
            pass

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test docstring."

    def test_user_owns_resource_with_custom_attr(self):
        """Test user_owns_resource avec un attribut personnalisé."""
        MockModel = Mock()

        @user_owns_resource(MockModel, "resource_id", user_id_attr="owner_id")
        def test_function(resource_id):
            return "test"

        assert callable(test_function)


class TestDecoratorChaining:
    """Tests pour l'enchaînement de décorateurs."""

    def test_multiple_decorators_can_be_chained(self):
        """Test que plusieurs décorateurs peuvent être enchaînés."""
        MockModel = Mock()

        @user_owns_resource(MockModel, "resource_id")
        @admin_required
        def test_function(resource_id):
            return "test"

        assert callable(test_function)

    def test_decorator_order_preservation(self):
        """Test que l'ordre des décorateurs est préservé."""
        MockModel = Mock()

        @user_owns_resource(MockModel, "resource_id")
        @admin_required
        def test_function(resource_id):
            """Test docstring."""
            pass

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test docstring."
