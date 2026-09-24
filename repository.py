from typing import Any

from sqlalchemy import create_engine, exc, exists, func, select
from sqlalchemy.orm import sessionmaker

import exceptions as t
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

SQLALCHEMY_DATABASE_URL = "sqlite:///./kowalski.db"


model_rows = [
    Models(
        model_name= 'BREAD AND BUTTER MODEL',
        description= 'REVERSAL OR CONTINUATION USING WEEKLY AND DAILY PROFILES.' \
        'ENTRY FRAMED ON CISD ORDERBLOCK LIMIT ENTRY.'
    ),
    Models(
        model_name= 'ONE SHOT ONE KILL',
        description= 'USE ICT WEEKLY PROFILES TO NARROW DOWN REVERSAL DAY OF THE WEEK. ENTRY ON PREMIUM/DISCOUNT PD ARRAYS.'
    ),
    Models(
        model_name= '2022 FVG MODEL',
        description= 'STOP RAID IN OPPOSITE DIRECTION OF DAILY BIAS. MARKET STRUCTURE SHIFT. ENTRY ON FIRST FVG AFTER REVERSAL.'
    ),
    Models(
        model_name= 'ERL TO IRL MODEL',
        description= 'PRICE TRADES BELOW OLD LOW (ERL) LEADING TO A MOVE HIGHER INTO FVG (IRL). ENTRY USING LTF CISD PATTERN.'
    ),
    Models(
        model_name= 'NO MODEL USED',
        description= 'NO TRADING MODEL WAS USED FOR THIS TRADE. IT WAS A YOLO TRADE AKA A GHOST TRADE. INSTANT F GRADE.'
    )
]

#CARDINAL QUESTION TO LIVE BY: what is one row of my result supposed to contain?

#NOTES TO SELF: TRADE_ID FOREIGN KEY LOOK-UPS HAPPENS OFTEN ENOUGH THAT IT SHOULD BE
#REFACTORED INTO A PRIVATE HELPER METHOD. IMPLEMENT FUTURE FIX AFTER CODE REVIEW!
#current implementation returns _orm objects, turn these into the domain dataclasses using _to_domain() helper
#to avoid DetachedInstanceErrors when trying to access relationships attributes later on.
#implement cascade on delete for trades and accounts and children. set cascade="all, delete-orphan" in the DB models relationships
class Repository:
    def __init__(self, db_url=SQLALCHEMY_DATABASE_URL):
        self.db_path = db_url

        self.engine = create_engine(
            url= self.db_path,
            connect_args= {"check_same_thread" : False},
            echo= True
        )

        self.SessionLocal = sessionmaker(bind= self.engine, expire_on_commit= False)
        self.initialize_database()

    def initialize_database(self):

        import database_models  # noqa: F401
        Base.metadata.create_all(bind= self.engine)

        with self.SessionLocal.begin() as session:
            count = session.scalar(select(func.count()).select_from(Models))
            if count == 0:
                session.add_all(model_rows)

