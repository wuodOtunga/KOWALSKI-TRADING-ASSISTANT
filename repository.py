from __future__ import annotations

from collections.abc import Generator, Iterable, Mapping
from contextlib import contextmanager
from dataclasses import fields
from pathlib import Path
from typing import Any, TypeVar, get_args

from sqlalchemy import Engine, create_engine, delete, event, exc, exists, func, select
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import exceptions as t
import seed_data
from database_models import (
    AccountsModel,
    Base,
    ChartsModel,
    EntryExecutionModel,
    Models,
    ParametersModel,
    TradeAmendmentsModel,
    TradeManagement,
    TradeModel,
    TradeNotesModel,
    TradeParametersModel,
)
from models import (
    Account,
    AmendableColumns,
    Amendments,
    Trade,
    TradeChart,
    TradeGrade,
    TradeNotes,
)

_DB_PATH: Path = Path(__file__).resolve().parent / "kowalski.db"
SQLALCHEMY_DATABASE_URL: URL = URL.create(drivername="sqlite", database=str(object=_DB_PATH))

T = TypeVar("T")

# I am providing the column names for the seed data for the static database tables.
# the seed data is inside seed_data.py as a list of tuples.
# in the previous implementation for the Database() class, the seed data could be passed in as
# positional arguments/tuples. SQLAlchemy constructors requires keyword arguments for the INSERTS to work.
# the list of tuples will be turned into a list of dictionaries: list[dict[str, Any]]
# then the column names set below are used as column names inside _seeding_if_empty()
_MODELS_COLUMNS = ("model_name", "description")
_TRADE_MANAGEMENT_COLUMNS = ("archetype", "description", "points", "grade")
_ENTRY_EXECUTION_COLUMNS = ("archetype", "description", "points", "grade")
_PARAMETERS_COLUMNS = ("parameter_name",)

# -------------------------------------------------------------------------
#   ENGINE CONSTRUCTION
# -------------------------------------------------------------------------
def _enable_sqlite_foreign_keys(db_connection: Any, _connection_record: Any = None) -> None:
    """SET PRAGMA FOR THE FOREIGN KEYS"""
    """sqlite ignores FK constraints unless the PRAGMA is set
    this needs to be set on all new connections created. SQLAlchemy doesn't set it"""

    cursor = db_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

def create_database_engine(url: str | URL = SQLALCHEMY_DATABASE_URL, *, echo: bool = True) -> Engine:
    """CREATE THE DATABASE ENGINE WITH SQLITE SPECIFIC CONFIGURATIONS"""

    url = make_url(name_or_url=url)
    kwargs: dict[str, Any] = {"echo": echo}

    if url.get_backend_name() == "sqlite":
        kwargs["connect_args"] = {"check_same_thread": False}

    if url.database in (None, "", ":memory:"):
        kwargs["poolclass"] = StaticPool

    engine: Engine = create_engine(url, **kwargs)

    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)

    return engine

# --------------------------------------------------------------------------
# SMALL PURE PRIVATE HELPERS WITH NO DATABASE ACCESS
# --------------------------------------------------------------------------
def _to_domain(cls: type[T], row: Any) -> T:
    """MAPS THE ORM ROW OBJECTS TO DOMAIN DATACLASS OBJECTS"""

    return cls(**{f.name: getattr(row, f.name) for f in fields(class_or_instance=cls)})  # type: ignore

def _field_values(obj: Any, exclude: Iterable[str] = ()) -> dict[str, Any]:
    """DATACLASS TO KWARGS DICTS FOR ORM CONSTRUCTOR"""
    """function offers an alternative to the manual construction
    of the orm database objects from our dataclass domain objects"""

    # set() will build an unordered collection of unique elements.
    # set() requires an Iterable as an argument and so we import Iterable from collections.abc
    # exclude will mostly contain the primary keys like trade_id that aren't user populated but
    # rather are the unique IDs populated by the repository for every database insert.
    # a bare string would be split into characters by set(), so normalise it first
    skip = {exclude} if isinstance(exclude, str) else set(exclude)
    return {f.name: getattr(obj, f.name) for f in fields(obj) if f.name not in skip}


