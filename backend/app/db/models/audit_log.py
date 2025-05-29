from sqlalchemy import Column, String, Text, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from app.db.base_class import Base
from enum import Enum


class AuditAction(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    VIEW = "VIEW"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    # Ação realizada
    action = Column(SAEnum(AuditAction), nullable=False)
    resource_type = Column(String(100), nullable=False)  # Ex: "tender", "quote", "user"
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Detalhes da ação
    description = Column(Text, nullable=True)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    
    # Contexto da requisição
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    endpoint = Column(String(255), nullable=True)
    
    # Relacionamentos
    user = relationship("User")
    company = relationship("Company")
