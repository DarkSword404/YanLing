from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Challenge, Category, Submission, Hint, UserHint
from datetime import datetime

challenges_bp = Blueprint('challenges', __name__, url_prefix='/challenges')


@challenges_bp.route('/')
def index():
    """题目列表"""
    category_id = request.args.get('category', type=int)
    difficulty = request.args.get('difficulty')
    solved = request.args.get('solved')  # 'true', 'false', or None
    
    # 基础查询
    query = Challenge.query.filter_by(is_active=True)
    
    # 按分类筛选
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    # 按难度筛选（基于分值）
    if difficulty == 'easy':
        query = query.filter(Challenge.points <= 200)
    elif difficulty == 'medium':
        query = query.filter(Challenge.points.between(201, 400))
    elif difficulty == 'hard':
        query = query.filter(Challenge.points > 400)
    
    challenges = query.order_by(Challenge.points.asc()).all()
    
    # 获取所有分类
    categories = Category.query.all()
    
    # 处理题目数据
    challenges_data = []
    for challenge in challenges:
        challenge_dict = challenge.to_dict()
        
        # 添加用户解题状态
        if current_user.is_authenticated:
            challenge_dict['is_solved'] = challenge.is_solved_by_user(current_user.id)
            if current_user.team:
                challenge_dict['is_solved_by_team'] = challenge.is_solved_by_team(current_user.team.id)
        else:
            challenge_dict['is_solved'] = False
            challenge_dict['is_solved_by_team'] = False
        
        # 按解题状态筛选
        if solved == 'true' and not challenge_dict['is_solved']:
            continue
        elif solved == 'false' and challenge_dict['is_solved']:
            continue
        
        challenges_data.append(challenge_dict)
    
    if request.is_json:
        return jsonify({
            'challenges': challenges_data,
            'categories': [c.to_dict() for c in categories]
        })
    
    return render_template('challenges.html',
                         challenges=challenges_data,
                         categories=categories,
                         current_category=category_id,
                         pagination=None)


@challenges_bp.route('/<int:challenge_id>')
def detail(challenge_id):
    """题目详情"""
    challenge = Challenge.query.get_or_404(challenge_id)
    
    if not challenge.is_active:
        if request.is_json:
            return jsonify({'error': '题目不存在或已下线'}), 404
        flash('题目不存在或已下线', 'error')
        return redirect(url_for('challenges.index'))
    
    challenge_data = challenge.to_dict()
    
    # 添加用户相关信息
    if current_user.is_authenticated:
        challenge_data['is_solved'] = challenge.is_solved_by_user(current_user.id)
        challenge_data['user_attempts'] = len(Submission.get_user_submissions(current_user.id, challenge_id))
        
        # 获取用户的提交记录
        user_submissions = Submission.get_user_submissions(current_user.id, challenge_id)
        challenge_data['submissions'] = [s.to_dict() for s in user_submissions[:10]]  # 最近10次提交
        
        # 获取提示信息
        hints = Hint.query.filter_by(challenge_id=challenge_id, is_active=True).order_by(Hint.order).all()
        challenge_data['hints'] = [h.to_dict(current_user.id) for h in hints]
    else:
        challenge_data['is_solved'] = False
        challenge_data['user_attempts'] = 0
        challenge_data['submissions'] = []
        challenge_data['hints'] = []
    
    # 获取解题记录（前10名）
    solves = (Submission.query
              .filter_by(challenge_id=challenge_id, is_correct=True)
              .order_by(Submission.created_at.asc())
              .limit(10)
              .all())
    
    challenge_data['top_solves'] = []
    for i, solve in enumerate(solves):
        solve_data = {
            'rank': i + 1,
            'username': solve.user.username,
            'team_name': solve.user.team.name if solve.user.team else None,
            'points': solve.points_awarded,
            'created_at': solve.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_first_blood': i == 0
        }
        challenge_data['top_solves'].append(solve_data)
    
    if request.is_json:
        return jsonify(challenge_data)
    
    return render_template('challenge_detail.html', challenge=challenge_data)


