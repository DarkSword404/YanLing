from datetime import datetime
from app import db

class Team(db.Model):
    """团队模型"""
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    
    # Team settings
    is_active = db.Column(db.Boolean, default=True)
    max_members = db.Column(db.Integer, default=4)
    invite_code = db.Column(db.String(32), unique=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Captain relationship
    captain_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    captain = db.relationship('User', foreign_keys=[captain_id], backref='captained_team')
    
    # Team submissions (through members)
    def get_submissions(self):
        """获取团队所有提交"""
        from app.models.submission import Submission
        member_ids = [member.id for member in self.members]
        return Submission.query.filter(Submission.user_id.in_(member_ids)).all()
    
    def get_score(self):
        """获取团队总分"""
        solved_challenges = set()
        for member in self.members:
            for submission in member.submissions:
                if submission.is_correct:
                    solved_challenges.add(submission.challenge_id)
        
        from app.models.challenge import Challenge
        total_score = 0
        for challenge_id in solved_challenges:
            challenge = Challenge.query.get(challenge_id)
            if challenge:
                total_score += challenge.points
        
        return total_score
    
    def get_solved_challenges(self):
        """获取团队已解决的题目"""
        solved_challenges = set()
        for member in self.members:
            for submission in member.submissions:
                if submission.is_correct:
                    solved_challenges.add(submission.challenge)
        return list(solved_challenges)
    
    def has_solved(self, challenge):
        """检查团队是否已解决某题目"""
        for member in self.members:
            if member.has_solved(challenge):
                return True
        return False
    
    def can_join(self):
        """检查是否可以加入团队"""
        return self.is_active and len(self.members) < self.max_members
    
    def generate_invite_code(self):
        """生成邀请码"""
        import secrets
        self.invite_code = secrets.token_urlsafe(16)
        return self.invite_code
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'max_members': self.max_members,
            'member_count': len(self.members),
            'captain_id': self.captain_id,
            'captain_username': self.captain.username if self.captain else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'score': self.get_score()
        }
    
    def __repr__(self):
        return f'<Team {self.name}>'