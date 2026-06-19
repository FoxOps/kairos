"""
Tests pour les décorateurs de permissions.
"""
import pytest


class TestDecoratorImports:
    """Tests pour l'import des décorateurs."""
    
    def test_admin_required_import(self):
        """Test que le décorateur admin_required peut être importé."""
        from app.utils.decorators import admin_required
        assert callable(admin_required)
    
    def test_role_required_import(self):
        """Test que le décorateur role_required peut être importé."""
        from app.utils.decorators import role_required
        assert callable(role_required)
    
    def test_user_can_edit_import(self):
        """Test que le décorateur user_can_edit peut être importé."""
        from app.utils.decorators import user_can_edit
        assert callable(user_can_edit)
    
    def test_user_can_delete_import(self):
        """Test que le décorateur user_can_delete peut être importé."""
        from app.utils.decorators import user_can_delete
        assert callable(user_can_delete)


class TestDecoratorProperties:
    """Tests pour les propriétés des décorateurs."""
    
    def test_decorator_preserves_function_name(self, app):
        """Test que le décorateur préserve le nom de la fonction."""
        from app.utils.decorators import admin_required
        
        @admin_required
        def test_function():
            return 'Test', 200
        
        assert test_function.__name__ == 'test_function'
    
    def test_decorator_preserves_function_docstring(self, app):
        """Test que le décorateur préserve le docstring de la fonction."""
        from app.utils.decorators import admin_required
        
        @admin_required
        def test_function():
            """This is a test function."""
            return 'Test', 200
        
        assert test_function.__doc__ == 'This is a test function.'
    
    def test_admin_required_is_callable(self, app):
        """Test que admin_required est callable."""
        from app.utils.decorators import admin_required
        
        @admin_required
        def dummy():
            pass
        
        assert callable(dummy)
    
    def test_role_required_is_callable(self, app):
        """Test que role_required est callable."""
        from app.utils.decorators import role_required
        
        decorated_func = role_required('admin')
        assert callable(decorated_func)
