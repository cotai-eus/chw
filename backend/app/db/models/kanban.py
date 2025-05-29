from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class KanbanBoard(Base):
    __tablename__ = "kanban_boards"
    
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # Informações básicas
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Configurações
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)
    
    # Relacionamentos
    company = relationship("Company", back_populates="kanban_boards")
    lists = relationship("KanbanList", back_populates="board", cascade="all, delete-orphan")
    members = relationship("KanbanMember", back_populates="board", cascade="all, delete-orphan")


class KanbanList(Base):
    __tablename__ = "kanban_lists"
    
    board_id = Column(UUID(as_uuid=True), ForeignKey("kanban_boards.id", ondelete="CASCADE"), nullable=False)
    
    # Informações básicas
    name = Column(String(255), nullable=False)
    position = Column(Integer, nullable=False)
    
    # Configurações
    is_archived = Column(Boolean, default=False)
    color = Column(String(7), nullable=True)  # Hex color
    
    # Relacionamentos
    board = relationship("KanbanBoard", back_populates="lists")
    cards = relationship("KanbanCard", back_populates="list", cascade="all, delete-orphan")


class KanbanCard(Base):
    __tablename__ = "kanban_cards"
    
    list_id = Column(UUID(as_uuid=True), ForeignKey("kanban_lists.id", ondelete="CASCADE"), nullable=False)
    tender_id = Column(UUID(as_uuid=True), ForeignKey("tenders.id"), nullable=True)
    
    # Informações básicas
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    position = Column(Integer, nullable=False)
    
    # Configurações
    color = Column(String(7), nullable=True)  # Hex color
    is_archived = Column(Boolean, default=False)
    
    # Dados adicionais
    labels = Column(JSON, default=[])
    due_date = Column(String(50), nullable=True)
    
    # Relacionamentos
    list = relationship("KanbanList", back_populates="cards")
    tender = relationship("Tender")
    comments = relationship("KanbanComment", back_populates="card", cascade="all, delete-orphan")
    card_members = relationship("KanbanCardMember", back_populates="card", cascade="all, delete-orphan")


class KanbanComment(Base):
    __tablename__ = "kanban_comments"
    
    card_id = Column(UUID(as_uuid=True), ForeignKey("kanban_cards.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Conteúdo
    content = Column(Text, nullable=False)
    
    # Relacionamentos
    card = relationship("KanbanCard", back_populates="comments")
    user = relationship("User")


class KanbanMember(Base):
    __tablename__ = "kanban_members"
    
    board_id = Column(UUID(as_uuid=True), ForeignKey("kanban_boards.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Permissões
    can_edit = Column(Boolean, default=True)
    can_delete = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    
    # Relacionamentos
    board = relationship("KanbanBoard", back_populates="members")
    user = relationship("User")


class KanbanCardMember(Base):
    __tablename__ = "kanban_card_members"
    
    card_id = Column(UUID(as_uuid=True), ForeignKey("kanban_cards.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Relacionamentos
    card = relationship("KanbanCard", back_populates="card_members")
    user = relationship("User")
