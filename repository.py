from __future__ import annotations

from collections.abc import Generator, Iterable, Mapping
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import fields
from datetime import date, time
from pathlib import Path
from typing import Any, TypeVar, get_args

from sqlalchemy import (
    Engine,
    Row,
    ScalarResult,
    and_,
    create_engine,
    delete,
    event,
    exc,
    exists,
    func,
    or_,
    select,
)
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
    TradeManagementModel,
    TradeModel,
    TradeNotesModel,
    TradeParametersModel,
)
from models import (
    Account,
    AmendableColumns,
    Amendments,
    EntryExecution,
    Parameter,
    Trade,
    TradeChart,
    TradeGrade,
    TradeManagement,
    TradeNotes,
    TradingModel,
)

_DB_PATH: Path = Path(__file__).resolve().parent / "kowalski.db"
SQLALCHEMY_DATABASE_URL: URL = URL.create(drivername="sqlite", database=str(object=_DB_PATH))

T = TypeVar("T")

_DERIVED_FIELDS = ("dollar_amount", "result", "rr_multiple", "risk_percent", "duration")

_WRITABLE_TRADE_COLUMNS = frozenset(get_args(AmendableColumns)) | set(_DERIVED_FIELDS) | {"overall_trade_grade"}

#ContextVar for context variables.
#Think of it as a variable whose value depends on who is asking.
#For the app, one requests chain router → services → journal → repository runs in a single worker thread.
#So when Journal calls self.db.transaction() and sets the variable,
#every repository method deeper in that chain reads the same session.
#A different request in another thread reads its own value.
#The variable gives you a “current transaction” that doesnt have to be passed as an argument.

#ADDITIONAL INFO: PROCESS VERSUS THREAD.
#A process is a running program with its own private memory. Two processes cant see each others variable.
#If they need to share data, they go through a file, a socket, or a database.
#A thread is a separate line of execution inside one process.
#Threads share the same memory, so they can all see the same variables, objects, and connections.
#That’s useful, but it’s also the source of the danger.     # noqa: RUF003
#Analogy: a process is a separate kitchen with its own pantry.
#Threads are several cooks in one kitchen sharing the same pantry.
#Cooks work faster together, but two cooks grabbing the same bowl at once is a problem.

#Module level context variable that holds the session of the transaction currently open in this context.
_active_session: ContextVar[Session | None] = ContextVar("active_session", default=None)

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
_ACCOUNTS_COLUMNS = ("account_name", "account_type", "broker", "starting_balance", "is_active")

_SQLITE_CONSTRAINTS = {
    "SQLITE_CONSTRAINT_FOREIGNKEY": t.ForeignKeyViolationError,
    "SQLITE_CONSTRAINT_UNIQUE":     t.UniqueViolationError,
    "SQLITE_CONSTRAINT_PRIMARYKEY": t.UniqueViolationError,
    "SQLITE_CONSTRAINT_CHECK":      t.CheckViolationError,
    "SQLITE_CONSTRAINT_NOTNULL":    t.NotNullViolationError,
}

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

def create_database_engine(url: str | URL = SQLALCHEMY_DATABASE_URL, *, echo: bool = False) -> Engine:
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
def _to_domain[T](cls: type[T], row: Any) -> T:
    """MAPS THE ORM ROW OBJECTS TO DOMAIN DATACLASS OBJECTS"""

    return cls(**{f.name: getattr(row, f.name) for f in fields(class_or_instance=cls)}) # pyright: ignore[reportArgumentType]

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
    return {f.name: getattr(obj, f.name) for f in fields(class_or_instance=obj) if f.name not in skip}


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