def _named(columns: tuple[str, ...], rows: Iterable) -> list[dict[str, Any]]:
    """SETTING COLUMN NAMES FOR THE POSITIONAL LIST OF TUPLES HOLDING SEEDING DATA"""

    return [
        dict(
            zip(columns, row if isinstance(row, (list, tuple)) else (row,), strict=True)
        )
        for row in rows
    ]

def _db_message(error: exc.SQLAlchemyError) -> str:
    """PROVIDES THE ERROR NAME FOR THE EXCEPTION THAT OCCURRED"""
    """e.orig allows us to identify the specific exception that fired instead
    of all the errors having a generic name. We need the specific name to tailor our
    domain error messages and to return accurate FastAPI status codes responses"""

    return str(object=getattr(error, "orig", None) or error)

# --------------------------------------------------------------------------
#   PRIVATE HELPERS FOR COMMON QUERIES SHARED ACROSS DIFFERENT METHODS
# --------------------------------------------------------------------------
def _get_trade_row(trade_id: int, session: Session) -> TradeModel:
    """LOAD A TRADE USING THE TRADE_ID PRIMARY KEY"""

    # session.get() is the idiomatic approach for PK queries.
    # it consults the identity map before hitting the database.
    row = session.get(TradeModel, trade_id)
    if row is None:
        raise t.TradeNotFoundError("INVALID TRADE_ID. NO TRADE FOUND!")

    return row

def _get_notes_row(trade_id: int, session: Session) -> TradeNotesModel:
    """LOADS TRADE NOTES ATTACHED TO A TRADE GIVEN A VALID TRADE_ID"""
    """the trade_id validity checks via _ensure_trade_exists() has been handled by the caller"""

    row = session.get(TradeNotesModel, trade_id)
    if row is None:
        raise t.NotesNotFoundError("NO AVAILABLE NOTES FOR THIS TRADE")

    return row

def _ensure_trade_exists(trade_id: int, session: Session) -> None:
    """VALIDATES THAT THE TRADE_ID EXISTS"""
    """cheap existence check to avoid foreign key constraint violations"""

    # the existence check helps turn an esoteric exc.IntegrityError to a domain TradeNotFoundError
    # notice how I am using exists() instead of get().
    # we aren't loading the trade row only to confirm if the trade exists, so exists() is more efficient.

    if not session.scalar(
        select(exists(TradeModel).where(TradeModel.trade_id == trade_id))
    ):
        raise t.TradeNotFoundError("INVALID TRADE_ID. NO TRADE FOUND!")

def _check_foreign_keys(trade: Trade, session: Session) -> None:
    """CHECKS THAT THE FOREIGN KEYS ATTACHED TO A TRADE EXIST AND ARE VALID"""
    """cheap existence check to avoid foreign key constraint violations"""
    # TradeModel trades tables has 4 foreign keys.
    # models, accounts, trade_management, entry_execution.
    # During INSERTs into trades table, you need to check for validity of these FKs.
    # This rules out Foreign Key constraint violation error from the onset.

    # using exists() is more efficient than select() since we are doing existence checks.
    # we don't want to load an entire row just to check if the FK exists and is valid.
    found = session.execute(
        select(
            exists(Models).where(Models.model_id == trade.model_id),
            exists(AccountsModel).where(AccountsModel.account_id == trade.account_id),
            exists(TradeManagement).where(
                TradeManagement.management_id == trade.management_id
            ),
            exists(EntryExecutionModel).where(
                EntryExecutionModel.entry_execution_id == trade.entry_execution_id
            ),
        )
    ).one()  # ONE ROW, FOUR BOOLEAN COLUMNS. ITERATING THE RESULT YIELDS ROWS, NOT COLUMNS.

    names = ("model_id", "account_id", "management_id", "entry_execution_id")

    missing = []
    for name, ok in zip(names, found, strict=True):
        if not ok:
            missing.append(f"{name}= {getattr(trade, name)}")

    if missing:
        raise t.InvalidIdentifierError(
            f"FOLLOWING FKs ARE MISSING: {','.join(missing)}"
        )

def _seed_if_empty(session: Session, db_model: type[Any], rows: Iterable[Mapping[str, Any]]) -> None:
    """IDEMPOTENT SEEDING OF THE TABLES ONLY IF TABLE IS COMPLETELY EMPTY!"""

    # db_model(**row) is equivalent to: say db_model == Models,
    # model_one = Models(model_name=2022 fvg, description=description wording)
    # for row in rows runs the loop for the number of rows in the list, each loop creates one db_model
    # each db_model is a row in the database.
    if (session.scalars(select(db_model)).first() is None):  # checks if table rows are populated.
        session.add_all(db_model(**row) for row in rows)


