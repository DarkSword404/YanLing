# Views module
from .auth import auth_bp
from .main import main_bp
from .challenges import challenges_bp
from .teams import teams_bp
from .admin import admin_bp

__all__ = ['auth_bp', 'main_bp', 'challenges_bp', 'teams_bp', 'admin_bp']