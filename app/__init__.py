from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import Config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()


def create_app(config_class=Config):
    # 设置静态文件和模板文件路径
    static_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static')
    template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    
    app = Flask(__name__, 
                static_folder=static_folder,
                template_folder=template_folder)
    app.config.from_object(config_class)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.views.auth import auth_bp
    from app.views.main import main_bp
    from app.views.challenges import challenges_bp
    from app.views.teams import teams_bp
    from app.views.admin import admin_bp
    from app.views.dashboard import dashboard_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(challenges_bp)
    app.register_blueprint(teams_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(dashboard_bp)
    
    # 注册模板全局函数
    from app.utils.timezone import format_beijing_time
    app.jinja_env.globals['format_beijing_time'] = format_beijing_time
    
    # 注册错误处理器
    from app.utils.error_handler import register_error_handlers
    register_error_handlers(app)
    
    return app