@challenges_bp.route('/<int:challenge_id>/submit', methods=['POST'])
@login_required
def submit_flag(challenge_id):
    """提交flag"""
    challenge = Challenge.query.get_or_404(challenge_id)
    
    if not challenge.is_active:
        if request.is_json:
            return jsonify({'error': '题目不存在或已下线'}), 404
        flash('题目不存在或已下线', 'error')
        return redirect(url_for('challenges.detail', challenge_id=challenge_id))
    
    # 检查是否已经解出
    if challenge.is_solved_by_user(current_user.id):
        if request.is_json:
            return jsonify({'error': '您已经解出此题'}), 400
        flash('您已经解出此题', 'warning')
        return redirect(url_for('challenges.detail', challenge_id=challenge_id))
    
    # 获取提交的flag
    if request.is_json:
        data = request.get_json()
        submitted_flag = data.get('flag', '').strip()
    else:
        submitted_flag = request.form.get('flag', '').strip()
    
    if not submitted_flag:
        if request.is_json:
            return jsonify({'error': 'Flag不能为空'}), 400
        flash('Flag不能为空', 'error')
        return redirect(url_for('challenges.detail', challenge_id=challenge_id))
    
    # 检查尝试次数限制
    if challenge.max_attempts > 0:
        user_attempts = len(Submission.get_user_submissions(current_user.id, challenge_id))
        if user_attempts >= challenge.max_attempts:
            if request.is_json:
                return jsonify({'error': f'已达到最大尝试次数限制({challenge.max_attempts}次)'}), 400
            flash(f'已达到最大尝试次数限制({challenge.max_attempts}次)', 'error')
            return redirect(url_for('challenges.detail', challenge_id=challenge_id))
    
    # 创建提交记录
    submission = Submission(
        user_id=current_user.id,
        challenge_id=challenge_id,
        submitted_flag=submitted_flag,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')
    )
    
    # 检查flag正确性
    is_correct = submission.check_and_update_correctness()
    
    try:
        db.session.add(submission)
        db.session.commit()
        
        if is_correct:
            message = f'恭喜！Flag正确，获得 {submission.points_awarded} 分'
            if submission.is_first_blood():
                message += ' (一血！)'
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': message,
                    'points': submission.points_awarded,
                    'is_first_blood': submission.is_first_blood()
                })
            flash(message, 'success')
        else:
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Flag错误，请重试'
                })
            flash('Flag错误，请重试', 'error')
    
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': '提交失败，请重试'}), 500
        flash('提交失败，请重试', 'error')
    
    return redirect(url_for('challenges.detail', challenge_id=challenge_id))


@challenges_bp.route('/<int:challenge_id>/hints/<int:hint_id>/purchase', methods=['POST'])
@login_required
def purchase_hint(challenge_id, hint_id):
    """购买提示"""
    challenge = Challenge.query.get_or_404(challenge_id)
    hint = Hint.query.get_or_404(hint_id)
    
    if hint.challenge_id != challenge_id:
        if request.is_json:
            return jsonify({'error': '提示不属于此题目'}), 400
        flash('提示不属于此题目', 'error')
        return redirect(url_for('challenges.detail', challenge_id=challenge_id))
    
    if not hint.is_active:
        if request.is_json:
            return jsonify({'error': '提示不可用'}), 400
        flash('提示不可用', 'error')
        return redirect(url_for('challenges.detail', challenge_id=challenge_id))
    
    # 检查是否已购买
    if hint.is_purchased_by_user(current_user.id):
        if request.is_json:
            return jsonify({'error': '您已经购买过此提示'}), 400
        flash('您已经购买过此提示', 'warning')
        return redirect(url_for('challenges.detail', challenge_id=challenge_id))
    
    # 检查用户分数是否足够
    user_score = current_user.get_score()
    if user_score < hint.cost:
        if request.is_json:
            return jsonify({'error': f'分数不足，需要 {hint.cost} 分'}), 400
        flash(f'分数不足，需要 {hint.cost} 分', 'error')
        return redirect(url_for('challenges.detail', challenge_id=challenge_id))
    
    # 创建购买记录
    user_hint = UserHint(
        user_id=current_user.id,
        hint_id=hint_id,
        cost_paid=hint.cost
    )
    
    try:
        db.session.add(user_hint)
        db.session.commit()
        
        if request.is_json:
            return jsonify({
                'message': f'成功购买提示，消耗 {hint.cost} 分',
                'hint_content': hint.content
            })
        flash(f'成功购买提示，消耗 {hint.cost} 分', 'success')
    
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': '购买失败，请重试'}), 500
        flash('购买失败，请重试', 'error')
    
    return redirect(url_for('challenges.detail', challenge_id=challenge_id))


@challenges_bp.route('/categories')
def categories():
    """题目分类列表"""
    categories = Category.query.all()
    categories_data = []
    
    for category in categories:
        category_dict = category.to_dict()
        category_dict['challenge_count'] = len([c for c in category.challenges if c.is_active])
        
        if current_user.is_authenticated:
            solved_count = 0
            for challenge in category.challenges:
                if challenge.is_active and challenge.is_solved_by_user(current_user.id):
                    solved_count += 1
            category_dict['solved_count'] = solved_count
        else:
            category_dict['solved_count'] = 0
        
        categories_data.append(category_dict)
    
    if request.is_json:
        return jsonify({'categories': categories_data})
    
    return render_template('categories.html', categories=categories_data)