from datetime import datetime
from app import db

class TeamRequest(db.Model):
    """团队加入申请模型"""
    __tablename__ = 'team_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 申请者信息
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', foreign_keys=[user_id], backref='team_requests')
    
    # 目标团队信息
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    team = db.relationship('Team', foreign_keys=[team_id], backref='join_requests')
    
    # 申请信息
    message = db.Column(db.Text)  # 申请理由
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    
    # 审核信息
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # 审核者ID
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    reviewed_at = db.Column(db.DateTime)
    review_message = db.Column(db.Text)  # 审核备注
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def approve(self, reviewer_id, message=None):
        """批准申请"""
        self.status = 'approved'
        self.reviewed_by = reviewer_id
        self.reviewed_at = datetime.utcnow()
        self.review_message = message
        
        # 将用户加入团队
        from app.models.user import User
        user = User.query.get(self.user_id)
        if user and self.team.can_join():
            user.team_id = self.team_id
            db.session.commit()
            return True
        return False
    
    def reject(self, reviewer_id, message=None):
        """拒绝申请"""
        self.status = 'rejected'
        self.reviewed_by = reviewer_id
        self.reviewed_at = datetime.utcnow()
        self.review_message = message
        db.session.commit()
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'team_id': self.team_id,
            'team_name': self.team.name if self.team else None,
            'message': self.message,
            'status': self.status,
            'reviewed_by': self.reviewed_by,
            'reviewer_username': self.reviewer.username if self.reviewer else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'review_message': self.review_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def get_pending_requests_for_team(team_id):
        """获取团队的待审核申请"""
        return TeamRequest.query.filter_by(
            team_id=team_id, 
            status='pending'
        ).order_by(TeamRequest.created_at.desc()).all()
    
    @staticmethod
    def get_user_pending_request(user_id):
        """获取用户的待审核申请"""
        return TeamRequest.query.filter_by(
            user_id=user_id, 
            status='pending'
        ).first()
    
    @staticmethod
    def has_pending_request(user_id, team_id):
        """检查用户是否已有对该团队的待审核申请"""
        return TeamRequest.query.filter_by(
            user_id=user_id,
            team_id=team_id,
            status='pending'
        ).first() is not None