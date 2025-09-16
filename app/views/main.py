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
    # 个人积分榜
    user_scores = (db.session.query(
        User.id,
        User.username,
        func.sum(Submission.points_awarded).label('total_score'),
        func.count(Submission.id).label('solve_count')
    ).join(Submission, User.id == Submission.user_id)
     .filter(Submission.is_correct == True)
     .group_by(User.id, User.username)
     .order_by(desc('total_score'))
     .limit(50)
     .all())
    
    user_scoreboard = []
    for rank, (user_id, username, total_score, solve_count) in enumerate(user_scores, 1):
        user_scoreboard.append({
            'rank': rank,
            'username': username,
            'score': int(total_score) if total_score else 0,
            'solve_count': solve_count
        })
    
    # 团队积分榜
    team_scores = (db.session.query(
        Team.id,
        Team.name,
        func.sum(Submission.points_awarded).label('total_score'),
        func.count(func.distinct(Submission.challenge_id)).label('solve_count')
    ).join(User, Team.id == User.team_id)
     .join(Submission, User.id == Submission.user_id)
     .filter(Submission.is_correct == True)
     .group_by(Team.id, Team.name)
     .order_by(desc('total_score'))
     .limit(50)
     .all())
    
    team_scoreboard = []
    for rank, (team_id, team_name, total_score, solve_count) in enumerate(team_scores, 1):
        team_scoreboard.append({
            'rank': rank,
            'team_name': team_name,
            'score': int(total_score) if total_score else 0,
            'solve_count': solve_count
        })
    
    if request.is_json:
        return jsonify({
            'user_scoreboard': user_scoreboard,
            'team_scoreboard': team_scoreboard
        })
    
    return render_template('scoreboard.html',
                         user_scoreboard=user_scoreboard,
                         team_scoreboard=team_scoreboard)


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