class Repository:
    """REPOSITORY ACCESS FOR TRADES, NOTES, CHARTS AND AMENDMENTS"""

    def __init__(
        self, db_url: str | URL = SQLALCHEMY_DATABASE_URL, *, echo: bool = True
    ):

        self.engine = create_database_engine(url=db_url, echo=echo)
        self.SessionFactory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.initialize_database()

    def initialize_database(self) -> None:
        """CREATES ALL TABLES AND ENSURES INDEMPOTENT SEEDING OF STATIC TABLES"""
        """four tables contain static data that isn't user provided but is critical
        to the journaling workflow of the trader. The tables are seeded once at app startup"""

        Base.metadata.create_all(bind=self.engine)

        with self._transaction() as session:
            _seed_if_empty(session, db_model=Models, rows=_named(columns=_MODELS_COLUMNS, rows=seed_data.models))
            _seed_if_empty(
                session,
                EntryExecutionModel,
                _named(_ENTRY_EXECUTION_COLUMNS, seed_data.entry_execution),
            )
            _seed_if_empty(
                session,
                ParametersModel,
                _named(_PARAMETERS_COLUMNS, seed_data.parameter_values),
            )
            _seed_if_empty(
                session,
                TradeManagement,
                _named(_TRADE_MANAGEMENT_COLUMNS, seed_data.trade_management),
            )

    def close_db_connection(self):
        "Dispose the connection pool used by this _engine.Engine instance"
        self.engine.dispose()

    @contextmanager
    def _transaction(self) -> Generator[Session]:
        """OPEN A SESSION, COMMIT ON SUCCESS, ROLL BACK ON ANY EXCEPTION, ALWAYS CLOSE."""

        """This is also the ONLY place SQLAlchemy exceptions are translated, so no
        method needs its own try/except, and commit-time failures (which a
        try/except around flush() would miss) are covered too.
        Order matters: IntegrityError is a subclass of SQLAlchemyError, so it
        must be caught first. Our own domain exceptions are not SQLAlchemy
        errors; they pass straight through after the automatic rollback.
        """

        try:
            with self.SessionFactory.begin() as session:
                yield session
        except exc.IntegrityError as e:
            raise t.ConstraintViolationError(f"CONSTRAINT VIOLATION: {_db_message(e)}") from e
        except exc.SQLAlchemyError as e:
            raise t.DatabaseError(f"DATABASE ERROR: {_db_message(e)}") from e

    # TRADE DOMAIN MODEL DATABASE METHODS; CRUd
    def save_trade(self, trade: Trade) -> int:
        """PERSIST A TRADE TO THE REPOSITORY"""

        # Check for validity of foreign keys and raise exception loudly
        # before doing anything else.
        row = TradeModel(**_field_values(trade, exclude="trade_id"))

        with self._transaction() as session:
            _check_foreign_keys(trade, session)
            session.add(row)
            session.flush()

            return row.trade_id

    def get_by_id(self, trade_id: int) -> Trade:
        """RETRIEVE A TRADE FROM THE REPOSITORY"""

        with self._transaction() as session:
            return _to_domain(Trade, _get_trade_row(trade_id, session))

    def get_all_trades(self) -> list[Trade]:
        """RETRIEVES ALL TRADES FROM THE REPOSITORY"""

        with self._transaction() as session:
            rows = list(session.execute(select(TradeModel)).scalars().all())
            return [_to_domain(Trade, row) for row in rows]

    def update_trade_grade(self, trade_id: int, new_grade: TradeGrade) -> None:
        """UPDATES TRADE.OVERALL_TRADE_GRADE IN THE REPOSITORY"""
        """updating trade.overall_trade_grade happens often enough that it deserves it's own method"""

        if not isinstance(new_grade, TradeGrade):
            raise t.InvalidGradeError("GRADE NEEDS TO BE OF TYPE TRADEGRADE.")

        with self._transaction() as session:
            _ensure_trade_exists(trade_id, session)
            _get_trade_row(trade_id, session).overall_trade_grade = new_grade

    def update_trade_field(self, trade_id: int, new_value: Any, column: AmendableColumns) -> None:
        """UPDATES A DYNAMIC TRADE COLUMN BASED ON TRADER PREFERENCE"""

        if column not in get_args(AmendableColumns):
            raise t.InvalidColumnNameError("CAN'T UPDATE INVALID COLUMN")

        # use setattr() to dynamically update the trade column with the new_value
        with self._transaction() as session:
            _ensure_trade_exists(trade_id, session)
            setattr(_get_trade_row(trade_id, session), column, new_value)

    def delete_trade(self, trade_id: int) -> None:
        """DELETES A TRADE ROW FROM THE REPOSITORY"""
        """deleting a trade also cascade deletes the children attached to a trade
        these include notes, charts and parameters linked to the trade
        trade amendments linked to the trade don't get deleted as a policy decision
        that audit trails for amendments are vital information that persists even for deleted trades"""

        with self._transaction() as session:
            _ensure_trade_exists(trade_id, session)
            session.delete(_get_trade_row(trade_id, session))

