from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Team, User, Submission
from sqlalchemy import func, desc
import secrets
import string

teams_bp = Blueprint('teams', __name__, url_prefix='/teams')


@teams_bp.route('/')
def index():
    """团队列表"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    teams = Team.query.filter_by(is_active=True).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    teams_data = []
    for team in teams.items:
        team_dict = team.to_dict()
        team_dict['member_count'] = len(team.members)
        team_dict['score'] = team.get_score()
        team_dict['solved_count'] = team.get_solved_challenges_count()
        teams_data.append(team_dict)
    
    if request.is_json:
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
    
    return render_template('teams/index.html', teams=teams_data, pagination=teams)


@teams_bp.route('/<int:team_id>')
def detail(team_id):
    """团队详情"""
    team = Team.query.get_or_404(team_id)
    
    if not team.is_active:
        if request.is_json:
            return jsonify({'error': '团队不存在或已被禁用'}), 404
        flash('团队不存在或已被禁用', 'error')
        return redirect(url_for('teams.index'))
    
    team_data = team.to_dict()
    team_data['member_count'] = len(team.members)
    team_data['score'] = team.get_score()
    team_data['solved_count'] = team.get_solved_challenges_count()
    
    # 获取团队成员信息
    members_data = []
    for member in team.members:
        member_data = {
            'id': member.id,
            'username': member.username,
            'score': member.get_score(),
            'solved_count': member.get_solved_challenges_count(),
            'joined_at': member.created_at.strftime('%Y-%m-%d') if member.created_at else None
        }
        members_data.append(member_data)
    
    # 按分数排序
    members_data.sort(key=lambda x: x['score'], reverse=True)
    team_data['members'] = members_data
    
    # 获取团队最近解题记录
    recent_solves = (db.session.query(Submission)
                    .join(User)
                    .filter(User.team_id == team_id)
                    .filter(Submission.is_correct == True)
                    .order_by(desc(Submission.created_at))
                    .limit(20)
                    .all())
    
    solves_data = []
    for solve in recent_solves:
        solve_data = {
            'username': solve.user.username,
            'challenge_name': solve.challenge.name,
            'points': solve.points_awarded,
            'created_at': solve.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_first_blood': solve.is_first_blood()
        }
        solves_data.append(solve_data)
    
    team_data['recent_solves'] = solves_data
    
    # 检查当前用户是否为团队成员
    if current_user.is_authenticated:
        team_data['is_member'] = current_user.team_id == team_id
        team_data['can_join'] = (current_user.team_id is None and 
                               len(team.members) < team.max_members)
    else:
        team_data['is_member'] = False
        team_data['can_join'] = False
    
    if request.is_json:
        return jsonify(team_data)
    
    return render_template('teams/detail.html', team=team_data)


@teams_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """创建团队"""
    if current_user.team_id:
        if request.is_json:
            return jsonify({'error': '您已经在一个团队中'}), 400
        flash('您已经在一个团队中', 'error')
        return redirect(url_for('teams.index'))
    
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            name = data.get('name', '').strip()
            description = data.get('description', '').strip()
            max_members = data.get('max_members', 4)
        else:
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            max_members = request.form.get('max_members', 4, type=int)
        
        # 验证输入
        errors = []
        
        if not name or len(name) < 2:
            errors.append('团队名称至少2个字符')
        elif Team.query.filter_by(name=name).first():
            errors.append('团队名称已存在')
        
        if max_members < 1 or max_members > 10:
            errors.append('团队成员数量应在1-10之间')
        
        if errors:
            if request.is_json:
                return jsonify({'errors': errors}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('teams/create.html')
        
        # 生成邀请码
        invite_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        while Team.query.filter_by(invite_code=invite_code).first():
            invite_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        
        # 创建团队
        team = Team(
            name=name,
            description=description,
            max_members=max_members,
            invite_code=invite_code,
            captain_id=current_user.id
        )
        
        try:
            db.session.add(team)
            db.session.flush()  # 获取team.id
            
            # 将创建者加入团队
            current_user.team_id = team.id
            db.session.commit()
            
            if request.is_json:
                return jsonify({
                    'message': '团队创建成功',
                    'team': team.to_dict(),
                    'invite_code': invite_code
                }), 201
            
            flash(f'团队创建成功！邀请码：{invite_code}', 'success')
            return redirect(url_for('teams.detail', team_id=team.id))
        
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'error': '创建团队失败，请重试'}), 500
            flash('创建团队失败，请重试', 'error')
    
    return render_template('teams/create.html')


@teams_bp.route('/<int:team_id>/join', methods=['POST'])
@login_required
def join(team_id):
    """加入团队（通过团队ID）"""
    if current_user.team_id:
        if request.is_json:
            return jsonify({'error': '您已经在一个团队中'}), 400
        flash('您已经在一个团队中', 'error')
        return redirect(url_for('teams.detail', team_id=team_id))
    
    team = Team.query.get_or_404(team_id)
    
    if not team.is_active:
        if request.is_json:
            return jsonify({'error': '团队已被禁用'}), 403
        flash('团队已被禁用', 'error')
        return redirect(url_for('teams.index'))
    
    if len(team.members) >= team.max_members:
        if request.is_json:
            return jsonify({'error': '团队已满'}), 400
        flash('团队已满', 'error')
        return redirect(url_for('teams.detail', team_id=team_id))
    
    current_user.team_id = team_id
    
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
    
    return redirect(url_for('teams.detail', team_id=team_id))


@teams_bp.route('/<int:team_id>/leave', methods=['POST'])
@login_required
def leave(team_id):
    """离开团队"""
    if current_user.team_id != team_id:
        if request.is_json:
            return jsonify({'error': '您不在此团队中'}), 400
        flash('您不在此团队中', 'error')
        return redirect(url_for('teams.detail', team_id=team_id))
    
    team = Team.query.get_or_404(team_id)
    
    # 如果是队长且团队还有其他成员，需要先转让队长
    if team.captain_id == current_user.id and len(team.members) > 1:
        if request.is_json:
            return jsonify({'error': '队长离开前需要先转让队长权限'}), 400
        flash('队长离开前需要先转让队长权限', 'error')
        return redirect(url_for('teams.detail', team_id=team_id))
    
    current_user.team_id = None
    
    # 如果是最后一个成员，删除团队
    if len(team.members) == 1:
        team.is_active = False
    
    try:
        db.session.commit()
        if request.is_json:
            return jsonify({'message': '已离开团队'})
        flash('已离开团队', 'success')
        return redirect(url_for('teams.index'))
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': '离开团队失败'}), 500
        flash('离开团队失败', 'error')
    
    return redirect(url_for('teams.detail', team_id=team_id))


@teams_bp.route('/<int:team_id>/transfer_captain', methods=['POST'])
@login_required
def transfer_captain(team_id):
    """转让队长"""
    team = Team.query.get_or_404(team_id)
    
    if team.captain_id != current_user.id:
        if request.is_json:
            return jsonify({'error': '只有队长可以转让队长权限'}), 403
        flash('只有队长可以转让队长权限', 'error')
        return redirect(url_for('teams.detail', team_id=team_id))
    
    if request.is_json:
        data = request.get_json()
        new_captain_id = data.get('new_captain_id')
    else:
        new_captain_id = request.form.get('new_captain_id', type=int)
    
    if not new_captain_id:
        if request.is_json:
            return jsonify({'error': '请选择新队长'}), 400
        flash('请选择新队长', 'error')
        return redirect(url_for('teams.detail', team_id=team_id))
    
    new_captain = User.query.get(new_captain_id)
    if not new_captain or new_captain.team_id != team_id:
        if request.is_json:
            return jsonify({'error': '新队长必须是团队成员'}), 400
        flash('新队长必须是团队成员', 'error')
        return redirect(url_for('teams.detail', team_id=team_id))
    
    team.captain_id = new_captain_id
    
    try:
        db.session.commit()
        if request.is_json:
            return jsonify({'message': f'已将队长权限转让给 {new_captain.username}'})
        flash(f'已将队长权限转让给 {new_captain.username}', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': '转让队长失败'}), 500
        flash('转让队长失败', 'error')
    
    return redirect(url_for('teams.detail', team_id=team_id))


@teams_bp.route('/<int:team_id>/regenerate_invite', methods=['POST'])
@login_required
def regenerate_invite_code(team_id):
    """重新生成邀请码"""
    team = Team.query.get_or_404(team_id)
    
    if team.captain_id != current_user.id:
        if request.is_json:
            return jsonify({'error': '只有队长可以重新生成邀请码'}), 403
        flash('只有队长可以重新生成邀请码', 'error')
        return redirect(url_for('teams.detail', team_id=team_id))
    
    # 生成新的邀请码
    invite_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    while Team.query.filter_by(invite_code=invite_code).first():
        invite_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    
    team.invite_code = invite_code
    
    try:
        db.session.commit()
        if request.is_json:
            return jsonify({
                'message': '邀请码已重新生成',
                'invite_code': invite_code
            })
        flash(f'邀请码已重新生成：{invite_code}', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': '重新生成邀请码失败'}), 500
        flash('重新生成邀请码失败', 'error')
    
    return redirect(url_for('teams.detail', team_id=team_id))