#TRADE DOMAIN MODEL DATABASE METHODS; CRUd
    def save_trade(self, trade: Trade) -> int:
        """PERSIST A TRADE TO THE REPOSITORY"""

        #Check for validity of foreign keys and raise exception loudly
        #before doing anything else.
        self._check_foreign_keys(trade)

        new_trade = TradeModel(
            entry_price = trade.entry_price,
            exit_price = trade.exit_price,
            take_profit= trade.take_profit,
            stop_loss= trade.stop_loss,
            position_size= trade.position_size,
            entry_time= trade.entry_time,
            exit_time= trade.exit_time,
            date= trade.date,
            model_id= trade.model_id,
            account_id= trade.account_id,
            management_id= trade.management_id,
            entry_execution_id= trade.entry_execution_id,
            asset= trade.asset,
            direction= trade.direction,
            dollar_amount= trade.dollar_amount,
            duration= trade.duration,
            result= trade.result,
            rr_multiple= trade.rr_multiple,
            risk_percent= trade.risk_percent,
            overall_trade_grade= trade.overall_trade_grade
        )

        with self.SessionLocal() as session:
            session.add(new_trade)

            try:
                session.flush()
            except exc.IntegrityError as e:
                session.rollback()
                raise t.Constraint_Violation_Error(f"CONSTRAINT VIOLATION DETECTED: {e.orig}") from e

            trade_id = new_trade.trade_id

            session.commit()    #Explict commits for INSERTs

        return trade_id

    def get_by_id(self, trade_id: int) -> TradeModel:
        """RETRIEVE A TRADE FROM THE REPOSITORY"""

        with self.SessionLocal.begin() as session:
            result = session.execute(select(TradeModel).where(TradeModel.trade_id == trade_id))

            #scalar_one_or_none() - Preferred for querying using a PK.
            trade = result.scalar_one_or_none()
            if not trade:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. NOT TRADE FOUND!")

        return trade

    def get_all_trades(self):
        """RETRIEVES ALL TRADES FROM THE REPOSITORY"""

        with self.SessionLocal.begin() as session:
            result = session.execute(select(TradeModel))
            trades = result.scalars().all()

        return trades

    def update_trade_grade(self, trade_id: int, new_grade: TradeGrade):
        """UPDATES TRADE.OVERALL_TRADE_GRADE IN THE REPOSITORY"""

        if not isinstance(new_grade, TradeGrade):
            raise t.Invalid_Grade_Error("GRADE NEEDS TO BE OF TYPE TRADEGRADE.")

        with self.SessionLocal.begin() as session:
            trade_row = session.execute(
                select(TradeModel).where(TradeModel.trade_id == trade_id)
            ).scalar_one_or_none()

            if not trade_row:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. NO TRADE TO UPDATE")

            trade_row.overall_trade_grade = new_grade

    def update_trade_field(self, trade_id: int, new_value: Any, column: AmendableColumns):
        """UPDATES A DYNAMIC TRADE COLUMN BASED ON TRADER PREFERENCE"""

        if column not in AmendableColumns:
            raise t.Invalid_Column_Name_Error("CAN'T UPDATE INVALID COLUMN")

        #use setattr() to dynamically update the trade column with the new_value
        with self.SessionLocal.begin() as session:
            trade_row = session.execute(
                select(TradeModel).where(TradeModel.trade_id == trade_id)
            ).scalar_one_or_none()

            if not trade_row:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. NO TRADE TO UPDATE")

            setattr(trade_row, column, new_value)

    def delete_trade(self, trade_id: int):
        """DELETES A TRADE ROW FROM THE REPOSITORY"""

        with self.SessionLocal.begin() as session:
            trade_row = session.get(TradeModel, trade_id)

            if not trade_row:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. NO TRADE TO UPDATE")

            session.delete(trade_row)

#TRADE NOTES DOMAIN MODEL DATABASE METHODS; CRUD
    def add_trade_notes(self, notes: TradeNotes):

        #current implementation assumes that once you check for validity of trade_id,
        #you are done with the Integrity errors. This is wrong.
        #What if a trader tries to insert notes for a trade that already exists?
        #That's a constraint violation for trade_id as a PK which must be UNIQUE.
        with self.SessionLocal() as session:
            trade = session.execute(
                select(TradeModel).where(TradeModel.trade_id == notes.trade_id)
            ).scalar_one_or_none()

            if not trade:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. NO TRADE FOUND")

            session.add(TradeNotesModel(
                trade_id= notes.trade_id,
                emotions= notes.emotions,
                mistakes= notes.mistakes,
                lessons= notes.lessons,
                general_notes= notes.general_notes,
            ))

            try:
                session.flush()
            except exc.IntegrityError as e:
                session.rollback()
                raise t.Constraint_Violation_Error(f"TABLE/COLUMN CONSTRAINT VIOLATION: {e.orig}")
            except exc.DatabaseError as e:
                session.rollback()
                raise t.DatabaseError(f"INTERNAL ERROR DETECTED WITH THE DATABASE: {e.orig}")

            session.commit()   #Explict commits for INSERTs

    def get_trade_notes(self, trade_id: int):

        #current implementation conflates "trade doesn't exist" with "no rows for this trade"
        #a trade might exist in trades table, but has no notes yet in the trade_notes table.
        #you can check validity of the trade_id separately and then check the notes table and
        #return an empty list or None not an exception if trade is valid but no notes attached to it yet.
        with self.SessionLocal.begin() as session:
            notes = session.get(TradeNotesModel, trade_id)

            if not notes:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. TRADE NOT FOUND")

        return notes

    def update_trading_notes(self, trade_id: int, new_notes: TradeNotes):
        """UPDATES FULL ROW ON TRADE NOTES DATABASE TABLE"""

        with self.SessionLocal.begin() as session:
            notes = session.get(TradeNotesModel, trade_id)

            if not notes:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. NO TRADE FOUND")

            notes.emotions = new_notes.emotions
            notes.mistakes = new_notes.mistakes
            notes.lessons = new_notes.lessons
            notes.general_notes = new_notes.general_notes

