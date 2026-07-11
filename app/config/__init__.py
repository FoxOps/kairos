"""
Configuration module for Leviia Schedule.

This module provides modular configuration for different environments:
- Development
- Production
- Testing
"""

from app.config.base import Config
from app.config.development import DevelopmentConfig
from app.config.production import ProductionConfig
from app.config.testing import TestingConfig

__all__ = ['Config', 'DevelopmentConfig', 'ProductionConfig', 'TestingConfig']
