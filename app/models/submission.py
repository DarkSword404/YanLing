from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app import db


class Submission(db.Model):
    """提交记录模型"""
    __tablename__ = 'submissions'
    
    id = Column(Integer, primary_key=True)
    
    # 关联关系
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship('User', back_populates='submissions')
    
    challenge_id = Column(Integer, ForeignKey('challenges.id'), nullable=False)
    challenge = relationship('Challenge', back_populates='submissions')
    
    # 提交内容
    submitted_flag = Column(String(255), nullable=False)
    is_correct = Column(Boolean, default=False)
    
    # 得分信息
    points_awarded = Column(Integer, default=0)
    
    # IP地址和用户代理
    ip_address = Column(String(45))  # 支持IPv6
    user_agent = Column(Text)
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Submission {self.id}: {self.user.username} -> {self.challenge.name}>'
    
    def check_and_update_correctness(self):
        """检查并更新提交的正确性"""
        # 确保challenge关联存在
        if not self.challenge:
            # 如果关联不存在，尝试重新加载
            from app.models.challenge import Challenge
            self.challenge = Challenge.query.get(self.challenge_id)
            
        if not self.challenge:
            # 如果仍然找不到challenge，返回False
            self.is_correct = False
            self.points_awarded = 0
            return False
            
        if self.challenge.check_flag(self.submitted_flag):
            self.is_correct = True
            # 计算得分
            if self.challenge.is_dynamic:
                self.points_awarded = self.challenge.get_dynamic_points()
            else:
                self.points_awarded = self.challenge.points
            return True
        else:
            self.is_correct = False
            self.points_awarded = 0
            return False
    
    def is_first_blood(self):
        """检查是否为一血"""
        if not self.is_correct:
            return False
        
        first_solve = (db.session.query(Submission)
                      .filter_by(challenge_id=self.challenge_id, is_correct=True)
                      .order_by(Submission.created_at.asc())
                      .first())
        
        return first_solve and first_solve.id == self.id
    
    def get_rank(self):
        """获取解题排名"""
        if not self.is_correct:
            return None
        
        earlier_solves = (db.session.query(Submission)
                         .filter_by(challenge_id=self.challenge_id, is_correct=True)
                         .filter(Submission.created_at < self.created_at)
                         .count())
        
        return earlier_solves + 1
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'challenge_id': self.challenge_id,
            'challenge_name': self.challenge.name if self.challenge else None,
            'submitted_flag': self.submitted_flag,
            'is_correct': self.is_correct,
            'points_awarded': self.points_awarded,
            'is_first_blood': self.is_first_blood(),
            'rank': self.get_rank(),
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def get_user_submissions(user_id, challenge_id=None):
        """获取用户的提交记录"""
        query = db.session.query(Submission).filter_by(user_id=user_id)
        if challenge_id:
            query = query.filter_by(challenge_id=challenge_id)
        return query.order_by(Submission.created_at.desc()).all()
    
    @staticmethod
    def get_challenge_submissions(challenge_id, correct_only=False):
        """获取题目的提交记录"""
        query = db.session.query(Submission).filter_by(challenge_id=challenge_id)
        if correct_only:
            query = query.filter_by(is_correct=True)
        return query.order_by(Submission.created_at.desc()).all()
    
    @staticmethod
    def get_team_submissions(team_id, challenge_id=None):
        """获取团队的提交记录"""
        from app.models.user import User
        query = (db.session.query(Submission)
                .join(User)
                .filter(User.team_id == team_id))
        if challenge_id:
            query = query.filter(Submission.challenge_id == challenge_id)
        return query.order_by(Submission.created_at.desc()).all()
    
    @staticmethod
    def get_recent_submissions(limit=50):
        """获取最近的提交记录"""
        return (db.session.query(Submission)
                .order_by(Submission.created_at.desc())
                .limit(limit)
                .all())
    
    @staticmethod
    def get_correct_submissions_count(user_id=None, team_id=None):
        """获取正确提交数量"""
        query = db.session.query(Submission).filter_by(is_correct=True)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        elif team_id:
            from app.models.user import User
            query = query.join(User).filter(User.team_id == team_id)
        
        return query.count()