#TRADE PARAMETERS DOMAIN MODEL DATABASE METHODS; CRUD
    def add_trade_parameters(self, trade_id: int, parameter_id: int):

        #trade_parameters junction table dual primary key is an explicit imperative
        #domain invariant hence this is the Constraint Violation Error we watching for.
        #THE (TRADE_ID, PARAMETER_ID) PAIR MUST BE UNIQUE!
        #So explicitly check for validity of trade_id to rule out foreign key constraint violation.
        #Not using self.SessionLocal.begin() because I want to commit explicitly for writes.

        #For the Trade_id foreign key look-ups, session.get() would be an easier syntax
        #But I am explicitly using select because I like it since it looks more like SQLAlchemy proper syntax.
        with self.SessionLocal() as session:
            #validity check for trade_id FK
            trade = session.execute(
                select(TradeModel).where(TradeModel.trade_id == trade_id)
            ).scalar_one_or_none()

            if not trade:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. NO TRADE FOUND")

            #validity check for parameter_id FK
            parameter = session.execute(
                select(ParametersModel).where(ParametersModel.parameter_id == parameter_id)
            ).scalar_one_or_none()

            if not parameter:
                raise t.Invalid_Identifier_Error("INVALID PARAMETER ID. PARAMETER NOT FOUND")

            #at this point, both FKs have been checked, so we rule out Foreign key constraint violation.
            session.add(TradeParametersModel(
                trade_id= trade_id,
                parameter_id= parameter_id
            ))

            try:
                session.flush()
            except exc.IntegrityError as e:
                session.rollback()
                raise t.Constraint_Violation_Error(f"UNIQUE CONSTRAINT VIOLATION DETECTED: {e.orig}") from e
            except exc.DatabaseError as e:
                session.rollback()
                raise t.DatabaseError(f"INTERNAL ERROR DETECTED WITH THE DATABASE: {e.orig}")

            session.commit()    #Explict commits for INSERTs

    def get_trade_parameters(self, trade_id: int) -> list[TradeParametersModel]:

        #result should look like this: [(1,2), (1,3), (1,5), (1,8)] each as (trade_id, parameter_id).
        #a single (trade_id, parameter_id) == TradeParametersModel, so the result should be a list.
        #the (trade_id, parameter_id) pair isn't what we want, we want the parameter_ids as a list of ints.
        #session.scalars() is the shortcut for session.execute().scalars().all()

        #ScalarResult[TradeParametersModel] is different from list[TradeParametersModel],,how??
        with self.SessionLocal.begin() as session:
            parameters = list(session.scalars(
                select(TradeParametersModel).where(TradeParametersModel.trade_id == trade_id)
            ))

            #Currently zero parameters is treated as an error. Zero parameters is valid state. FIX!
            if not parameters:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. NO TRADE MATCHES THAT ID")

        #revisit the conversion step from list[TradeParametersModel] -> list[ints]
        return parameters

#TRADING ACCOUNTS DOMAIN MODEL DATABASE METHODS; CRUD
    def create_trading_account(self, account: Account):
        """PERSIST A NEW TRADING ACCOUNT TO THE REPOSITORY"""

        new_account = AccountsModel(
            account_name= account.account_name,
            account_type= account.account_type,
            broker= account.broker,
            starting_balance= account.starting_balance,
            is_active= account.is_active
        )
        with self.SessionLocal() as session:
            session.add(new_account)
            try:
                session.flush()
            except exc.IntegrityError as e:
                session.rollback()
                raise t.Constraint_Violation_Error(f"CHECK COLUMN CONSTRAINT VIOLATION DETECTED: {e.orig}")
            except exc.DatabaseError as e:
                session.rollback()
                raise t.DatabaseError(f"INTERNAL ERROR DETECTED WITH THE DATABASE: {e.orig}")

            account_id = new_account.account_id

            session.commit()   #Explict commits for INSERTs

        return account_id

    def get_trading_accounts(self):

        #orm_queryguide_select_orm_entities - contrasts the behavior of _orm.Session.execute to _orm.Session.scalars
        with self.SessionLocal.begin() as session:
            accounts = list(session.scalars(select(AccountsModel)).all())

            #FUTURE FIX: EMPTY ACCOUNTS TABLE SHOULD RETURN AN EMPTY LIST NOT RAISING AN EXCEPTION.
            #CURRENT ARCHICTECTURE ASSUMES QUERYING ACCOUNTS BEFORE ANY HAS BEEN CREATED IS AN ERROR.
            if not accounts:
                raise t.Empty_Accounts_Table_Error("NO TRADING ACCOUNTS HAVE BEEN CREATED YET!")

        #does returning accounts outside the with context manager cause an error?
        #do I still have access to accounts if .scalars() returns a lazy ScalarResult?
        return accounts

    def get_current_account_balance(self, account_id: int) -> float | None:

        with self.SessionLocal.begin() as session:
            starting_balance = session.scalar(
                select(AccountsModel.starting_balance).where(AccountsModel.account_id == account_id)
            )

            if starting_balance is None:
                raise t.Invalid_Account_Error("INVALID ACCOUNT ID. NO ACCOUNT FOUND")

            pnl = session.scalar(
                select(func.coalesce(func.sum(TradeModel.dollar_amount), 0)).where(TradeModel.account_id == account_id)
            )

            return pnl

    def delete_account_from_db(self, account_id: int):

        #account_id == PK. Use scalar_one_or_none() for PK querying.
        with self.SessionLocal.begin() as session:
            account = session.execute(
                select(AccountsModel).where(AccountsModel.account_id == account_id)
            ).scalar_one_or_none()

            if not account:
                raise t.Invalid_Account_Error("INVALID ACCOUNT_ID. ACCOUNT NOT FOUND")

            session.delete(account)