#----------TRADE NOTES DOMAIN MODEL DATABASE METHODS; CRUD---------------------------
    def add_trade_notes(self, notes: TradeNotes) -> None:
        """PERSISTS TRADE NOTES TO THE REPOSITORY"""

        with self._transaction() as session:
            _ensure_trade_exists(notes.trade_id, session) # type: ignore
            session.add(TradeNotesModel(**_field_values(notes)))
            session.flush()

    def get_trade_notes(self, trade_id: int) -> TradeNotes:
        """RETRIEVE TRADE NOTES FROM THE REPOSITORY"""

        with self._transaction() as session:
            _ensure_trade_exists(trade_id, session)
            return _to_domain(TradeNotes, _get_notes_row(trade_id, session))

    def update_trading_notes(self, new_notes: TradeNotes) -> None:
        """UPSERTS FULL ROW ON TRADE NOTES DATABASE TABLE"""
        """inserts the trade notes if they don't already exists or
        updates the trade notes if they do exist. This mirrors PUT semantics.
        an upsert makes the method idempotent. making calls, same database state"""

        with self._transaction() as session:
            _ensure_trade_exists(new_notes.trade_id, session) # type: ignore

            row = session.get(TradeNotesModel, new_notes.trade_id)
            if row is None:
                session.add(TradeNotesModel(**_field_values(new_notes)))
            else:
                for name, value in _field_values(new_notes, exclude="trade_id").items():
                    setattr(row, name, value)

#------------TRADE PARAMETERS DOMAIN MODEL DATABASE METHODS; JUNCTION TABLE--------------------------------
    def add_trade_parameters(self, trade_id: int, parameter_id: int) -> None:
        """PERSIST THE TRADE PARAMETERS TO THE JUNCTION TABLE"""

        # trade_parameters junction table dual primary key is an explicit imperative
        # domain invariant hence this is the Constraint Violation Error we watching for.
        # THE (TRADE_ID, PARAMETER_ID) PAIR MUST BE UNIQUE!
        # So explicitly check for validity of trade_id to rule out foreign key constraint violation.

        with self._transaction() as session:
            # validity check for trade_id FK
            _ensure_trade_exists(trade_id, session)

            # validity check for parameter_id FK
            if session.get(ParametersModel, parameter_id) is None:
                raise t.InvalidIdentifierError("INVALID PARAMETER ID. PARAMETER NOT FOUND")

            # at this point, both FKs have been checked, so we rule out Foreign key constraint violation.
            # we have no dataclass for trade parameters, so we can't use _field_values() only manual construction
            session.add(
                TradeParametersModel(trade_id=trade_id, parameter_id=parameter_id)
            )

    def get_trade_parameters(self, trade_id: int) -> list[int]:
        """RETRIEVE THE TRADE PARAMETERS FROM THE JUNCTION TABLE"""

        with self._transaction() as session:
            _ensure_trade_exists(trade_id, session)

            return list(
                session.scalars(
                    select(TradeParametersModel.parameter_id)
                    .where(TradeParametersModel.trade_id == trade_id)
                    .order_by(TradeParametersModel.parameter_id)
                )
            )

