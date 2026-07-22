"""Shared SQLAlchemy declarative base for application tables."""

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    text,
)
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


class FinancialStatement(Base):
    """企業が開示した決算期ごとの財務情報サマリー。"""

    __tablename__ = "financial_statements"

    code: Mapped[str] = mapped_column(
        String(5),
        ForeignKey("companies.code"),
        primary_key=True,
    )
    fiscal_period: Mapped[str] = mapped_column(String(50), primary_key=True)
    disclosed_date: Mapped[date] = mapped_column(
        Date,
        primary_key=True,
        index=True,
    )
    document_type: Mapped[str | None] = mapped_column(String(100))
    fiscal_year_start: Mapped[date | None] = mapped_column(Date)
    fiscal_year_end: Mapped[date | None] = mapped_column(Date, index=True)

    net_sales: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    operating_profit: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    ordinary_profit: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    profit: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    total_assets: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    equity: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    liabilities: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    eps: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    bps: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    dividend: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))

    def __repr__(self) -> str:
        return (
            f"FinancialStatement(code={self.code!r}, "
            f"fiscal_period={self.fiscal_period!r}, "
            f"disclosed_date={self.disclosed_date!r})"
        )


class FinancialMetric(Base):
    """財務諸表と株価から計算した決算期ごとの財務指標。"""

    __tablename__ = "financial_metrics"
    __table_args__ = (
        ForeignKeyConstraint(
            ["code", "fiscal_period", "disclosed_date"],
            [
                "financial_statements.code",
                "financial_statements.fiscal_period",
                "financial_statements.disclosed_date",
            ],
        ),
    )

    code: Mapped[str] = mapped_column(String(5), primary_key=True)
    fiscal_period: Mapped[str] = mapped_column(String(50), primary_key=True)
    disclosed_date: Mapped[date] = mapped_column(
        Date,
        primary_key=True,
        index=True,
    )
    fiscal_year_end: Mapped[date | None] = mapped_column(Date, index=True)
    price_date: Mapped[date | None] = mapped_column(Date)

    equity_ratio: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))
    roe: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))
    roa: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))
    roi: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))
    operating_margin: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))
    per: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    pbr: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    dividend_yield: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))

    def __repr__(self) -> str:
        return (
            f"FinancialMetric(code={self.code!r}, "
            f"fiscal_period={self.fiscal_period!r}, "
            f"disclosed_date={self.disclosed_date!r})"
        )
