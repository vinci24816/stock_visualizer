"""Shared SQLAlchemy declarative base for application tables."""

from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Numeric, String, text
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


class DailyPrice(Base):
    """上場銘柄の日次株価と株式分割等を反映した調整後株価。"""

    __tablename__ = "daily_prices"

    code: Mapped[str] = mapped_column(
        String(5),
        ForeignKey("companies.code"),
        primary_key=True,
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True, index=True)
    open: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    high: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    low: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    close: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    volume: Mapped[int | None] = mapped_column(BigInteger)
    turnover_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    adjustment_factor: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))
    adjusted_open: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    adjusted_high: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    adjusted_low: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    adjusted_close: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    adjusted_volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 6))

    def __repr__(self) -> str:
        return (
            f"DailyPrice(code={self.code!r}, date={self.date!r}, "
            f"close={self.close!r})"
        )