#---------TRADING ACCOUNTS DOMAIN MODEL DATABASE METHODS; CRUD------------------------------
    def create_trading_account(self, account: Account) -> int:
        """PERSIST A NEW TRADING ACCOUNT TO THE REPOSITORY"""

        row = AccountsModel(**_field_values(account, exclude="account_id"))
        with self._transaction() as session:
            session.add(row)
            session.flush()
            return row.account_id

    def get_trading_accounts(self) -> list[Account]:
        """RETRIEVE ALL AVAILABLE ACCOUNTS FROM THE REPOSITORY"""
        """an empty accounts table returns an empty list"""

        # orm_queryguide_select_orm_entities - contrasts the behavior of _orm.Session.execute to _orm.Session.scalars
        with self._transaction() as session:
            accounts = list(
                session.scalars(
                    select(AccountsModel).order_by(AccountsModel.account_id)
                )
            )

            return [_to_domain(Account, account) for account in accounts]

    def get_current_account_balance(self, account_id: int) -> float:
        """CALCULATES THE ACCOUNT BALANCE OF AN ACCOUNT GIVEN AN EXISTING ACCOUNT_ID"""
        """account_balance is stored in the repository because it's a derived value that
        also depends on other column values. Storing account_balance causes issues like stale data
        in the database when we have amendments to the trades table that also affect account_balance
        calculating the value on demand side steps these staleness issues"""

        with self._transaction() as session:
            starting_balance = session.scalar(
                select(AccountsModel.starting_balance).where(
                    AccountsModel.account_id == account_id
                )
            )

            if starting_balance is None:
                raise t.InvalidAccountError("INVALID ACCOUNT ID. NO ACCOUNT FOUND")

            pnl = session.scalar(
                select(func.coalesce(func.sum(TradeModel.dollar_amount), 0)).where(
                    TradeModel.account_id == account_id
                )
            )

            return float(starting_balance + pnl)  # type: ignore

    def delete_account_from_db(self, account_id: int) -> None:
        """DELETE ACCOUNT DETAILS FROM THE ACCOUNTS TABLE"""
        """accounts that have trades can't be deleted because the account_id
        is a FK on the trades table and pragma FKs is on so account deletion
        cause a constraint violation error, so we deactivate the account instead"""

        with self._transaction() as session:
            if session.get(AccountsModel, account_id) is None:
                raise t.InvalidAccountError("INVALID ACCOUNT_ID. ACCOUNT NOT FOUND")

            trade_count = session.scalar(
                select(func.count())
                .select_from(TradeModel)
                .where(TradeModel.account_id == account_id)
            )
            if trade_count:
                raise t.ConstraintViolationError(
                    "THE ACCOUNT HAS TRADES ATTACHED. DEACTIVATE ACCOUNT INSTEAD"
                )
            session.execute(
                delete(AccountsModel).where(AccountsModel.account_id == account_id)
            )

#---------TRADING CHARTS DOMAIN MODEL DATABASE METHODS; CRUD-------------------------
    def add_chart(self, charts: TradeChart) -> int:
        """ATTACH CHARTS TO A TRADE IN THE REPOSITORY"""

        row = ChartsModel(**_field_values(charts, exclude="chart_id"))
        with self._transaction() as session:
            _ensure_trade_exists(charts.trade_id, session)

            session.add(row)
            session.flush()

            return row.chart_id

    def get_trade_charts(self, trade_id: int) -> list[TradeChart]:
        """RETRIEVE A LIST OF CHARTS ATTACHED TO A TRADE"""
        """for a trade that doesn't have any charts attached to it, return an empty list"""

        with self._transaction() as session:
            _ensure_trade_exists(trade_id, session)
            rows = session.scalars(
                select(ChartsModel)
                .where(ChartsModel.trade_id == trade_id)
                .order_by(ChartsModel.chart_id)
            )

            return [_to_domain(TradeChart, row) for row in rows]

#-------TRADING AMENDMENTS DOMAIN MODEL DATABASE METHODS; CRUD------------------

    def add_trade_amendments(self, amendment: Amendments) -> int:
        """RECORDS AN AUDIT TRAIL OF ALL THE TRADE CHANGES SUBMITTED"""
        """deleting a trade doesn't cascade delete the amendments attached to the trade"""

        row = TradeAmendmentsModel(**_field_values(amendment, exclude="amendment_id"))
        with self._transaction() as session:
            _ensure_trade_exists(amendment.trade_id, session)
            session.add(row)
            session.flush()

            return row.amendment_id

