from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from app import db
import hashlib
import json


class Challenge(db.Model):
    """题目模型"""
    __tablename__ = 'challenges'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    flag = Column(String(255), nullable=False)
    points = Column(Integer, default=100)
    max_attempts = Column(Integer, default=0)  # 0表示无限制
    
    # 题目状态
    is_active = Column(Boolean, default=True)
    is_dynamic = Column(Boolean, default=False)  # 是否为动态分值
    
    # 分类关联
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    category = relationship('Category', back_populates='challenges')
    
    # 文件和资源
    files = Column(Text)  # JSON格式存储文件列表
    docker_image = Column(String(255))  # Docker镜像名称
    docker_port = Column(Integer)  # 容器端口
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    submissions = relationship('Submission', back_populates='challenge', cascade='all, delete-orphan')
    hints = relationship('Hint', back_populates='challenge', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Challenge {self.name}>'
    
    def check_flag(self, submitted_flag):
        """验证flag"""
        # 去除首尾空格并转换为小写进行比较
        return self.flag.strip().lower() == submitted_flag.strip().lower()
    
    def get_dynamic_points(self):
        """计算动态分值"""
        if not self.is_dynamic:
            return self.points
        
        # 获取解题人数
        solved_count = len([s for s in self.submissions if s.is_correct])
        
        # 动态分值算法：基础分值 - (解题人数 * 衰减系数)
        decay_factor = 5
        min_points = max(10, self.points // 4)  # 最低分值
        
        dynamic_points = max(min_points, self.points - (solved_count * decay_factor))
        return dynamic_points
    
    def get_solve_count(self):
        """获取解题人数"""
        return len([s for s in self.submissions if s.is_correct])
    
    def get_attempt_count(self):
        """获取尝试次数"""
        return len(self.submissions)
    
    def is_solved_by_user(self, user_id):
        """检查用户是否已解题"""
        return any(s.user_id == user_id and s.is_correct for s in self.submissions)
    
    def is_solved_by_team(self, team_id):
        """检查团队是否已解题"""
        return any(s.user.team_id == team_id and s.is_correct for s in self.submissions)
    
    def get_files_list(self):
        """获取文件列表"""
        if self.files:
            try:
                return json.loads(self.files)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_files_list(self, files_list):
        """设置文件列表"""
        self.files = json.dumps(files_list)
    
    def get_first_blood(self):
        """获取一血信息"""
        first_solve = (db.session.query(Submission)
                      .filter_by(challenge_id=self.id, is_correct=True)
                      .order_by(Submission.created_at.asc())
                      .first())
        return first_solve
    
    def get_solve_rate(self):
        """获取解题率"""
        total_attempts = self.get_attempt_count()
        if total_attempts == 0:
            return 0
        return (self.get_solve_count() / total_attempts) * 100
    
    def to_dict(self, include_flag=False):
        """转换为字典"""
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'points': self.get_dynamic_points() if self.is_dynamic else self.points,
            'category': self.category.name if self.category else None,
            'is_active': self.is_active,
            'is_dynamic': self.is_dynamic,
            'files': self.get_files_list(),
            'docker_image': self.docker_image,
            'docker_port': self.docker_port,
            'solve_count': self.get_solve_count(),
            'attempt_count': self.get_attempt_count(),
            'solve_rate': round(self.get_solve_rate(), 2),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_flag:
            data['flag'] = self.flag
            
        return data