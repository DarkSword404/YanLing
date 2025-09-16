from datetime import datetime
from app import db

class Category(db.Model):
    """题目分类模型"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#007bff')  # Hex color code
    icon = db.Column(db.String(50))  # Icon class name
    
    # Category settings
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Challenges relationship
    challenges = db.relationship('Challenge', back_populates='category', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_challenge_count(self):
        """获取分类下的题目数量"""
        return self.challenges.filter_by(is_active=True).count()
    
    def get_solved_count(self, user=None, team=None):
        """获取已解决的题目数量"""
        if not user and not team:
            return 0
        
        solved_count = 0
        for challenge in self.challenges.filter_by(is_active=True):
            if user and user.has_solved(challenge):
                solved_count += 1
            elif team and team.has_solved(challenge):
                solved_count += 1
        
        return solved_count
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'icon': self.icon,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'challenge_count': self.get_challenge_count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Category {self.name}>'