#---- STATIC LOOK UP TABLES DATABASE READ METHODS; GETTER METHODS-----
#-----STATIC TABLES: MODELS, TRADE_MANAGEMENT, PARAMETERS, ENTRY_EXECUTION------

    def get_parameter_ids(self, parameter_names: list) -> list[int]:
        """RETRIEVE THE PARAMETER_ID CORRESPONDING TO A PARAMETER_NAME"""

        # We have a list of parameter_names that we want to get the
        # corresponding id for each parameter from the parameters table.
        # We can't assign ids using indices from enumerate() because the
        # specific parameter_id assigned in the parameters table has domain significance.

        parameter_ids = []

        with self._transaction() as session:
            for parameter in parameter_names:
                parameter_id = session.execute(
                    select(ParametersModel.parameter_id).where(
                        ParametersModel.parameter_name == parameter
                    )
                ).scalar_one_or_none()

                # We shouldn't be getting None as a value after the query but if
                # parameter_names list somehow has an invalid parameter name, then raise exception.
                # I thought about using scalar_one() to enforce the domain invariant but I don't want
                # a non-domain exception firing and leaking out into the higher level modules like journal.py.
                if not parameter_id:
                    raise t.InvalidIdentifierError(
                        "INVALID PARAMETER NAME. CHECK INPUTS"
                    )

                parameter_ids.append(parameter_id)

            return parameter_ids

    def get_parameter_names(self, parameter_ids: list) -> list[int]:
        """RETRIEVE THE PARAMETER_NAME CORRESPONDING TO A PARAMETER_ID"""

        # We have a list of IDs for the parameters present for a trade fetched from the
        # trade_parameters junction table which stores (trade_id, parameter_id) pairs.
        # We need to show the trader which parameters were present for the trade but a parameter_id
        # doesn't offer any informational value to the trader. We need the actual parameter names so we query.

        parameter_names = []

        with self._transaction() as session:
            for parameter_id in parameter_ids:
                parameter_name = session.execute(
                    select(ParametersModel.parameter_name).where(
                        ParametersModel.parameter_id == parameter_id
                    )
                ).scalar_one_or_none()

                # We shouldn't be getting None as a value after the query but if
                # parameter_ids list somehow has an invalid parameter_id, then raise exception.
                if not parameter_name:
                    raise t.InvalidIdentifierError("INVALID PARAMETER ID. CHECK INPUTS")

                parameter_names.append(parameter_name)

            return parameter_names

    def get_entry_execution_points(self, entry_execution_id: int) -> int:
        """RETRIEVE THE POINTS CORRESPONDING TO AN ENTRY EXECUTION ARCHETYPE"""
        """entry_execution points is used in the grading logic of individual trades"""

        with self._transaction() as session:
            points = session.execute(
                select(EntryExecutionModel.points).where(
                    EntryExecutionModel.entry_execution_id == entry_execution_id
                )
            ).scalar_one_or_none()

            if not points:
                raise t.InvalidIdentifierError(
                    "INVALID ENTRY EXECUTION ID. CHECK INPUTS"
                )

            return points

    def get_trade_management_points(self, management_id: int) -> int:
        """RETRIEVE THE POINTS CORRESPONDING TO A TRADE MANAGEMENT ARCHETYPE"""
        """trade_management points is used in the grading logic of individual trades"""

        with self._transaction() as session:
            points = session.execute(
                select(TradeManagement.points).where(
                    TradeManagement.management_id == management_id
                )
            ).scalar_one_or_none()

            if not points:
                raise t.InvalidIdentifierError(
                    "INVALID TRADE MANAGEMENT ID. CHECK INPUTS"
                )

            return points

    def get_models_list(self):
        pass

    def get_entry_executions_list(self):
        pass

    def get_trade_managements_list(self):
        pass

    def get_parameters_list(self):
        pass

#-------REPORTS/STATISTICS/ANALYTICS AGGREGATION DATABASE METHODS FOR REPORTS.PY-------

    def get_global_stats_rows(self):
        # NOT BEING IMPLEMENTED RIGHT NOW TILL WE SET UP REPORTS.PY
        pass


