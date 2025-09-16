from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app import db


class Hint(db.Model):
    """提示模型"""
    __tablename__ = 'hints'
    
    id = Column(Integer, primary_key=True)
    
    # 关联关系
    challenge_id = Column(Integer, ForeignKey('challenges.id'), nullable=False)
    challenge = relationship('Challenge', back_populates='hints')
    
    # 提示内容
    content = Column(Text, nullable=False)
    cost = Column(Integer, default=0)  # 提示消耗的分数
    
    # 提示状态
    is_active = Column(Boolean, default=True)
    order = Column(Integer, default=1)  # 提示顺序
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系 - 用户购买的提示
    purchased_hints = relationship('UserHint', back_populates='hint', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Hint {self.id}: {self.challenge.name if self.challenge else "Unknown"}>'
    
    def is_purchased_by_user(self, user_id):
        """检查用户是否已购买此提示"""
        return any(uh.user_id == user_id for uh in self.purchased_hints)
    
    def get_purchase_count(self):
        """获取购买次数"""
        return len(self.purchased_hints)
    
    def to_dict(self, user_id=None):
        """转换为字典"""
        data = {
            'id': self.id,
            'challenge_id': self.challenge_id,
            'cost': self.cost,
            'is_active': self.is_active,
            'order': self.order,
            'purchase_count': self.get_purchase_count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        # 只有购买了提示的用户才能看到内容
        if user_id and self.is_purchased_by_user(user_id):
            data['content'] = self.content
            data['is_purchased'] = True
        else:
            data['content'] = None
            data['is_purchased'] = False
            
        return data


class UserHint(db.Model):
    """用户购买提示记录"""
    __tablename__ = 'user_hints'
    
    id = Column(Integer, primary_key=True)
    
    # 关联关系
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship('User', back_populates='purchased_hints')
    
    hint_id = Column(Integer, ForeignKey('hints.id'), nullable=False)
    hint = relationship('Hint', back_populates='purchased_hints')
    
    # 购买信息
    cost_paid = Column(Integer, nullable=False)  # 实际支付的分数
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserHint {self.user.username} -> Hint {self.hint_id}>'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'hint_id': self.hint_id,
            'cost_paid': self.cost_paid,
            'hint_content': self.hint.content if self.hint else None,
            'challenge_name': self.hint.challenge.name if self.hint and self.hint.challenge else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }