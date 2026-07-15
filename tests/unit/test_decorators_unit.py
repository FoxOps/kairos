"""
Unit tests for the decorators without a Flask context.
"""

from unittest.mock import Mock

from app.auth.decorators import admin_required, user_owns_resource


class TestAdminRequiredDecorator:
    """Unit tests for admin_required."""

    def test_admin_required_decorator_structure(self):
        """Test that admin_required is a valid decorator."""

        @admin_required
        def test_function():
            return "test"

        assert callable(test_function)
        assert hasattr(test_function, "__name__")
        assert test_function.__name__ == "test_function"

    def test_admin_required_preserves_docstring(self):
        """Test that admin_required preserves the docstring."""

        @admin_required
        def test_function():
            """This is a docstring."""
            pass

        assert test_function.__doc__ == "This is a docstring."

    def test_admin_required_preserves_function_name(self):
        """Test that admin_required preserves the function name."""

        @admin_required
        def my_function():
            pass

        assert my_function.__name__ == "my_function"


class TestUserOwnsResourceDecorator:
    """Unit tests for user_owns_resource."""

    def test_user_owns_resource_decorator_structure(self):
        """Test that user_owns_resource is a valid decorator."""
        # Create a mock for the model
        MockModel = Mock()

        @user_owns_resource(MockModel, "resource_id")
        def test_function(resource_id):
            return "test"

        assert callable(test_function)

    def test_user_owns_resource_preserves_metadata(self):
        """Test that user_owns_resource preserves the metadata."""
        MockModel = Mock()

        @user_owns_resource(MockModel, "resource_id")
        def test_function(resource_id):
            """Test docstring."""
            pass

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test docstring."

    def test_user_owns_resource_with_custom_attr(self):
        """Test user_owns_resource with a custom attribute."""
        MockModel = Mock()

        @user_owns_resource(MockModel, "resource_id", user_id_attr="owner_id")
        def test_function(resource_id):
            return "test"

        assert callable(test_function)


class TestDecoratorChaining:
    """Tests for chaining decorators."""

    def test_multiple_decorators_can_be_chained(self):
        """Test that multiple decorators can be chained."""
        MockModel = Mock()

        @user_owns_resource(MockModel, "resource_id")
        @admin_required
        def test_function(resource_id):
            return "test"

        assert callable(test_function)

    def test_decorator_order_preservation(self):
        """Test that decorator order is preserved."""
        MockModel = Mock()

        @user_owns_resource(MockModel, "resource_id")
        @admin_required
        def test_function(resource_id):
            """Test docstring."""
            pass

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test docstring."
