"""
Routes module for Leviia Schedule.

This module contains all the Flask blueprints and route handlers for the
application. Routes are organized by functional area.

Blueprints:
- auth: Authentication routes
- main: Main application routes (to be split into domain-specific files)
- admin: Administration routes
- export: Export routes (ICS, etc.)
"""

# Import all route modules to register them
from app.routes import auth, main, admin, export
