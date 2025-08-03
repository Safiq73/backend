"""
Permission-related database models for CivicPulse

This module defines the SQLAlchemy models for the dynamic permission system
based on API routes and roles.
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class SystemRole(Base):
    """System roles that can be assigned to users"""
    __tablename__ = "system_roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    level = Column(Integer, default=0)  # Role hierarchy level
    color = Column(String(7))  # Hex color for UI
    is_system_role = Column(Boolean, default=False)  # Cannot be deleted if True
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user_roles = relationship("UserRole", back_populates="role")
    role_permissions = relationship("RoleAPIPermission", back_populates="role")

class APIPermission(Base):
    """API permissions based on actual route paths and HTTP methods"""
    __tablename__ = "api_permissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_path = Column(String(255), nullable=False)  # e.g., '/api/v1/posts/{post_id}'
    method = Column(String(10), nullable=False)  # e.g., 'GET', 'POST', 'PUT', 'DELETE', '*'
    permission_name = Column(String(150), nullable=False, index=True)  # e.g., 'posts.detail.get'
    description = Column(Text)
    category = Column(String(50), index=True)  # Group permissions by feature area
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('route_path', 'method', name='uq_api_permissions_route_method'),
    )
    
    # Relationships
    role_permissions = relationship("RoleAPIPermission", back_populates="permission")

class UserRole(Base):
    """Mapping between users and their assigned roles"""
    __tablename__ = "user_roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey('system_roles.id', ondelete='CASCADE'), nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))  # Optional expiration for temporary roles
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='uq_user_roles_user_role'),
    )
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="user_roles")
    role = relationship("SystemRole", back_populates="user_roles")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])

class RoleAPIPermission(Base):
    """Mapping between roles and API permissions"""
    __tablename__ = "role_api_permissions"
    
    role_id = Column(UUID(as_uuid=True), ForeignKey('system_roles.id', ondelete='CASCADE'), primary_key=True)
    api_permission_id = Column(UUID(as_uuid=True), ForeignKey('api_permissions.id', ondelete='CASCADE'), primary_key=True)
    granted = Column(Boolean, default=True)  # Can also be used to explicitly deny
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    role = relationship("SystemRole", back_populates="role_permissions")
    permission = relationship("APIPermission", back_populates="role_permissions")

class PermissionOverride(Base):
    """Individual permission overrides for specific users"""
    __tablename__ = "permission_overrides"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    api_permission_id = Column(UUID(as_uuid=True), ForeignKey('api_permissions.id', ondelete='CASCADE'), nullable=False)
    granted = Column(Boolean, nullable=False)  # True to grant, False to deny
    reason = Column(Text)  # Reason for the override
    granted_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    expires_at = Column(DateTime(timezone=True))  # Optional expiration
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'api_permission_id', name='uq_permission_overrides_user_permission'),
    )
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    permission = relationship("APIPermission")
    granted_by_user = relationship("User", foreign_keys=[granted_by])
