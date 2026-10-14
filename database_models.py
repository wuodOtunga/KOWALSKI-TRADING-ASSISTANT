"""A MODULE FOR SQLALCHEMY CLASSES THAT DEFINE WHAT WE STORE IN THE KOWALSKI.DB DATABASE"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Interval,
    Text,
    Time,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from models import TradeAsset, TradeDirection, TradeGrade, TradeResult
from schemas import AmendableColumns


class Base(DeclarativeBase):
    pass


# THE SIDE WITH THE FK COLUMN IS THE CHILD CLASS (MANY SIDE)
# THE SIDE THAT IS REFERENCED BY THE FK IS THE PARENT (ONE SIDE)
# BACK_POPULATES VALUE IS ALWAYS THE NAME OF THE ATTRIBUTE ON THE OTHER CLASS


class TradeModel(Base):
    __tablename__ = "trades"

    trade_id: Mapped[int] = mapped_column(primary_key=True)
    entry_price: Mapped[float] = mapped_column(nullable=False)
    exit_price: Mapped[float] = mapped_column(nullable=False)
    take_profit: Mapped[float] = mapped_column(nullable=False)
    stop_loss: Mapped[float] = mapped_column(nullable=False)
    position_size: Mapped[float] = mapped_column(nullable=False)
    #FIX: WILL RAISE AN ERROR ON READ DUE TO STORED FORMAT
    entry_time: Mapped[time] = mapped_column(Time, nullable=False)
    #FIX: WILL RAISE AN ERROR ON READ DUE TO STORED FORMAT
    exit_time: Mapped[time] = mapped_column(Time, nullable=False)
    #FIX: WILL RAISE AN ERROR ON READ DUE TO STORED FORMAT
    date: Mapped[date] = mapped_column(Date, nullable=False)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.model_id"), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.account_id"), nullable=False)
    management_id: Mapped[int] = mapped_column(
        ForeignKey("trade_management.management_id"), nullable=False
    )
    entry_execution_id: Mapped[int] = mapped_column(
        ForeignKey("entry_execution.entry_execution_id"), nullable=False
    )
    asset: Mapped[TradeAsset] = mapped_column(
        Enum(
            TradeAsset,
            values_callable=lambda x: [i.value for i in x],
            native_enum=False,
            check_constraint=True,
            name="ck_trades_asset",
        ),
        nullable=False,
    )
    direction: Mapped[TradeDirection] = mapped_column(
        Enum(
            TradeDirection,
            values_callable=lambda e: [m.value for m in e],
            native_enum=False,
            check_constraint=True,
            name="ck_trades_direction",
        ),
        nullable=False,
    )
    dollar_amount: Mapped[float | None]
    duration: Mapped[timedelta | None] = mapped_column(Interval)
    result: Mapped[TradeResult | None] = mapped_column(
        Enum(
            TradeResult,
            values_callable=lambda r: [i.value for i in r],
            native_enum=False,
            check_constraint=True,
            name="ck_trades_result",
        )
    )
    rr_multiple: Mapped[float | None]
    risk_percent: Mapped[float | None]
    overall_trade_grade: Mapped[TradeGrade | None] = mapped_column(
        Enum(
            TradeGrade,
            values_callable=lambda g: [t.value for t in g],
            native_enum=False,
            check_constraint=True,
            name="ck_trades_grade",
        )
    )

    model: Mapped[Models] = relationship(back_populates="trades")
    account: Mapped[AccountsModel] = relationship(back_populates="trades")
    management: Mapped[TradeManagementModel] = relationship(back_populates="trades")
    execution: Mapped[EntryExecutionModel] = relationship(back_populates="trades")

    notes: Mapped[TradeNotesModel] = relationship(back_populates="trade", cascade="all, delete-orphan")
    charts: Mapped[list[ChartsModel]] = relationship(back_populates="trade", cascade="all, delete-orphan")
    amendment: Mapped[list[TradeAmendmentsModel]] = relationship(back_populates="trade")
    parameters: Mapped[list[ParametersModel]] = relationship(
        secondary="trade_parameters", back_populates="trades"
    )


class Models(Base):
    __tablename__ = "models"

    model_id: Mapped[int] = mapped_column(primary_key=True)
    model_name: Mapped[str] = mapped_column(nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    trades: Mapped[list[TradeModel]] = relationship(back_populates="model")

    def __repr__(self) -> str:
        return f"Models(model_id={self.model_id!r}, model_name={self.model_name!r}, description={self.description!r})"  # noqa: E501


class EntryExecutionModel(Base):
    __tablename__ = "entry_execution"

    entry_execution_id: Mapped[int] = mapped_column(primary_key=True)
    archetype: Mapped[str] = mapped_column(nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    points: Mapped[int] = mapped_column(nullable=False)
    grade: Mapped[str] = mapped_column(nullable=False)

    trades: Mapped[list[TradeModel]] = relationship(back_populates="execution")

    __table_args__ = (
        CheckConstraint("points BETWEEN 1 AND 5", name="ck_entry_execution_points"),
        CheckConstraint(
            "grade IN ('A+', 'B', 'C', 'D', 'F')", name="ck_entry_execution_grade"
        ),
    )


class TradeManagementModel(Base):
    __tablename__ = "trade_management"

    management_id: Mapped[int] = mapped_column(primary_key=True)
    archetype: Mapped[str] = mapped_column(nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    points: Mapped[int] = mapped_column(nullable=False)
    grade: Mapped[str] = mapped_column(nullable=False)

    trades: Mapped[list[TradeModel]] = relationship(back_populates="management")

    __table_args__ = (
        CheckConstraint("points BETWEEN 1 AND 5", name="ck_trade_management_points"),
        CheckConstraint(
            "grade IN ('A+', 'B', 'C', 'D', 'F')", name="ck_trade_management_grade"
        ),
    )


class AccountsModel(Base):
    __tablename__ = "accounts"

    account_id: Mapped[int] = mapped_column(primary_key=True)
    account_name: Mapped[str] = mapped_column(nullable=False)
    account_type: Mapped[str] = mapped_column(nullable=False)
    broker: Mapped[str] = mapped_column(nullable=False)
    starting_balance: Mapped[float] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    trades: Mapped[list[TradeModel]] = relationship(back_populates="account")

    __table_args__ = (
        CheckConstraint(
            "account_type IN ('FUNDED CHALLENGE', 'FUNDED LIVE', 'PERSONAL LIVE')",
            name="ck_accounts_type",
        ),
    )


class ParametersModel(Base):
    __tablename__ = "parameters"

    parameter_id: Mapped[int] = mapped_column(primary_key=True)
    parameter_name: Mapped[str] = mapped_column(nullable=False, unique=True)

    trades: Mapped[list[TradeModel]] = relationship(
        secondary="trade_parameters", back_populates="parameters"
    )


class TradeParametersModel(Base):
    __tablename__ = "trade_parameters"

    trade_id: Mapped[int] = mapped_column(
        ForeignKey("trades.trade_id"), primary_key=True
    )
    parameter_id: Mapped[int] = mapped_column(
        ForeignKey("parameters.parameter_id"), primary_key=True
    )


class TradeNotesModel(Base):
    __tablename__ = "trade_notes"

    trade_id: Mapped[int] = mapped_column(
        ForeignKey("trades.trade_id"), primary_key=True
    )
    emotions: Mapped[str] = mapped_column(Text, nullable=False)
    mistakes: Mapped[str] = mapped_column(Text, nullable=False)
    lessons: Mapped[str] = mapped_column(Text, nullable=False)
    general_notes: Mapped[str] = mapped_column(Text, nullable=False)

    trade: Mapped[TradeModel] = relationship(back_populates="notes")


class ChartsModel(Base):
    __tablename__ = "charts"

    chart_id: Mapped[int] = mapped_column(primary_key=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.trade_id"))
    filepath: Mapped[str] = mapped_column(nullable=False, unique=True)
    filename: Mapped[str] = mapped_column(nullable=False, unique=True)
    upload_date: Mapped[datetime | None] = mapped_column(DateTime)

    trade: Mapped[TradeModel] = relationship(back_populates="charts")


class TradeAmendmentsModel(Base):
    __tablename__ = "trade_amendments"

    amendment_id: Mapped[int] = mapped_column(primary_key=True)
    #DECIDE IF YOU WANT TRADE_ID TO BE A FK ON THIS TABLE.
    #IF AUDITS ARE TO PERSIST AFTER A TRADE IS DELETED THEN YOU MUST DROP
    #THE TRADE_ID FOREIGN KEY. DEBATE LATER.
    trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.trade_id"))
    column_name: Mapped[AmendableColumns] = mapped_column(nullable=False)
    old_value: Mapped[str] = mapped_column(Text, nullable=False)
    new_value: Mapped[str] = mapped_column(Text, nullable=False)
    amended_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    trade: Mapped[TradeModel] = relationship(back_populates="amendment")
