"""
User and Role Models.
"""
import enum
from sqlalchemy import Column, String, Boolean, Enum
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import UUIDPrimaryKeyMixin, TimestampMixin

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    ASSIGNER = "ASSIGNER"
    INTERN = "INTERN"

class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.INTERN, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    assigned_tasks = relationship("Task", back_populates="assigner", foreign_keys="Task.assigner_id")
    intern_tasks = relationship("Task", back_populates="intern", foreign_keys="Task.intern_id")
    audit_logs = relationship("AuditLog", back_populates="actor", foreign_keys="AuditLog.actor_id")
