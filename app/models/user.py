from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile information
    nickname = db.Column(db.String(80))
    bio = db.Column(db.Text)
    avatar_url = db.Column(db.String(255))
    
    # Account status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Team relationship
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    team = db.relationship('Team', foreign_keys=[team_id], backref='members', lazy=True)
    
    # Submissions relationship
    submissions = db.relationship('Submission', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    purchased_hints = db.relationship('UserHint', back_populates='user', cascade='all, delete-orphan')
    
    def __init__(self, username, email, password=None, **kwargs):
        self.username = username
        self.email = email
        if password:
            self.set_password(password)
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def set_password(self, password):
        """设置密码哈希"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def get_score(self):
        """获取用户总分"""
        if self.team_id:
            return self.team.get_score()
        else:
            return sum(submission.challenge.points for submission in self.submissions 
                      if submission.is_correct)
    
    def get_solved_challenges(self):
        """获取已解决的题目"""
        return [submission.challenge for submission in self.submissions 
                if submission.is_correct]
    
    def has_solved(self, challenge):
        """检查是否已解决某题目"""
        return self.submissions.filter_by(challenge_id=challenge.id, is_correct=True).first() is not None
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'nickname': self.nickname,
            'bio': self.bio,
            'avatar_url': self.avatar_url,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'team_id': self.team_id,
            'score': self.get_score()
        }
    
    def __repr__(self):
        return f'<User {self.username}>'