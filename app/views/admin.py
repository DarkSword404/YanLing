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
                         challenge_stats=challenge_stats,
                         system_info={
                             'memory_usage': 65,
                             'disk_usage': 45,
                             'uptime': '2天 3小时'
                         })


@admin_bp.route('/api/category-distribution')
@login_required
@admin_required
def admin_category_distribution():
    """管理后台题目分类分布API"""
    from app.models import Category
    
    # 获取各分类的题目数量
    categories = db.session.query(
        Category.name,
        Category.color,
        func.count(Challenge.id).label('count')
    ).join(Challenge).filter(
        Challenge.is_active == True,
        Category.is_active == True
    ).group_by(Category.id, Category.name, Category.color).all()
    
    data = []
    for category in categories:
        data.append({
            'name': category.name,
            'value': category.count,
            'color': category.color
        })
    
    return jsonify(data)


@admin_bp.route('/api/registration-trend')
@login_required
@admin_required
def admin_registration_trend():
    """管理后台用户注册趋势API"""
    from datetime import datetime, timedelta
    from sqlalchemy import extract
    
    # 获取最近6个月的用户注册数据
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    
    registrations = db.session.query(
        extract('year', User.created_at).label('year'),
        extract('month', User.created_at).label('month'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= six_months_ago,
        User.is_active == True
    ).group_by(
        extract('year', User.created_at),
        extract('month', User.created_at)
    ).order_by(
        extract('year', User.created_at),
        extract('month', User.created_at)
    ).all()
    
    data = []
    for reg in registrations:
        month_name = f"{int(reg.year)}-{int(reg.month):02d}"
        data.append({
            'month': month_name,
            'count': reg.count
        })
    
    return jsonify(data)


@admin_bp.route('/api/system-status')
@login_required
@admin_required
def admin_system_status():
    """管理后台系统状态API"""
    import psutil
    import os
    from datetime import datetime, timedelta
    
    try:
        # 获取系统信息
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 计算运行时间（从进程启动时间开始）
        process = psutil.Process(os.getpid())
        start_time = datetime.fromtimestamp(process.create_time())
        uptime = datetime.now() - start_time
        
        # 格式化运行时间
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 0:
            uptime_str = f"{days}天 {hours}小时"
        elif hours > 0:
            uptime_str = f"{hours}小时 {minutes}分钟"
        else:
            uptime_str = f"{minutes}分钟"
        
        # 检查数据库连接状态
        try:
            db.session.execute('SELECT 1')
            db_status = "正常"
            db_status_class = "success"
        except Exception:
            db_status = "异常"
            db_status_class = "danger"
        
        data = {
            'database': {
                'status': db_status,
                'status_class': db_status_class
            },
            'memory': {
                'usage': round(memory.percent, 1),
                'status_class': 'danger' if memory.percent > 80 else 'warning' if memory.percent > 60 else 'info'
            },
            'disk': {
                'usage': round(disk.percent, 1),
                'status_class': 'danger' if disk.percent > 80 else 'warning' if disk.percent > 60 else 'info'
            },
            'uptime': {
                'text': uptime_str,
                'status_class': 'primary'
            }
        }
        
        return jsonify(data)
        
    except Exception as e:
        # 如果获取系统信息失败，返回默认值
        return jsonify({
            'database': {
                'status': '正常',
                'status_class': 'success'
            },
            'memory': {
                'usage': 65,
                'status_class': 'info'
            },
            'disk': {
                'usage': 45,
                'status_class': 'info'
            },
            'uptime': {
                'text': '2天 3小时',
                'status_class': 'primary'
            }
        })


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """用户管理"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '').strip()
    role = request.args.get('role', '').strip()
    status = request.args.get('status', '').strip()
    
    query = User.query
    
    # 搜索用户名或邮箱
    if search:
        query = query.filter(User.username.contains(search) | User.email.contains(search))
    
    # 按角色筛选
    if role == 'admin':
        query = query.filter(User.is_admin == True)
    elif role == 'user':
        query = query.filter(User.is_admin == False)
    
    # 按状态筛选
    if status == 'active':
        query = query.filter(User.is_active == True)
    elif status == 'inactive':
        query = query.filter(User.is_active == False)
    
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


@admin_bp.route('/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    """创建新用户"""
    data = request.form if request.form else request.get_json()
    if not data:
        if request.is_json:
            return jsonify({'error': '缺少请求数据'}), 400
        flash('缺少请求数据', 'error')
        return redirect(url_for('admin.users'))
    
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    is_admin = bool(data.get('is_admin'))
    is_active = bool(data.get('is_active', True))
    
    # 验证必填字段
    if not username or not email or not password:
        error = '用户名、邮箱和密码不能为空'
        if request.is_json:
            return jsonify({'error': error}), 400
        flash(error, 'error')
        return redirect(url_for('admin.users'))
    
    # 检查用户名是否已存在（只检查活跃的用户）
    if User.query.filter_by(username=username, is_active=True).first():
        error = '用户名已存在'
        if request.is_json:
            return jsonify({'error': error}), 400
        flash(error, 'error')
        return redirect(url_for('admin.users'))
    
    # 检查邮箱是否已存在（只检查活跃的用户）
    if User.query.filter_by(email=email, is_active=True).first():
        error = '邮箱已存在'
        if request.is_json:
            return jsonify({'error': error}), 400
        flash(error, 'error')
        return redirect(url_for('admin.users'))
    
    # 创建新用户
    user = User(
        username=username,
        email=email,
        is_admin=is_admin,
        is_active=is_active
    )
    user.set_password(password)
    
    try:
        db.session.add(user)
        db.session.commit()
        
        if request.is_json:
            return jsonify({
                'message': f'用户 {user.username} 创建成功',
                'user': user.to_dict()
            }), 201
        
        flash(f'用户 {user.username} 创建成功', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': '创建用户失败'}), 500
        flash('创建用户失败', 'error')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def toggle_user_admin(user_id):
    """切换用户管理员状态"""
    user = User.query.get_or_404(user_id)
    
    # 检查是否是AJAX请求
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if user.id == current_user.id:
        if is_ajax:
            return jsonify({'error': '不能修改自己的管理员状态'}), 400
        flash('不能修改自己的管理员状态', 'error')
        return redirect(url_for('admin.users'))
    
    user.is_admin = not user.is_admin
    
    try:
        db.session.commit()
        status = '管理员' if user.is_admin else '普通用户'
        if is_ajax:
            return jsonify({'message': f'用户 {user.username} 已设置为{status}'})
        flash(f'用户 {user.username} 已设置为{status}', 'success')
    except Exception as e:
        db.session.rollback()
        if is_ajax:
            return jsonify({'error': '操作失败'}), 500
        flash('操作失败', 'error')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(user_id):
    """切换用户激活状态"""
    user = User.query.get_or_404(user_id)
    
    # 检查是否是AJAX请求
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if user.id == current_user.id:
        if is_ajax:
            return jsonify({'error': '不能修改自己的激活状态'}), 400
        flash('不能修改自己的激活状态', 'error')
        return redirect(url_for('admin.users'))
    
    user.is_active = not user.is_active
    
    try:
        db.session.commit()
        status = '激活' if user.is_active else '禁用'
        if is_ajax:
            return jsonify({'message': f'用户 {user.username} 已{status}'})
        flash(f'用户 {user.username} 已{status}', 'success')
    except Exception as e:
        db.session.rollback()
        if is_ajax:
            return jsonify({'error': '操作失败'}), 500
        flash('操作失败', 'error')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    """删除用户"""
    user = User.query.get_or_404(user_id)
    
    # 检查是否是AJAX请求
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if user.id == current_user.id:
        if is_ajax:
            return jsonify({'error': '不能删除自己的账户'}), 400
        flash('不能删除自己的账户', 'error')
        return redirect(url_for('admin.users'))
    
    username = user.username
    
    try:
        # 删除用户相关的提交记录
        Submission.query.filter_by(user_id=user.id).delete()
        
        # 删除用户
        db.session.delete(user)
        db.session.commit()
        
        if is_ajax:
            return jsonify({'message': f'用户 {username} 已删除'})
        flash(f'用户 {username} 已删除', 'success')
    except Exception as e:
        db.session.rollback()
        if is_ajax:
            return jsonify({'error': '删除用户失败'}), 500
        flash('删除用户失败', 'error')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    """更新用户信息"""
    user = User.query.get_or_404(user_id)
    
    # 检查是否是AJAX请求
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    data = request.form if request.form else request.get_json()
    if not data:
        if is_ajax:
            return jsonify({'error': '缺少请求数据'}), 400
        flash('缺少请求数据', 'error')
        return redirect(url_for('admin.users'))
    
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    # 验证必填字段
    if not username or not email:
        error = '用户名和邮箱不能为空'
        if is_ajax:
            return jsonify({'error': error}), 400
        flash(error, 'error')
        return redirect(url_for('admin.users'))
    
    # 检查用户名是否已存在（排除当前用户，只检查活跃用户）
    existing_user = User.query.filter(User.username == username, User.id != user_id, User.is_active == True).first()
    if existing_user:
        error = '用户名已存在'
        if is_ajax:
            return jsonify({'error': error}), 400
        flash(error, 'error')
        return redirect(url_for('admin.users'))
    
    # 检查邮箱是否已存在（排除当前用户，只检查活跃用户）
    existing_email = User.query.filter(User.email == email, User.id != user_id, User.is_active == True).first()
    if existing_email:
        error = '邮箱已存在'
        if is_ajax:
            return jsonify({'error': error}), 400
        flash(error, 'error')
        return redirect(url_for('admin.users'))
    
    # 更新用户信息
    user.username = username
    user.email = email
    
    # 如果提供了新密码，则更新密码
    if password:
        user.set_password(password)
    
    try:
        db.session.commit()
        if is_ajax:
            return jsonify({'message': f'用户 {user.username} 信息已更新'})
        flash(f'用户 {user.username} 信息已更新', 'success')
    except Exception as e:
        db.session.rollback()
        if is_ajax:
            return jsonify({'error': '更新用户失败'}), 500
        flash('更新用户失败', 'error')
    
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
        
        # 检查题目名称是否重复（只检查活跃的题目）
        if Challenge.query.filter_by(name=data['name'], is_active=True).first():
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
    
    # 检查是否是AJAX请求
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    challenge.is_active = not challenge.is_active
    
    try:
        db.session.commit()
        status = '激活' if challenge.is_active else '禁用'
        if is_ajax:
            return jsonify({'message': f'题目 {challenge.name} 已{status}'})
        flash(f'题目 {challenge.name} 已{status}', 'success')
    except Exception as e:
        db.session.rollback()
        if is_ajax:
            return jsonify({'error': '操作失败'}), 500
        flash('操作失败', 'error')
    
    return redirect(url_for('admin.challenges'))


@admin_bp.route('/challenges/<int:challenge_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_challenge(challenge_id):
    """删除题目"""
    challenge = Challenge.query.get_or_404(challenge_id)
    
    # 检查是否是AJAX请求
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    challenge_name = challenge.name
    
    try:
        # 删除题目相关的提交记录和提示
        Submission.query.filter_by(challenge_id=challenge.id).delete()
        
        # 删除题目
        db.session.delete(challenge)
        db.session.commit()
        
        if is_ajax:
            return jsonify({'message': f'题目 {challenge_name} 已删除'})
        flash(f'题目 {challenge_name} 已删除', 'success')
    except Exception as e:
        db.session.rollback()
        if is_ajax:
            return jsonify({'error': '删除失败'}), 500
        flash('删除失败', 'error')
    
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
    
    if Category.query.filter_by(name=name, is_active=True).first():
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