#When SQLite rejects an insert, three objects are involved:
#sqlite3.IntegrityError, the drivers original exception.
#sqlalchemy.exc.IntegrityError (your e), a wrapper SQLAlchemy puts around it.
# The original is available as e.orig.
#Your own t.ConstraintViolationError family, the domain exceptions.
#On Python 3.11+, e.orig carries two attributes you can see with plain sqlite3:
#sqlite_errorname: SQLITE_CONSTRAINT_UNIQUE, sqlite_errorcode: 2067
#when you print the error: print(err) ==> UNIQUE constraint failed: x.a
#The errorname is the machine-readable label you want to dispatch on.
#The message text is for humans and logs.
#The function reads the errorname from e.orig,
#uses it to pick the class, and returns an instance with the message
def _translate_integrity(e: exc.IntegrityError):
    """function reads the errorname from e.orig,
    uses it to pick the class, and returns an instance with the message"""

    error_name: str | None = getattr(e.orig, "sqlite_errorname", None)

    cls = _SQLITE_CONSTRAINTS.get(error_name, t.ConstraintViolationError) # pyright: ignore[reportCallIssue, reportArgumentType]

    return cls(f"CONSTRAINT VIOLATION: {_db_message(e)}")

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
    found: Row[tuple[bool, bool, bool, bool]] = session.execute(
        statement=select(
            exists(Models).where(Models.model_id == trade.model_id),
            exists(AccountsModel).where(AccountsModel.account_id == trade.account_id),
            exists(TradeManagementModel).where(
                TradeManagementModel.management_id == trade.management_id
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
    if session.scalars(select(db_model)).first() is None:  # checks if table rows are populated.
        session.add_all(db_model(**row) for row in rows)


class Repository:
    """REPOSITORY ACCESS FOR TRADES, NOTES, CHARTS AND AMENDMENTS"""

    def __init__(
        self, db_url: str | URL = SQLALCHEMY_DATABASE_URL, *, echo: bool = False
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
            _seed_if_empty(
                session=session,
                db_model=Models,
                rows=_named(columns=_MODELS_COLUMNS, rows=seed_data.models),
            )
            _seed_if_empty(
                session=session,
                db_model=AccountsModel,
                rows=_named(columns=_ACCOUNTS_COLUMNS, rows=seed_data.accounts),
            )
            _seed_if_empty(
                session,
                db_model=EntryExecutionModel,
                rows=_named(_ENTRY_EXECUTION_COLUMNS, seed_data.entry_execution),
            )
            _seed_if_empty(
                session,
                db_model=ParametersModel,
                rows=_named(_PARAMETERS_COLUMNS, seed_data.parameter_values),
            )
            _seed_if_empty(
                session,
                db_model=TradeManagementModel,
                rows=_named(_TRADE_MANAGEMENT_COLUMNS, seed_data.trade_management),
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
        #A with block needs an object with __enter__ and __exit__ methods.
        #@contextmanager lets you write one as a generator with a single yield
        #If the body raises, Python re-raises the exception at the yield line.
        #That is why a try/except wrapped around the yield can catch errors from the body.
        #The except clauses in _transaction() work this way:
        #they catch anything thrown inside the caller’s with block and translate it.  # noqa: RUF003
        #The rule is that the generator must yield exactly once. Every code path through it reaches one yield.

        #check whether a transaction is open.
        outer: Session | None = _active_session.get()

        try:
            if outer is not None:
                #if transaction is open, yield associated session
                #a transaction is already open, so hand the same session to the caller.
                yield outer
            else:
                #if no transaction is open, create a session.
                #Owner branch. Nothing is open, so create a session.
                #begin() is itself a context manager: it commits on clean exit and rolls back on exception.
                with self.SessionFactory.begin() as session:
            #Publish the session so nested calls can find it,
            #run the body, and always unpublish, even on exceptions.
            #set() returns a token that remembers the previous value, and reset(token) restores it.
            #Without the finally, a failed transaction would leave a dead session in the variable
            #and the next call would try to join it.
                    token: Token[Session | None] = _active_session.set(session)
                    try:
                        yield session
                    finally:
                        _active_session.reset(token)
        #The outer try/except translates SQLAlchemy errors into your domain exceptions, in both branches.
        except exc.IntegrityError as e:
            raise _translate_integrity(e) from e
        except exc.SQLAlchemyError as e:
            raise t.KowalskiError(f"DATABASE ERROR: {_db_message(e)}") from e

    def transaction(self):
        """PUBLIC INTERFACE FOR THE JOURNAL MODULE"""

        return self._transaction()

#----------------- TRADE DOMAIN MODEL DATABASE METHODS----------------------------
    def save_trade(self, trade: Trade) -> int:
        """PERSIST A TRADE TO THE REPOSITORY"""

        #UniqueConstraintViolation == trade_id
        #ForeignKeyViolation == model_id, account_id, management_id, entry_execution_id
        #CheckConstraintViolation == asset, direction, result, overall_trade_grade
        #NotNullViolation == All non-derived attributes
        #TradeValidationError == validation of attributes via validate_trade_data()
        row = TradeModel(**_field_values(obj=trade, exclude="trade_id"))

        with self._transaction() as session:
            _check_foreign_keys(trade, session)
            session.add(instance=row)
            session.flush()

            return row.trade_id

    def get_by_id(self, trade_id: int) -> Trade:
        """RETRIEVE A TRADE FROM THE REPOSITORY"""

        with self._transaction() as session:
            return _to_domain(Trade, _get_trade_row(trade_id, session))

    def get_all_trades(self) -> list[Trade]:
        """RETRIEVES ALL TRADES FROM THE REPOSITORY"""

        with self._transaction() as session:
            rows: list[TradeModel] = list(session.scalars(
                select(TradeModel).order_by(TradeModel.trade_id)
            ))
            return [_to_domain(Trade, row) for row in rows]

    def update_trade_grade(self, trade_id: int, new_grade: TradeGrade) -> None:
        """UPDATES TRADE.OVERALL_TRADE_GRADE IN THE REPOSITORY"""
        """updating trade.overall_trade_grade happens often enough that it deserves it's own method"""

        if not isinstance(new_grade, TradeGrade):
            raise t.GradingError(f"{new_grade} IS INVALID. GRADE MUST BE OF TYPE TRADE_GRADE")

        with self._transaction() as session:
            _ensure_trade_exists(trade_id, session)
            row: TradeModel = _get_trade_row(trade_id, session)
            row.overall_trade_grade = new_grade
            _check_foreign_keys(trade=_to_domain(cls=Trade, row=row), session=session)
            session.flush()

    def update_trade_fields(self, trade_id: int, changes: Mapping[str, Any]) -> None:
        """UPDATES SEVERAL TRADE COLUMNS IN ONE FLUSH"""
        unknown = set(changes) - _WRITABLE_TRADE_COLUMNS
        if unknown:
            raise t.TradeValidationError(f"CAN'T WRITE COLUMNS: {sorted(unknown)}")

        with self._transaction() as session:
            row: TradeModel = _get_trade_row(trade_id, session)
            for column, value in changes.items():
                setattr(row, column, value)
            _check_foreign_keys(trade=_to_domain(cls=Trade, row=row), session=session)
            session.flush()

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

        #UniqueConstraintViolation == trade_id
        #ForeignKeyViolation == trade_id
        #NotNullViolation == all columns
        with self._transaction() as session:
            _ensure_trade_exists(notes.trade_id, session) # pyright: ignore[reportArgumentType]
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
            _ensure_trade_exists(new_notes.trade_id, session) # pyright: ignore[reportArgumentType]

            row: TradeNotesModel | None = session.get(TradeNotesModel, new_notes.trade_id)
            if row is None:
                session.add(TradeNotesModel(**_field_values(new_notes)))
            else:
                for name, value in _field_values(new_notes, exclude="trade_id").items():
                    setattr(row, name, value)
                session.flush()

    def delete_trade_notes(self, trade_id: int) -> None:
        with self._transaction() as session:
            _ensure_trade_exists(trade_id, session)
            session.delete(_get_notes_row(trade_id, session))

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

            #at this point, both FKs have been checked, so we rule out Foreign key constraint violation.
            session.add( TradeParametersModel(trade_id=trade_id, parameter_id=parameter_id))
            session.flush()

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

        with self._transaction() as session:
            accounts: list[AccountsModel] = list(
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
                raise t.InvalidIdentifierError("INVALID ACCOUNT ID. NO ACCOUNT FOUND")

            pnl = session.scalar(
                select(func.coalesce(func.sum(TradeModel.dollar_amount), 0)).where(
                    TradeModel.account_id == account_id
                )
            )

            return float(starting_balance + pnl) # pyright: ignore[reportOperatorIssue]

    def get_account_balance_as_of(
    self, account_id: int, as_of_date: date, as_of_time: time,
    exclude_trade_id: int | None = None,
) -> float:

#PROBLEM: The current get_current_account_balance sums every trade on the account,
# with no time filter and no exclusion. That causes the two B2 problems:
#Amending: the sum includes the trades own P&L,
#so risk_percent is measured against a balance that already contains the result of the trade it describes.
#Backdating: a trade from three weeks ago is measured against todays balance,
#which includes three weeks of later results.
#The fix is to come up with an "as-off balance." What as-off means in this context:
#The balance the account had at a specific moment in the trades life, not the balance right now.
#For a trade, that moment is its entry, because risk_percent answers
#“how much of my equity did I put at risk when I took this?”
        with self._transaction() as session:
            starting = session.scalar(
                select(AccountsModel.starting_balance)
                .where(AccountsModel.account_id == account_id)
            )
            if starting is None:
                raise t.InvalidIdentifierError("INVALID ACCOUNT ID. NO ACCOUNT FOUND")

            closed_before = or_(TradeModel.date < as_of_date,
                and_(TradeModel.date == as_of_date, TradeModel.exit_time <= as_of_time),
            )
            query = select(func.coalesce(func.sum(TradeModel.dollar_amount), 0)).where(
                TradeModel.account_id == account_id, closed_before
            )
            if exclude_trade_id is not None:
                query = query.where(TradeModel.trade_id != exclude_trade_id)

            return float(starting + session.scalar(query)) # pyright: ignore[reportOperatorIssue]

    def delete_account_from_db(self, account_id: int) -> None:
        """DELETE ACCOUNT DETAILS FROM THE ACCOUNTS TABLE"""
        """accounts that have trades can't be deleted because the account_id
        is a FK on the trades table and pragma FKs is on so account deletion
        cause a constraint violation error, so we deactivate the account instead"""

        with self._transaction() as session:
            if session.get(AccountsModel, account_id) is None:
                raise t.InvalidIdentifierError("INVALID ACCOUNT_ID. ACCOUNT NOT FOUND")

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

    def get_chart(self, trade_id: int, chart_id: int) -> TradeChart:
        with self._transaction() as session:
            row = session.get(ChartsModel, chart_id)
            if row is None or row.trade_id != trade_id:   # 404 for someone else's chart, never 403 (F3)
                raise t.ChartsNotFoundError("NO SUCH CHART FOR THIS TRADE")
            return _to_domain(TradeChart, row)

    def delete_chart(self, trade_id: int, chart_id: int) -> TradeChart:
        with self._transaction() as session:
            row = session.get(ChartsModel, chart_id)
            if row is None or row.trade_id != trade_id:
                raise t.ChartsNotFoundError("NO SUCH CHART FOR THIS TRADE")
            chart = _to_domain(TradeChart, row)
            session.delete(row)
        return chart

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

                if not parameter_id:
                    raise t.InvalidIdentifierError(
                        "INVALID PARAMETER NAME. CHECK INPUTS"
                    )

                parameter_ids.append(parameter_id)

            return parameter_ids

    def get_parameter_names(self, parameter_ids: list) -> list[str]:
        """RETRIEVE THE PARAMETER_NAME CORRESPONDING TO A PARAMETER_ID"""

        # We have a list of IDs for the parameters present for a trade fetched from the
        # trade_parameters junction table which stores (trade_id, parameter_id) pairs.
        # We need to show the trader which parameters were present for the trade but a parameter_id
        # doesn't offer any informational value to the trader. We need the actual parameter names so we query.

        parameter_names: list[str] = []

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

            if points is None:
                raise t.InvalidIdentifierError(
                    "INVALID ENTRY EXECUTION ID. CHECK INPUTS"
                )

            return points

    def get_trade_management_points(self, management_id: int) -> int:
        """RETRIEVE THE POINTS CORRESPONDING TO A TRADE MANAGEMENT ARCHETYPE"""
        """trade_management points is used in the grading logic of individual trades"""

        with self._transaction() as session:
            points: int | None = session.execute(
                select(TradeManagementModel.points).where(
                    TradeManagementModel.management_id == management_id
                )
            ).scalar_one_or_none()

            if points is None:
                raise t.InvalidIdentifierError(
                    "INVALID TRADE MANAGEMENT ID. CHECK INPUTS"
                )

            return points

    def get_models_list(self) -> list[TradingModel]:
        with self._transaction() as session:
            rows: ScalarResult[Models] = session.scalars(statement=select(Models))

            return [_to_domain(cls=TradingModel, row=row) for row in rows]


    def get_entry_executions_list(self) -> list[EntryExecution]:
        with self._transaction() as session:
            rows: ScalarResult[EntryExecutionModel] = session.scalars(statement=select(EntryExecutionModel))

            return [_to_domain(cls=EntryExecution, row=row) for row in rows]

    def get_trade_managements_list(self) -> list[TradeManagement]:
        with self._transaction() as session:
            rows: ScalarResult[TradeManagementModel] = session.scalars(statement=select(TradeManagementModel))

            return [_to_domain(cls=TradeManagement, row=row) for row in rows]

    def get_parameters_list(self):
        with self._transaction() as session:
            rows: ScalarResult[ParametersModel] = session.scalars(statement=select(ParametersModel))

            return [_to_domain(cls=Parameter, row=row) for row in rows]

#-------REPORTS/STATISTICS/ANALYTICS AGGREGATION DATABASE METHODS FOR REPORTS.PY-------

    def get_global_stats_rows(self):
        # NOT BEING IMPLEMENTED RIGHT NOW TILL WE SET UP REPORTS.PY
        pass


