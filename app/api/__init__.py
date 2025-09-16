# API模块初始化文件
from .auth import auth_api_bp
from .challenges import challenges_api_bp
from .teams import teams_api_bp
from .admin import admin_api_bp

__all__ = ['auth_api_bp', 'challenges_api_bp', 'teams_api_bp', 'admin_api_bp']