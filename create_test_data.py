#!/usr/bin/env python3
"""
创建测试数据脚本
用于为雁翎CTF平台创建测试用的用户、题目、分类等数据
"""

import os
import sys
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app, db
from app.models import User, Team, Challenge, Category, Submission


def create_test_data():
    """创建测试数据"""
    app = create_app()
    
    with app.app_context():
        print("开始创建测试数据...")
        
        # 创建分类
        categories_data = [
            {"name": "Web", "description": "Web安全相关题目", "color": "#007bff"},
            {"name": "Crypto", "description": "密码学相关题目", "color": "#28a745"},
            {"name": "Pwn", "description": "二进制漏洞利用题目", "color": "#dc3545"},
            {"name": "Reverse", "description": "逆向工程题目", "color": "#6f42c1"},
            {"name": "Misc", "description": "杂项题目", "color": "#fd7e14"}
        ]
        
        categories = {}
        for cat_data in categories_data:
            category = Category.query.filter_by(name=cat_data["name"]).first()
            if not category:
                category = Category(
                    name=cat_data["name"],
                    description=cat_data["description"],
                    color=cat_data["color"]
                )
                db.session.add(category)
                print(f"创建分类: {cat_data['name']}")
            categories[cat_data["name"]] = category
        
        db.session.commit()
        
        # 创建测试题目
        challenges_data = [
            {
                "name": "简单的Web题目",
                "description": "这是一个简单的Web安全题目，适合初学者练习。\n\n题目描述：\n找到隐藏在网页中的flag。",
                "category": "Web",
                "points": 100,
                "flag": "flag{welcome_to_web_security}",
                "hints": ["查看网页源代码", "注意HTML注释"]
            },
            {
                "name": "SQL注入入门",
                "description": "学习SQL注入的基础知识。\n\n题目描述：\n绕过登录验证，获取管理员权限。",
                "category": "Web",
                "points": 200,
                "flag": "flag{sql_injection_basic}",
                "hints": ["尝试万能密码", "观察SQL查询语句的构造"]
            },
            {
                "name": "凯撒密码",
                "description": "经典的凯撒密码解密题目。\n\n密文：IODJ{FDHVDU_FLSKHU_LV_HDV\\}",
                "category": "Crypto",
                "points": 50,
                "flag": "flag{caesar_cipher_is_easy}",
                "hints": ["尝试不同的偏移量", "凯撒密码是替换密码的一种"]
            },
            {
                "name": "Base64解码",
                "description": "简单的Base64编码解密。\n\n密文：ZmxhZ3tiYXNlNjRfaXNfZWFzeX0=",
                "category": "Crypto",
                "points": 30,
                "flag": "flag{base64_is_easy}",
                "hints": ["这是Base64编码", "使用在线工具或命令行解码"]
            },
            {
                "name": "栈溢出入门",
                "description": "学习栈溢出的基本原理。\n\n下载附件，分析二进制文件并获取shell。",
                "category": "Pwn",
                "points": 300,
                "flag": "flag{stack_overflow_pwn}",
                "hints": ["分析程序的栈结构", "寻找缓冲区溢出点", "构造ROP链"]
            },
            {
                "name": "简单逆向",
                "description": "逆向工程入门题目。\n\n分析给定的可执行文件，找出正确的输入。",
                "category": "Reverse",
                "points": 150,
                "flag": "flag{reverse_engineering}",
                "hints": ["使用反汇编工具", "分析程序逻辑", "注意字符串比较"]
            },
            {
                "name": "隐写术",
                "description": "图片隐写术题目。\n\n在给定的图片中找到隐藏的信息。",
                "category": "Misc",
                "points": 120,
                "flag": "flag{steganography_hidden}",
                "hints": ["使用binwalk分析文件", "检查图片的元数据", "尝试LSB隐写"]
            },
            {
                "name": "网络流量分析",
                "description": "分析网络数据包，找出敏感信息。\n\n使用Wireshark分析给定的pcap文件。",
                "category": "Misc",
                "points": 180,
                "flag": "flag{network_forensics}",
                "hints": ["过滤HTTP流量", "查看POST请求", "注意Base64编码的数据"]
            }
        ]
        
        for chall_data in challenges_data:
            challenge = Challenge.query.filter_by(name=chall_data["name"]).first()
            if not challenge:
                challenge = Challenge(
                    name=chall_data["name"],
                    description=chall_data["description"],
                    category=categories[chall_data["category"]],
                    points=chall_data["points"],
                    flag=chall_data["flag"],
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                db.session.add(challenge)
                db.session.flush()  # 获取challenge的ID
                
                # 创建提示
                for i, hint_content in enumerate(chall_data["hints"]):
                    from app.models import Hint
                    hint = Hint(
                        challenge_id=challenge.id,
                        content=hint_content,
                        cost=10 * (i + 1),  # 提示费用递增
                        order=i + 1
                    )
                    db.session.add(hint)
                
                print(f"创建题目: {chall_data['name']}")
        
        db.session.commit()
        
        # 创建测试用户
        users_data = [
            {
                "username": "testuser1",
                "email": "test1@example.com",
                "password": "password123",
                "nickname": "测试用户1"
            },
            {
                "username": "testuser2", 
                "email": "test2@example.com",
                "password": "password123",
                "nickname": "测试用户2"
            },
            {
                "username": "player1",
                "email": "player1@example.com", 
                "password": "player123",
                "nickname": "选手一号"
            },
            {
                "username": "player2",
                "email": "player2@example.com",
                "password": "player123", 
                "nickname": "选手二号"
            }
        ]
        
        test_users = []
        for user_data in users_data:
            user = User.query.filter_by(username=user_data["username"]).first()
            if not user:
                user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    password_hash=generate_password_hash(user_data["password"]),
                    nickname=user_data["nickname"],
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                db.session.add(user)
                test_users.append(user)
                print(f"创建用户: {user_data['username']}")
        
        db.session.commit()
        
        # 创建测试团队
        teams_data = [
            {
                "name": "测试团队A",
                "description": "这是一个测试团队",
                "captain_username": "testuser1"
            },
            {
                "name": "测试团队B", 
                "description": "另一个测试团队",
                "captain_username": "player1"
            }
        ]
        
        for team_data in teams_data:
            team = Team.query.filter_by(name=team_data["name"]).first()
            if not team:
                captain = User.query.filter_by(username=team_data["captain_username"]).first()
                if captain:
                    team = Team(
                        name=team_data["name"],
                        description=team_data["description"],
                        captain_id=captain.id,
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(team)
                    captain.team = team
                    print(f"创建团队: {team_data['name']}")
        
        db.session.commit()
        
        # 创建一些测试提交记录
        challenges = Challenge.query.all()
        users = User.query.filter(User.username.in_(['testuser1', 'testuser2', 'player1'])).all()
        
        if challenges and users:
            # 为每个用户创建一些解题记录
            for user in users:
                # 随机解决一些简单题目
                easy_challenges = [c for c in challenges if c.points <= 100]
                for i, challenge in enumerate(easy_challenges[:2]):  # 每人解决前2道简单题
                    submission = Submission(
                        user_id=user.id,
                        challenge_id=challenge.id,
                        submitted_flag=challenge.flag,
                        is_correct=True,
                        points_awarded=challenge.points,
                        created_at=datetime.utcnow() - timedelta(days=i+1)
                    )
                    db.session.add(submission)
                    print(f"创建解题记录: {user.username} -> {challenge.name}")
        
        db.session.commit()
        
        print("\n测试数据创建完成！")
        print("\n创建的数据包括:")
        print(f"- 分类: {len(categories_data)} 个")
        print(f"- 题目: {len(challenges_data)} 个") 
        print(f"- 用户: {len(users_data)} 个")
        print(f"- 团队: {len(teams_data)} 个")
        print("\n测试账户信息:")
        print("管理员账户: admin / admin123")
        for user_data in users_data:
            print(f"测试用户: {user_data['username']} / {user_data['password']}")


if __name__ == "__main__":
    create_test_data()