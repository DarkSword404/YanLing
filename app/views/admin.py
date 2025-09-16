from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import User, Team, Challenge, Category, Submission
from sqlalchemy import func, desc
import os
from werkzeug.utils import secure_filename

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            if request.is_json:
                return jsonify({'error': '需要管理员权限'}), 403
            flash('需要管理员权限', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """管理员仪表板"""
    # 统计数据
    stats = {
        'total_users': User.query.count(),
        'total_teams': Team.query.filter_by(is_active=True).count(),
        'total_challenges': Challenge.query.filter_by(is_active=True).count(),
        'total_submissions': Submission.query.count(),
        'correct_submissions': Submission.query.filter_by(is_correct=True).count(),
    }
    
    # 最近注册用户
    recent_users = User.query.order_by(desc(User.created_at)).limit(10).all()
    
    # 最近提交记录
    recent_submissions = (Submission.query
                         .order_by(desc(Submission.created_at))
                         .limit(20)
                         .all())
    
    # 题目解题统计
    challenge_stats = (db.session.query(
        Challenge.name,
        func.count(Submission.id).label('total_attempts'),
        func.count(Submission.id).filter(Submission.is_correct == True).label('correct_attempts')
    ).outerjoin(Submission)
     .group_by(Challenge.id, Challenge.name)
     .order_by(desc('correct_attempts'))
     .limit(10)
     .all())
    
    if request.is_json:
        return jsonify({
            'stats': stats,
            'recent_users': [user.to_dict() for user in recent_users],
            'recent_submissions': [sub.to_dict() for sub in recent_submissions],
            'challenge_stats': [
                {
                    'name': stat.name,
                    'total_attempts': stat.total_attempts,
                    'correct_attempts': stat.correct_attempts,
                    'success_rate': round(stat.correct_attempts / stat.total_attempts * 100, 2) if stat.total_attempts > 0 else 0
                }
                for stat in challenge_stats
            ]
        })
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         recent_users=recent_users,
                         recent_submissions=recent_submissions,
                         challenge_stats=challenge_stats)


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """用户管理"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '').strip()
    
    query = User.query
    if search:
        query = query.filter(User.username.contains(search) | User.email.contains(search))
    
    users = query.order_by(desc(User.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    if request.is_json:
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'pagination': {
                'page': users.page,
                'pages': users.pages,
                'per_page': users.per_page,
                'total': users.total,
                'has_next': users.has_next,
                'has_prev': users.has_prev
            }
        })
    
    return render_template('admin/users.html', users=users, search=search)


@admin_bp.route('/users/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def toggle_user_admin(user_id):
    """切换用户管理员状态"""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        if request.is_json:
            return jsonify({'error': '不能修改自己的管理员状态'}), 400
        flash('不能修改自己的管理员状态', 'error')
        return redirect(url_for('admin.users'))
    
    user.is_admin = not user.is_admin
    
    try:
        db.session.commit()
        status = '管理员' if user.is_admin else '普通用户'
        if request.is_json:
            return jsonify({'message': f'用户 {user.username} 已设置为{status}'})
        flash(f'用户 {user.username} 已设置为{status}', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': '操作失败'}), 500
        flash('操作失败', 'error')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(user_id):
    """切换用户激活状态"""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        if request.is_json:
            return jsonify({'error': '不能修改自己的激活状态'}), 400
        flash('不能修改自己的激活状态', 'error')
        return redirect(url_for('admin.users'))
    
    user.is_active = not user.is_active
    
    try:
        db.session.commit()
        status = '激活' if user.is_active else '禁用'
        if request.is_json:
            return jsonify({'message': f'用户 {user.username} 已{status}'})
        flash(f'用户 {user.username} 已{status}', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': '操作失败'}), 500
        flash('操作失败', 'error')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/challenges')
@login_required
@admin_required
def challenges():
    """题目管理"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    category_id = request.args.get('category_id', type=int)
    
    query = Challenge.query
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    challenges = query.order_by(desc(Challenge.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    categories = Category.query.filter_by(is_active=True).all()
    
    if request.is_json:
        return jsonify({
            'challenges': [challenge.to_dict() for challenge in challenges.items],
            'categories': [category.to_dict() for category in categories],
            'pagination': {
                'page': challenges.page,
                'pages': challenges.pages,
                'per_page': challenges.per_page,
                'total': challenges.total,
                'has_next': challenges.has_next,
                'has_prev': challenges.has_prev
            }
        })
    
    return render_template('admin/challenges.html', 
                         challenges=challenges, 
                         categories=categories,
                         selected_category=category_id)


@admin_bp.route('/challenges/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_challenge():
    """创建题目"""
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        # 验证输入
        required_fields = ['name', 'description', 'flag', 'points', 'category_id']
        errors = []
        
        for field in required_fields:
            if not data.get(field):
                errors.append(f'{field} 不能为空')
        
        if errors:
            if request.is_json:
                return jsonify({'errors': errors}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('admin/create_challenge.html', 
                                 categories=Category.query.filter_by(is_active=True).all())
        
        # 检查题目名称是否重复
        if Challenge.query.filter_by(name=data['name']).first():
            error = '题目名称已存在'
            if request.is_json:
                return jsonify({'error': error}), 400
            flash(error, 'error')
            return render_template('admin/create_challenge.html', 
                                 categories=Category.query.filter_by(is_active=True).all())
        
        # 创建题目
        challenge = Challenge(
            name=data['name'],
            description=data['description'],
            flag=data['flag'],
            points=int(data['points']),
            category_id=int(data['category_id']),
            author_id=current_user.id,
            difficulty=data.get('difficulty', 'medium'),
            max_attempts=int(data.get('max_attempts', 0)) if data.get('max_attempts') else None,
            is_dynamic=data.get('is_dynamic', False) == 'true' if not request.is_json else data.get('is_dynamic', False)
        )
        
        try:
            db.session.add(challenge)
            db.session.commit()
            
            if request.is_json:
                return jsonify({
                    'message': '题目创建成功',
                    'challenge': challenge.to_dict()
                }), 201
            
            flash('题目创建成功', 'success')
            return redirect(url_for('admin.challenges'))
        
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'error': '创建题目失败'}), 500
            flash('创建题目失败', 'error')
    
    categories = Category.query.filter_by(is_active=True).all()
    return render_template('admin/create_challenge.html', categories=categories)


@admin_bp.route('/challenges/<int:challenge_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_challenge(challenge_id):
    """编辑题目"""
    challenge = Challenge.query.get_or_404(challenge_id)
    
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        # 更新题目信息
        challenge.name = data.get('name', challenge.name)
        challenge.description = data.get('description', challenge.description)
        challenge.flag = data.get('flag', challenge.flag)
        challenge.points = int(data.get('points', challenge.points))
        challenge.category_id = int(data.get('category_id', challenge.category_id))
        challenge.difficulty = data.get('difficulty', challenge.difficulty)
        challenge.max_attempts = int(data.get('max_attempts')) if data.get('max_attempts') else None
        challenge.is_dynamic = data.get('is_dynamic', False) == 'true' if not request.is_json else data.get('is_dynamic', False)
        
        try:
            db.session.commit()
            
            if request.is_json:
                return jsonify({
                    'message': '题目更新成功',
                    'challenge': challenge.to_dict()
                })
            
            flash('题目更新成功', 'success')
            return redirect(url_for('admin.challenges'))
        
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'error': '更新题目失败'}), 500
            flash('更新题目失败', 'error')
    
    categories = Category.query.filter_by(is_active=True).all()
    
    if request.is_json:
        return jsonify({
            'challenge': challenge.to_dict(),
            'categories': [category.to_dict() for category in categories]
        })
    
    return render_template('admin/edit_challenge.html', 
                         challenge=challenge, 
                         categories=categories)


@admin_bp.route('/challenges/<int:challenge_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_challenge_active(challenge_id):
    """切换题目激活状态"""
    challenge = Challenge.query.get_or_404(challenge_id)
    challenge.is_active = not challenge.is_active
    
    try:
        db.session.commit()
        status = '激活' if challenge.is_active else '禁用'
        if request.is_json:
            return jsonify({'message': f'题目 {challenge.name} 已{status}'})
        flash(f'题目 {challenge.name} 已{status}', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': '操作失败'}), 500
        flash('操作失败', 'error')
    
    return redirect(url_for('admin.challenges'))


@admin_bp.route('/categories')
@login_required
@admin_required
def categories():
    """分类管理"""
    categories = Category.query.order_by(Category.order, Category.name).all()
    
    if request.is_json:
        return jsonify({
            'categories': [category.to_dict() for category in categories]
        })
    
    return render_template('admin/categories.html', categories=categories)


@admin_bp.route('/categories/create', methods=['POST'])
@login_required
@admin_required
def create_category():
    """创建分类"""
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    
    if not name:
        error = '分类名称不能为空'
        if request.is_json:
            return jsonify({'error': error}), 400
        flash(error, 'error')
        return redirect(url_for('admin.categories'))
    
    if Category.query.filter_by(name=name).first():
        error = '分类名称已存在'
        if request.is_json:
            return jsonify({'error': error}), 400
        flash(error, 'error')
        return redirect(url_for('admin.categories'))
    
    category = Category(
        name=name,
        description=description,
        order=int(data.get('order', 0))
    )
    
    try:
        db.session.add(category)
        db.session.commit()
        
        if request.is_json:
            return jsonify({
                'message': '分类创建成功',
                'category': category.to_dict()
            }), 201
        
        flash('分类创建成功', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': '创建分类失败'}), 500
        flash('创建分类失败', 'error')
    
    return redirect(url_for('admin.categories'))


@admin_bp.route('/teams')
@login_required
@admin_required
def teams():
    """团队管理"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    teams = Team.query.order_by(desc(Team.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    if request.is_json:
        teams_data = []
        for team in teams.items:
            team_dict = team.to_dict()
            team_dict['member_count'] = len(team.members)
            team_dict['score'] = team.get_score()
            teams_data.append(team_dict)
        
        return jsonify({
            'teams': teams_data,
            'pagination': {
                'page': teams.page,
                'pages': teams.pages,
                'per_page': teams.per_page,
                'total': teams.total,
                'has_next': teams.has_next,
                'has_prev': teams.has_prev
            }
        })
    
    return render_template('admin/teams.html', teams=teams)


@admin_bp.route('/teams/<int:team_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_team_active(team_id):
    """切换团队激活状态"""
    team = Team.query.get_or_404(team_id)
    team.is_active = not team.is_active
    
    try:
        db.session.commit()
        status = '激活' if team.is_active else '禁用'
        if request.is_json:
            return jsonify({'message': f'团队 {team.name} 已{status}'})
        flash(f'团队 {team.name} 已{status}', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': '操作失败'}), 500
        flash('操作失败', 'error')
    
    return redirect(url_for('admin.teams'))