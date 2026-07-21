"""Shared SQLAlchemy declarative base for application tables."""

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class inherited by every ORM table model."""


class Company(Base):
    """A listed company that may be included in the Nikkei 225."""

    __tablename__ = "companies"

    code: Mapped[str] = mapped_column(String(5), primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100), index=True)
    market: Mapped[str | None] = mapped_column(String(100))
    is_nikkei225: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"Company(code={self.code!r}, company_name={self.company_name!r}, "
            f"is_nikkei225={self.is_nikkei225!r})"
        )
