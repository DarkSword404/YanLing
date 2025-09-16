from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from app.models import User, Team, Challenge, Category, Submission
from app import db
from sqlalchemy import func, desc

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """主页"""
    # 获取统计数据
    stats = {
        'total_users': User.query.count(),
        'total_teams': Team.query.count(),
        'total_challenges': Challenge.query.filter_by(is_active=True).count(),
        'total_submissions': Submission.query.count()
    }
    
    # 获取最新公告（暂时使用静态数据）
    announcements = [
        {
            'title': '欢迎来到雁翎CTF平台',
            'content': '这是一个专业的CTF竞赛平台，提供丰富的网络安全挑战题目。',
            'created_at': '2024-01-01'
        }
    ]
    
    # 获取最近解题记录
    recent_solves = (db.session.query(Submission)
                    .filter_by(is_correct=True)
                    .order_by(desc(Submission.created_at))
                    .limit(10)
                    .all())
    
    recent_solves_data = []
    for solve in recent_solves:
        recent_solves_data.append({
            'username': solve.user.username,
            'challenge_name': solve.challenge.name,
            'points': solve.points_awarded,
            'created_at': solve.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    if request.is_json:
        return jsonify({
            'stats': stats,
            'announcements': announcements,
            'recent_solves': recent_solves_data
        })
    
    return render_template('index.html', 
                         stats=stats, 
                         announcements=announcements,
                         recent_solves=recent_solves_data)


@main_bp.route('/scoreboard')
def scoreboard():
    """积分榜"""
    view_type = request.args.get('view', 'user')  # 默认显示个人排行
    page = request.args.get('page', 1, type=int)
    
    # 统计数据
    stats = {
        'total_participants': 0,
        'total_solves': Submission.query.filter_by(is_correct=True).count(),
        'avg_score': 0,
        'highest_score': 0
    }
    
    rankings = []
    pagination = None
    
    if view_type == 'team':
        # 团队积分榜
        team_query = (db.session.query(
            Team.id,
            Team.name,
            func.sum(Submission.points_awarded).label('score'),
            func.count(func.distinct(Submission.challenge_id)).label('solve_count'),
            func.max(Submission.created_at).label('last_submission'),
            func.count(func.distinct(User.id)).label('member_count')
        ).join(User, Team.id == User.team_id)
         .join(Submission, User.id == Submission.user_id)
         .filter(Submission.is_correct == True)
         .group_by(Team.id, Team.name)
         .order_by(desc('score')))
        
        teams = team_query.all()
        stats['total_participants'] = len(teams)
        
        for team_data in teams:
            team = Team.query.get(team_data.id)
            rankings.append({
                'id': team_data.id,
                'name': team_data.name,
                'score': int(team_data.score) if team_data.score else 0,
                'solve_count': team_data.solve_count,
                'last_submission': team_data.last_submission,
                'member_count': team_data.member_count,
                'captain': team.captain if team else None
            })
            
        if rankings:
            stats['highest_score'] = rankings[0]['score']
            stats['avg_score'] = round(sum(r['score'] for r in rankings) / len(rankings), 1)
    
    else:
        # 个人积分榜
        user_query = (db.session.query(
            User.id,
            User.username,
            User.nickname,
            func.sum(Submission.points_awarded).label('score'),
            func.count(Submission.id).label('solve_count'),
            func.max(Submission.created_at).label('last_submission')
        ).join(Submission, User.id == Submission.user_id)
         .filter(Submission.is_correct == True)
         .group_by(User.id, User.username, User.nickname)
         .order_by(desc('score')))
        
        users = user_query.all()
        stats['total_participants'] = len(users)
        
        for user_data in users:
            user = User.query.get(user_data.id)
            rankings.append({
                'id': user_data.id,
                'username': user_data.username,
                'nickname': user_data.nickname,
                'score': int(user_data.score) if user_data.score else 0,
                'solve_count': user_data.solve_count,
                'last_submission': user_data.last_submission,
                'team': user.team if user else None
            })
            
        if rankings:
            stats['highest_score'] = rankings[0]['score']
            stats['avg_score'] = round(sum(r['score'] for r in rankings) / len(rankings), 1)
    
    if request.is_json:
        return jsonify({
            'view_type': view_type,
            'stats': stats,
            'rankings': rankings
        })
    
    return render_template('scoreboard.html',
                         view_type=view_type,
                         stats=stats,
                         rankings=rankings,
                         pagination=pagination)


@main_bp.route('/about')
def about():
    """关于页面"""
    about_info = {
        'platform_name': '雁翎CTF与网络安全攻防实训平台',
        'version': 'v0.1.0',
        'description': '专业的CTF竞赛和网络安全实训平台，提供丰富的挑战题目和实战环境。',
        'features': [
            '多类型CTF题目支持',
            '团队协作功能',
            '实时积分排行榜',
            'Docker容器化题目环境',
            '智能提示系统',
            '详细的解题统计'
        ],
        'tech_stack': [
            'Flask Web框架',
            'SQLAlchemy ORM',
            'Redis缓存',
            'Celery任务队列',
            'Docker容器化',
            'Bootstrap前端框架'
        ]
    }
    
    if request.is_json:
        return jsonify(about_info)
    
    return render_template('about.html', about=about_info)


@main_bp.route('/api/stats')
def api_stats():
    """API: 获取平台统计数据"""
    stats = {
        'users': {
            'total': User.query.count(),
            'active': User.query.filter_by(is_active=True).count()
        },
        'teams': {
            'total': Team.query.count(),
            'active': Team.query.filter_by(is_active=True).count()
        },
        'challenges': {
            'total': Challenge.query.count(),
            'active': Challenge.query.filter_by(is_active=True).count(),
            'by_category': {}
        },
        'submissions': {
            'total': Submission.query.count(),
            'correct': Submission.query.filter_by(is_correct=True).count()
        }
    }
    
    # 按分类统计题目数量
    categories = Category.query.all()
    for category in categories:
        stats['challenges']['by_category'][category.name] = {
            'total': len(category.challenges),
            'active': len([c for c in category.challenges if c.is_active])
        }
    
    return jsonify(stats)


@main_bp.route('/search')
def search():
    """搜索功能"""
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')  # all, users, teams, challenges
    
    if not query:
        if request.is_json:
            return jsonify({'error': '搜索关键词不能为空'}), 400
        return render_template('search.html', results={}, query=query)
    
    results = {}
    
    if search_type in ['all', 'users']:
        users = User.query.filter(
            User.username.contains(query)
        ).filter_by(is_active=True).limit(20).all()
        results['users'] = [{'id': u.id, 'username': u.username, 'score': u.get_score()} for u in users]
    
    if search_type in ['all', 'teams']:
        teams = Team.query.filter(
            Team.name.contains(query)
        ).filter_by(is_active=True).limit(20).all()
        results['teams'] = [{'id': t.id, 'name': t.name, 'member_count': len(t.members)} for t in teams]
    
    if search_type in ['all', 'challenges']:
        challenges = Challenge.query.filter(
            Challenge.name.contains(query)
        ).filter_by(is_active=True).limit(20).all()
        results['challenges'] = [c.to_dict() for c in challenges]
    
    if request.is_json:
        return jsonify(results)
    
    return render_template('search.html', results=results, query=query)


@main_bp.route('/user/<int:user_id>/submissions')
def user_submissions(user_id):
    """用户提交记录页面"""
    user = User.query.get_or_404(user_id)
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # 获取用户的提交记录
    submissions_query = (Submission.query
                        .filter_by(user_id=user_id)
                        .order_by(desc(Submission.created_at)))
    
    pagination = submissions_query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    submissions = pagination.items
    
    # 统计数据
    stats = {
        'total_submissions': Submission.query.filter_by(user_id=user_id).count(),
        'correct_submissions': Submission.query.filter_by(user_id=user_id, is_correct=True).count(),
        'total_points': db.session.query(func.sum(Submission.points_awarded)).filter_by(user_id=user_id, is_correct=True).scalar() or 0,
        'solved_challenges': len(set(s.challenge_id for s in Submission.query.filter_by(user_id=user_id, is_correct=True).all()))
    }
    
    if request.is_json:
        return jsonify({
            'user': {
                'id': user.id,
                'username': user.username,
                'nickname': user.nickname
            },
            'stats': stats,
            'submissions': [s.to_dict() for s in submissions],
            'pagination': {
                'page': page,
                'pages': pagination.pages,
                'per_page': per_page,
                'total': pagination.total,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        })
    
    return render_template('user_submissions.html', 
                         user=user, 
                         submissions=submissions,
                         stats=stats,
                         pagination=pagination)