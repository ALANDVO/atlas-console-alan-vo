from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import String, Text, DateTime, Integer, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ScopeEntryType(str, PyEnum):
    IP_RANGE = "ip_range"
    PORT_RANGE = "port_range"
    SERVICE = "service"


class ScopeEntry(Base):
    __tablename__ = "scope_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[ScopeEntryType] = mapped_column(
        SQLEnum(ScopeEntryType), nullable=False, index=True
    )
    value: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    creator: Mapped["User"] = relationship("User", back_populates="scope_entries")

    def __repr__(self) -> str:
        return f"<ScopeEntry(id={self.id}, type={self.type}, value={self.value})>"


class ScopeImportExport(Base):
    __tablename__ = "scope_import_export"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[str] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ScopeImportExport(id={self.id}, filename={self.filename}, format={self.format})>"