#TRADING CHARTS DOMAIN MODEL DATABASE METHODS; CRUD
    def add_chart(self, charts: TradeChart):

        #I don't want a Foreign Key constraint violation error being raised.
        #It takes attention away from the other column constraints.

        #A trader adding charts for a trade that already has the same charts,
        #causes Integrity error since filepath and filename must be unique.

        #NOT NULL column constraints can't be reached because in TradeChart only chart_id
        #can be None, the rest have to be provided while constructing TradeChart instance
        #or we get an error. Repository.add_chart() receives a fully populated valid TradeChart instance.

        new_chart = ChartsModel(
            trade_id= charts.trade_id,
            filepath= charts.filepath,
            filename= charts.filename,
            upload_date= charts.upload_date
        )

        with self.SessionLocal() as session:
            trade = session.execute(
                select(TradeModel).where(TradeModel.trade_id == charts.trade_id)
            ).scalar_one_or_none()

            if not trade:
                raise t.Trade_Not_Found_Error(
                    "INVALID TRADE_ID. CAN'T ATTACH CHARTS FOR A NON EXISTING TRADE"
                )

            session.add(new_chart)

            try:
                session.flush()
            except exc.IntegrityError as e:
                session.rollback()
                raise t.Constraint_Violation_Error(f"TABLE/COLUMN CONSTRAINT VIOLATION: {e.orig}")
            except exc.DatabaseError as e:
                session.rollback()
                raise t.DatabaseError(f"INTERNAL ERROR DETECTED WITH THE DATABASE: {e.orig}")

            chart_id = new_chart.chart_id

            session.commit()  #Explict commits for INSERTs

        return chart_id

    def get_trade_charts(self, trade_id: int):

        with self.SessionLocal.begin() as session:
            charts = session.execute(
                select(ChartsModel).where(ChartsModel.trade_id == trade_id)
            ).scalars().all()

            if not charts:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. NO CHARTS FOUND FOR THAT TRADE_ID")

        return charts

#TRADING AMENDMENTS DOMAIN MODEL DATABASE METHODS; CRUD
    def add_trade_amendments(self, amendment: Amendments):

        new_amendment = TradeAmendmentsModel(
            trade_id= amendment.trade_id,
            column_name= amendment.column_name,
            old_value= amendment.old_value,
            new_value= amendment.new_value,
            amended_at= amendment.amended_at
        )

        #Avoid Foreign key violation by checking for existence of trade_id
        with self.SessionLocal() as session:
            trade = session.execute(
                select(TradeModel).where(TradeModel.trade_id == amendment.trade_id)
            ).scalar_one_or_none()

            if not trade:
                raise t.Trade_Not_Found_Error("INVALID TRADE_ID. CAN'T ADD CHANGES FOR A NON EXISTENT TRADE")

            session.add(new_amendment)

            try:
                session.flush()
            except exc.IntegrityError as e:
                session.rollback()
                raise t.Constraint_Violation_Error(f"TABLE/COLUMN CONSTRAINT VIOLATION: {e.orig}")
            except exc.DatabaseError as e:
                session.rollback()
                raise t.DatabaseError(f"INTERNAL ERROR DETECTED WITH THE DATABASE: {e.orig}")

            amendment_id = new_amendment.amendment_id

            session.commit()    #Explict commits for INSERTs

        return amendment_id

