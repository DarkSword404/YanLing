from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf.csrf import validate_csrf
from werkzeug.security import check_password_hash
from app import db
from app.models import User, Team
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.form.get('username')
            password = request.form.get('password')
        
        if not username or not password:
            if request.is_json:
                return jsonify({'error': '用户名和密码不能为空'}), 400
            flash('用户名和密码不能为空', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                if request.is_json:
                    return jsonify({'error': '账户已被禁用'}), 403
                flash('账户已被禁用', 'error')
                return render_template('auth/login.html')
            
            login_user(user, remember=True)
            
            if request.is_json:
                return jsonify({
                    'message': '登录成功',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'role': 'admin' if user.is_admin else 'user',
                        'team': user.team.name if user.team else None
                    }
                })
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            if request.is_json:
                return jsonify({'error': '用户名或密码错误'}), 401
            flash('用户名或密码错误', 'error')
    
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            confirm_password = data.get('confirm_password')
        else:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
        
        # 验证输入
        errors = []
        
        if not username or len(username) < 3:
            errors.append('用户名至少3个字符')
        elif User.query.filter_by(username=username).first():
            errors.append('用户名已存在')
        
        if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            errors.append('请输入有效的邮箱地址')
        elif User.query.filter_by(email=email).first():
            errors.append('邮箱已被注册')
        
        if not password or len(password) < 6:
            errors.append('密码至少6个字符')
        elif password != confirm_password:
            errors.append('两次输入的密码不一致')
        
        if errors:
            if request.is_json:
                return jsonify({'errors': errors}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html')
        
        # 创建用户
        user = User(username=username, email=email)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            if request.is_json:
                return jsonify({'message': '注册成功，请登录'}), 201
            
            flash('注册成功，请登录', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'error': '注册失败，请重试'}), 500
            flash('注册失败，请重试', 'error')
    
    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    logout_user()
    if request.is_json:
        return jsonify({'message': '已退出登录'})
    flash('已退出登录', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/profile')
@login_required
def profile():
    """用户资料"""
    user_data = {
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'role': 'admin' if current_user.is_admin else 'user',
        'score': current_user.get_score(),
        'solved_challenges': current_user.get_solved_challenges_count(),
        'team': current_user.team.to_dict() if current_user.team else None,
        'created_at': current_user.created_at.isoformat() if current_user.created_at else None
    }
    
    if request.is_json:
        return jsonify(user_data)
    
    return render_template('profile.html', user=user_data)


@auth_bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """编辑用户资料"""
    if request.method == 'POST':
        try:
            # 验证CSRF令牌
            validate_csrf(request.form.get('csrf_token'))
        except Exception as e:
            flash('CSRF令牌验证失败，请重试', 'error')
            return render_template('auth/edit_profile.html', user=current_user), 400
            
        if request.is_json:
            data = request.get_json()
            nickname = data.get('nickname', '').strip()
            bio = data.get('bio', '').strip()
        else:
            nickname = request.form.get('nickname', '').strip()
            bio = request.form.get('bio', '').strip()
        
        # 更新用户信息
        if nickname:
            current_user.nickname = nickname
        if bio:
            current_user.bio = bio
        
        try:
            db.session.commit()
            if request.is_json:
                return jsonify({'message': '资料更新成功'})
            flash('资料更新成功', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'error': '更新失败，请重试'}), 500
            flash('更新失败，请重试', 'error')
    
    if request.is_json:
        return jsonify({
            'nickname': current_user.nickname or '',
            'bio': current_user.bio or ''
        })
    
    return render_template('auth/edit_profile.html', user=current_user)


@auth_bp.route('/join_team', methods=['POST'])
@login_required
def join_team():
    """加入团队"""
    if request.is_json:
        data = request.get_json()
        invite_code = data.get('invite_code')
    else:
        invite_code = request.form.get('invite_code')
    
    if not invite_code:
        if request.is_json:
            return jsonify({'error': '请输入邀请码'}), 400
        flash('请输入邀请码', 'error')
        return redirect(url_for('auth.profile'))
    
    if current_user.team_id:
        if request.is_json:
            return jsonify({'error': '您已经在一个团队中'}), 400
        flash('您已经在一个团队中', 'error')
        return redirect(url_for('auth.profile'))
    
    team = Team.query.filter_by(invite_code=invite_code).first()
    
    if not team:
        if request.is_json:
            return jsonify({'error': '无效的邀请码'}), 404
        flash('无效的邀请码', 'error')
        return redirect(url_for('auth.profile'))
    
    if not team.is_active:
        if request.is_json:
            return jsonify({'error': '团队已被禁用'}), 403
        flash('团队已被禁用', 'error')
        return redirect(url_for('auth.profile'))
    
    if len(team.members) >= team.max_members:
        if request.is_json:
            return jsonify({'error': '团队已满'}), 400
        flash('团队已满', 'error')
        return redirect(url_for('auth.profile'))
    
    current_user.team_id = team.id
    
    try:
        db.session.commit()
        if request.is_json:
            return jsonify({'message': f'成功加入团队 {team.name}'})
        flash(f'成功加入团队 {team.name}', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': '加入团队失败'}), 500
        flash('加入团队失败', 'error')
    
    return redirect(url_for('auth.profile'))


@auth_bp.route('/leave_team', methods=['POST'])
@login_required
def leave_team():
    """离开团队"""
    if not current_user.team_id:
        if request.is_json:
            return jsonify({'error': '您不在任何团队中'}), 400
        flash('您不在任何团队中', 'error')
        return redirect(url_for('auth.profile'))
    
    current_user.team_id = None
    
    try:
        db.session.commit()
        if request.is_json:
            return jsonify({'message': '已离开团队'})
        flash('已离开团队', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': '离开团队失败'}), 500
        flash('离开团队失败', 'error')
    
    return redirect(url_for('auth.profile'))