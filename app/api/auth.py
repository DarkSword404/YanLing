from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import db
from app.models import User, Team
import re

auth_api_bp = Blueprint('auth_api', __name__, url_prefix='/api/auth')


@auth_api_bp.route('/login', methods=['POST'])
def login():
    """用户登录API"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请提供JSON数据'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    remember = data.get('remember', False)
    
    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    
    # 支持用户名或邮箱登录
    user = User.query.filter(
        (User.username == username) | (User.email == username)
    ).first()
    
    if not user or not user.check_password(password):
        return jsonify({'error': '用户名或密码错误'}), 401
    
    if not user.is_active:
        return jsonify({'error': '账户已被禁用'}), 403
    
    login_user(user, remember=remember)
    
    return jsonify({
        'message': '登录成功',
        'user': user.to_dict()
    })


@auth_api_bp.route('/register', methods=['POST'])
def register():
    """用户注册API"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请提供JSON数据'}), 400
    
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')
    
    # 验证输入
    errors = []
    
    if not username or len(username) < 3:
        errors.append('用户名至少3个字符')
    elif not re.match(r'^[a-zA-Z0-9_]+$', username):
        errors.append('用户名只能包含字母、数字和下划线')
    elif User.query.filter_by(username=username).first():
        errors.append('用户名已存在')
    
    if not email:
        errors.append('邮箱不能为空')
    elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        errors.append('邮箱格式不正确')
    elif User.query.filter_by(email=email).first():
        errors.append('邮箱已被注册')
    
    if not password or len(password) < 6:
        errors.append('密码至少6个字符')
    elif password != confirm_password:
        errors.append('两次输入的密码不一致')
    
    if errors:
        return jsonify({'errors': errors}), 400
    
    # 创建用户
    user = User(
        username=username,
        email=email
    )
    user.set_password(password)
    
    try:
        db.session.add(user)
        db.session.commit()
        
        # 自动登录
        login_user(user)
        
        return jsonify({
            'message': '注册成功',
            'user': user.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': '注册失败，请重试'}), 500


@auth_api_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """用户登出API"""
    logout_user()
    return jsonify({'message': '已退出登录'})


@auth_api_bp.route('/profile', methods=['GET'])
@login_required
def profile():
    """获取用户资料API"""
    user_data = current_user.to_dict()
    
    # 添加统计信息
    user_data['score'] = current_user.get_score()
    user_data['solved_count'] = current_user.get_solved_challenges_count()
    user_data['rank'] = current_user.get_rank()
    
    # 团队信息
    if current_user.team:
        user_data['team'] = {
            'id': current_user.team.id,
            'name': current_user.team.name,
            'score': current_user.team.get_score(),
            'rank': current_user.team.get_rank(),
            'is_captain': current_user.team.captain_id == current_user.id
        }
    
    return jsonify(user_data)


@auth_api_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """更新用户资料API"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请提供JSON数据'}), 400
    
    # 可更新的字段
    updatable_fields = ['email', 'bio']
    errors = []
    
    for field in updatable_fields:
        if field in data:
            value = data[field].strip() if isinstance(data[field], str) else data[field]
            
            if field == 'email':
                if not value:
                    errors.append('邮箱不能为空')
                elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', value):
                    errors.append('邮箱格式不正确')
                elif User.query.filter(User.email == value, User.id != current_user.id).first():
                    errors.append('邮箱已被使用')
                else:
                    current_user.email = value
            
            elif field == 'bio':
                if len(value) > 500:
                    errors.append('个人简介不能超过500字符')
                else:
                    current_user.bio = value
    
    if errors:
        return jsonify({'errors': errors}), 400
    
    try:
        db.session.commit()
        return jsonify({
            'message': '资料更新成功',
            'user': current_user.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': '更新失败，请重试'}), 500


@auth_api_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """修改密码API"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请提供JSON数据'}), 400
    
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')
    
    # 验证输入
    errors = []
    
    if not current_password:
        errors.append('请输入当前密码')
    elif not current_user.check_password(current_password):
        errors.append('当前密码错误')
    
    if not new_password or len(new_password) < 6:
        errors.append('新密码至少6个字符')
    elif new_password != confirm_password:
        errors.append('两次输入的新密码不一致')
    
    if errors:
        return jsonify({'errors': errors}), 400
    
    current_user.set_password(new_password)
    
    try:
        db.session.commit()
        return jsonify({'message': '密码修改成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': '修改密码失败，请重试'}), 500


@auth_api_bp.route('/join_team', methods=['POST'])
@login_required
def join_team():
    """通过邀请码加入团队API"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请提供JSON数据'}), 400
    
    invite_code = data.get('invite_code', '').strip().upper()
    
    if not invite_code:
        return jsonify({'error': '请输入邀请码'}), 400
    
    if current_user.team_id:
        return jsonify({'error': '您已经在一个团队中'}), 400
    
    team = Team.query.filter_by(invite_code=invite_code, is_active=True).first()
    
    if not team:
        return jsonify({'error': '邀请码无效'}), 404
    
    if len(team.members) >= team.max_members:
        return jsonify({'error': '团队已满'}), 400
    
    current_user.team_id = team.id
    
    try:
        db.session.commit()
        return jsonify({
            'message': f'成功加入团队 {team.name}',
            'team': team.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': '加入团队失败，请重试'}), 500


@auth_api_bp.route('/leave_team', methods=['POST'])
@login_required
def leave_team():
    """离开团队API"""
    if not current_user.team_id:
        return jsonify({'error': '您不在任何团队中'}), 400
    
    team = current_user.team
    
    # 如果是队长且团队还有其他成员，需要先转让队长
    if team.captain_id == current_user.id and len(team.members) > 1:
        return jsonify({'error': '队长离开前需要先转让队长权限'}), 400
    
    current_user.team_id = None
    
    # 如果是最后一个成员，删除团队
    if len(team.members) == 1:
        team.is_active = False
    
    try:
        db.session.commit()
        return jsonify({'message': '已离开团队'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': '离开团队失败，请重试'}), 500


@auth_api_bp.route('/current_user', methods=['GET'])
@login_required
def current_user_info():
    """获取当前用户信息API"""
    return jsonify({
        'user': current_user.to_dict(),
        'is_authenticated': True
    })


@auth_api_bp.route('/check_auth', methods=['GET'])
def check_auth():
    """检查认证状态API"""
    if current_user.is_authenticated:
        return jsonify({
            'is_authenticated': True,
            'user': current_user.to_dict()
        })
    else:
        return jsonify({
            'is_authenticated': False,
            'user': None
        })