#STATIC LOOK UP TABLES DATABASE READ METHODS; GETTER METHODS
#STATIC TABLES: MODELS, TRADE_MANAGEMENT, PARAMETERS, ENTRY_EXECUTION
    def get_parameter_ids(self, parameter_names: list):

            #We have a list of parameter_names that we want to get the
            #corresponding id for each parameter from the parameters table.
            #We can't assign ids using indices from enumerate() because the
            #specific parameter_id assigned in the parameters table has domain significance.

            parameter_ids = []

            with self.SessionLocal.begin() as session:
                for parameter in parameter_names:
                    parameter_id = session.execute(
                        select(ParametersModel.parameter_id).where(ParametersModel.parameter_name == parameter)
                    ).scalar_one_or_none()

                    #We shouldn't be getting None as a value after the query but if
                    #parameter_names list somehow has an invalid parameter name, then raise exception.
                    #I thought about using scalar_one() to enforce the domain invariant but I don't want
                    #a non-domain exception firing and leaking out into the higher level modules like journal.py.
                    if not parameter_id:
                        raise t.Invalid_Identifier_Error("INVALID PARAMETER NAME. CHECK INPUTS")

                    parameter_ids.append(parameter_id)

            return parameter_ids

    def get_parameter_names(self, parameter_ids: list):

        #We have a list of IDs for the parameters present for a trade fetched from the
        #trade_parameters junction table which stores (trade_id, parameter_id) pairs.
        #We need to show the trader which parameters were present for the trade but a parameter_id
        #doesn't offer any informational value to the trader. We need the actual parameter names so we query.

        parameter_names = []

        with self.SessionLocal.begin() as session:
            for parameter_id in parameter_ids:
                parameter_name = session.execute(
                    select(ParametersModel.parameter_name).where(ParametersModel.parameter_id == parameter_id)
                ).scalar_one_or_none()

                #We shouldn't be getting None as a value after the query but if
                #parameter_ids list somehow has an invalid parameter_id, then raise exception.
                if not parameter_name:
                    raise t.Invalid_Identifier_Error("INVALID PARAMETER ID. CHECK INPUTS")

                parameter_names.append(parameter_name)

        return parameter_names

    def get_entry_execution_points(self, entry_execution_id: int):

        with self.SessionLocal.begin() as session:
            points = session.execute(
                select(EntryExecutionModel.points).where(EntryExecutionModel.entry_execution_id == entry_execution_id)
            ).scalar_one_or_none()

            if not points:
                raise t.Invalid_Identifier_Error("INVALID ENTRY EXECUTION ID. CHECK INPUTS")

        return points

    def get_trade_management_points(self, management_id: int):

        with self.SessionLocal.begin() as session:
            points = session.execute(
                select(TradeManagement.points).where(TradeManagement.management_id == management_id)
            ).scalar_one_or_none()

            if not points:
                raise t.Invalid_Identifier_Error("INVALID TRADE MANAGEMENT ID. CHECK INPUTS")

        return points

#REPORTS/STATISTICS/ANALYTICS AGGREGATION DATABASE METHODS FOR REPORTS.PY
    def get_global_stats_rows(self):
        #NOT BEING IMPLEMENTED RIGHT NOW TILL WE SET UP REPORTS.PY
        pass

#MISCELLANEOUS DATABASE METHODS FOR VARIOUS ABSTRACTIONS
    def _check_foreign_keys(self, trade: Trade):

        #TradeModel trades tables has 4 foreign keys.
        #models, accounts, trade_management, entry_execution.
        #During INSERTs into trades table, you need to check for validity of these FKs.
        #This rules out Foreign Key constraint violation error from the onset.

        with self.SessionLocal.begin() as session:

            #using exists() is more efficient than using select() to query and load the entire rows
            found = session.execute(
                select(
                    exists(Models).where(Models.model_id == trade.model_id),
                    exists(AccountsModel).where(AccountsModel.account_id == trade.account_id),
                    exists(TradeManagement).where(TradeManagement.management_id == trade.management_id),
                    exists(EntryExecutionModel).where(
                        EntryExecutionModel.entry_execution_id == trade.entry_execution_id
                    )
                )
            )

            names = ("model_id", "account_id", "management_id", "entry_execution_id")

            missing = []
            for name, ok in zip(names, found, strict=True):
                if not ok:
                    missing.append(f"{name}= {getattr(trade, name)}")

            if missing:
                raise t.Invalid_Identifier_Error(f"FOLLOWING FKs ARE MISSING: {','.join(missing)}")

    def close_db_connection(self):

        #Dispose the connection pool used by this _engine.Engine instance
        self.engine.dispose()
