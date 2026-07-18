"""
Routes module for Kairos.

This module contains all the Flask blueprints and route handlers for the
application. Routes are organized by functional area.

Blueprints (registered explicitly in app/__init__.py::create_app(), via
direct submodule imports - e.g. `from app.routes.auth import auth_bp`):
- auth: Authentication routes
- main: Main application routes (split across multiple files, see
  dashboard_routes.py, shift_routes.py, leave_routes.py, oncall_routes.py)
- admin: Administration routes (split across multiple files, see
  admin_user_routes.py, admin_group_routes.py, etc.)
- export: Export routes (ICS, etc.)
"""
