#!/usr/bin/env python3
"""
创建管理员用户脚本
Create Admin User Script
"""

from app import create_app, db
from app.models.user import User
from werkzeug.security import generate_password_hash

def create_admin_user():
    """创建管理员用户"""
    app = create_app()
    
    with app.app_context():
        # 检查是否已存在管理员用户
        existing_admin = User.query.filter_by(username='admin').first()
        if existing_admin:
            print("管理员用户已存在！")
            return
        
        # 创建管理员用户
        admin = User(
            username='admin',
            email='admin@yanling.ctf',
            password_hash=generate_password_hash('admin123'),
            is_admin=True,
            is_verified=True
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print("管理员用户创建成功！")
        print("用户名: admin")
        print("密码: admin123")
        print("邮箱: admin@yanling.ctf")

if __name__ == '__main__':
    create_admin_user()