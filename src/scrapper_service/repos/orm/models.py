from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Chat(Base):
    __tablename__ = "chats"

    id = Column(BigInteger, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True)
    url = Column(Text, unique=True, nullable=False)
    resource_type = Column(String(20))
    resource_id = Column(String(255))
    last_checked = Column(DateTime(timezone=True))
    last_updated = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_links_url", url),
        Index("idx_links_resource_type", resource_type),
        Index("idx_links_last_updated", last_updated),
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    __table_args__ = (
        UniqueConstraint("chat_id", "link_id", name="uq_subscriptions_chat_link"),
        Index("idx_subscriptions_chat_id", "chat_id"),
        Index("idx_subscriptions_link_id", "link_id"),
        Index("idx_subscriptions_tags", "tags", postgresql_using="gin"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(
        BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    link_id = Column(
        Integer, ForeignKey("links.id", ondelete="CASCADE"), nullable=False
    )
    tags = Column(ARRAY(String), server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Update(Base):
    __tablename__ = "updates"
    __table_args__ = (
        Index("idx_updates_link_id", "link_id"),
        Index("idx_updates_checked_at", "checked_at"),
    )

    id = Column(Integer, primary_key=True)
    link_id = Column(
        Integer, ForeignKey("links.id", ondelete="CASCADE"), nullable=False
    )
    checked_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True))
    had_changes = Column(Boolean, default=False)
