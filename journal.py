from datetime import date, time

import exceptions as t
from database import Database
from models import Account, Trade, TradeChart, TradeDirection, TradeNotes  # noqa: F401

trade1 = Trade(
    trade_id= 1,
    entry_price= 4023.90,
    exit_price= 4030.40,
    take_profit= 4045.00,
    stop_loss= 4017.58,
    position_size= 0.04,
    entry_time= time(10, 30),
    exit_time= time(12, 45),
    date= date(2026, 8, 1),
    model_id= 4,
    account_id= 1,
    management_id= 1,
    entry_execution_id= 1,
    asset= "XAUUSD",
    direction= "long",
    dollar_amount= 26.0,
    profit_loss= 26.0,
    rr_multiple= 1,
    overall_trade_grade= "C"
)

class Journal:

    def __init__(self, db: Database):
        self.db = db
 
#INPUTS: TRADE OBJECT.
#OUTPUTS: RETURN VALIDATED TRADE OBJECT.
#RESPONSIBILITY: MAKE SURE THE TRADE DATA IS ERROR FREE.
#ERRORS: TYPE VALIDATION, STRUCTURAL VALIDATION: REQUIRED FIELDS EXIST -> ENFORCED BY TRADE DATACLASS.
#BUSINESS RULES VALIDATION.

#CROSS-FIELD VALIDATION.
#ENTRY_TIME CAN'T BE GREATER THAN EXIT_TIME.
#ENTRY_TIME CAN'T BE EQUAL TO EXIT_TIME.
#ENTRY_PRICE CAN'T EQUAL TAKE_PROFIT/STOP_LOSS.

#DIRECTION BASED RELATIONSHIPS.
#RELATIONSHIP BETWEEN ENTRY_PRICE, EXIT_PRICE AND (TAKE_PROFIT, STOP_LOSS)
#RELATIONSHIP BETWEEN EXIT_PRICE AND (TAKE_PROFIT, STOP_LOSS)
#LONG: EXIT_PRICE CAN'T BE GREATER THAN TAKE_PROFIT.
#LONG: STOP_LOSS CAN'T BE GREATER THAN EXIT_PRICE.
#SHORT: TAKE_PROFIT CAN'T BE GREATER THAN EXIT_PRICE.
#SHORT: EXIT_PRICE CAN'T BE GREATER THAN STOP_LOSS.

#RELATIONSHIP BETWEEN ENTRY_PRICE AND (TAKE_PROFIT, STOP_LOSS)
#LONG: ENTRY_PRICE CAN'T BE GREATER THAN TAKE_PROFIT.
#LONG: STOP_LOSS CAN'T BE GREATER THAN ENTRY_PRICE.
#SHORT: ENTRY_PRICE CAN'T BE GREATER THAN STOP_LOSS.
#SHORT: TAKE_PROFIT CAN'T BE GREATER THAN ENTRY_PRICE.

    def _validate_price_logic(self, trade: Trade) -> None:
        """RESPONSIBLE FOR CROSS FIELD VALIDATION."""

        islong = trade.direction == TradeDirection.LONG

        #DECLARATIVE RULE TABLE: RULES AS DATA: CROSS FIELD VALIDATION RULES.
        rules = [
            (trade.entry_time >= trade.exit_time, "ENTRY TIME CAN'T EXCEED OR BE EQUAL TO EXIT TIME."),
            (islong and trade.exit_price > trade.take_profit, "LONG EXIT PRICE CAN'T EXCEED TAKE PROFIT."),
            (islong and trade.entry_price > trade.take_profit, "LONG ENTRY PRICE EXCEED TAKE PROFIT."),
            (islong and trade.stop_loss > trade.exit_price, "LONG STOP LOSS CAN'T EXCEED EXIT PRICE."),
            (islong and trade.stop_loss > trade.entry_price, "LONG STOP LOSS CAN'T EXCEED ENTRY PRICE."),
            (not islong and trade.exit_price > trade.stop_loss, "SHORT EXIT PRICE CAN'T EXCEED STOP LOSS."),
            (not islong and trade.entry_price > trade.stop_loss, "SHORT ENTRY PRICE CAN'T EXCEED STOP LOSS."),
            (not islong and trade.take_profit > trade.entry_price, "SHORT TAKE PROFIT CAN'T EXCEED ENTRY PRICE."),
            (not islong and trade.take_profit > trade.exit_price, "SHORT TAKE PROFIT CAN'T EXCEED EXIT PRICE."),
            (trade.entry_price in (trade.take_profit, trade.stop_loss), "ENTRY PRICE CAN'T EQUAL TAKE PROFIT OR STOP LOSS."),
        ]

        for condition, message in rules:
            if condition:
                raise t.Trade_Validation_Error(message)

    def _validate_time_logic(self, trade: Trade) -> None:
        """RESPONSIBLE FOR TIME LOGIC VALIDATION."""

        time_values = [trade.entry_time, trade.exit_time]

        #DATETIME.TIME VALUES YOU CAN'T HAVE ZERO CHECKS.
        #SINCE THERE IS NO SUPPORT FOR >= 0 OR POSITIVITY BASICALLY.
        for value in time_values:
            if not isinstance(value, time):
                raise t.Trade_Validation_Error(f"INVALID TIME INPUT. {value} MUST BE TIME OBJECT.")

    def _validate_float_values(self, **fields: float) -> None:
        """RESPONSIBLE FOR FLOAT TYPE VALIDATION"""
        """FLOAT VALUES: ENTRY_PRICE, EXIT_PRICE, TAKE_PROFIT, STOP LOSS,
        POSITION_SIZE, DOLLAR_AMOUNT, PROFIT_LOSS, RR_MULTIPLE"""

        for name, value in fields.items():
            if not isinstance(value, float):
                raise t.Trade_Validation_Error(f"INVALID FLOAT VALUE. {name.upper()} MUST BE A FLOAT VALUE. GOT {value}.")

    def _validate_trade_data(self, trade: Trade) -> Trade:
        #STRUCTURAL/TYPE CHECKS SHOULD HAPPEN BEFORE BUSINESS RULE LOGIC VALIDATION.
        #VALIDATE THE SHAPE OF THE DATA BEFORE YOU VALIDATE IT'S MEANING.
        
        int_values = [trade.model_id, trade.management_id, trade.entry_execution_id]
        
        for value in int_values:
            if not isinstance(value, int) or value <= 0:
                raise t.Trade_Validation_Error(f"INVALID INT VALUE. {value} MUST BE AN INTEGER AND > 0.")
        
        if not isinstance(trade.date, date):
            raise t.Trade_Validation_Error(f"DATE SHOULD BE A DATE VALUE NOT {trade.date}.")
        
        return trade

#INPUTS: TRADE OBJECT.
#OUTPUTS: RETURNS TRADEID.
#RESPONSIBILITY: SAVES A TRADE ENTRY TO TRADES TABLE IN DATABASE.
#ERRORS: CONSTRAINT VIOLATION ERROR
#CALLS SAVE_TRADE METHOD IN DATABASE CLASS.
    def record_trade(self, trade: Trade):
        valid_trade = self._validate_trade_data(trade)
        trade_id = self.db.save_trade(valid_trade)
        return trade_id
        
#INPUTS: CHART OBJECT, TRADE_ID
#OUTPUTS: RETURNS A CHARTID. RESEARCH WHY WE NEED TO RETURN A CHARTID.
#RESPONSIBILITY: ADD CHARTS TO THE CHARTS TABLE
#ERRORS: CONSTRAINT VIOLATION ERROR. UNDERSTAND WHAT THIS MEANS FIRST.
#HOW DO WE KNOW THAT THE CHARTS HAVE BEEN ADDED?
#CALLS ADD_CHART METHOD IN DATABASE CLASS
    def attach_charts(self, trade_id: int, chart: TradeChart):
        pass

#INPUTS: TRADE_ID
#OUTPUTS: ENTRY_EXECUTION, TRADE_MANAGEMENT, TRADE_PARAMETERS, MODEL USED
#RESPONSIBILITY: EVALUATES THE POINTS ATTACHED TO A TRADE.
#ERRORS: INVALID_IDENTIFIER_ERROR, TRADE_NOT_FOUND_ERROR.
#CALLS GET_ENTRY_EXECUTION_POINTS, GET_TRADE_MANAGEMENT_POINTS
#AND GET_PARAMETER_POINTS METHODS IN DATABASE CLASS  
    def evaluate_trade(self, trade_id: int):
        pass

#INPUTS: ENTRY_EXECUTION POINTS, TRADE_MANAGEMENT POINTS,
#TRADE_PARAMETERS, TRADE_ID
#OUTPUTS: GRADE AS A STR VALUE.
#RESPONSIBILITY: RETURN THE GRADE OF A TRADE.
#ERRORS: CONSTRAINT VIOLATION ERROR, INVALID IDENTIFIER ERROR.
#CALLS EVALUATE_TRADE() METHOD IN JOURNAL CLASS
    def grade_trade(self):
        pass

#INPUTS: TRADE_NOTE OBJECT, TRADE_ID.
#OUTPUTS: NOTHING. HOW DO WE KNOW THAT THE NOTES HAVE BEEN ADDED?
#RESPONSIBILITY: Add thoughts, mistakes, emotions, lessons, observations.
#ERRORS: TRADE_NOT_FOUND_ERROR.
#CALLS ADD_TRADE_NOTES METHOD IN DATABASE CLASS.
    def add_reflection_notes(self, trade_id: int, trade_notes: TradeNotes):
        pass

#INPUTS: TRADE_ID.
#OUTPUTS: A TRADE OBJECT FROM THE TRADES TABLE.
#RESPONSIBILITY: SHOW THE TRADE DATA OF A PARTICULAR TRADE.
#ERRORS: TRADE_NOT_FOUND_ERROR FOR MISSING TRADE.
#CALLS GET_BY_ID METHOD IN DATABASE CLASS.
    def get_trade(self, trade_id: int):
        pass

#JOURNAL ENTRY DEFINITION: TRADES DATA FROM TRADES TABLE,
#TRADE NOTES, CHARTS, TRADE_PARAMETERS PRESENT AND ABSENT,
#ACCOUNT USED, TRADE MANAGEMENT/ENTRY_EXECUTION INFO STATS,
#MODEL USED, GRADE.
#INPUTS: TRADE_ID
#OUTPUTS: TRADE OBJECT, TRADE_NOTE OBJECT, CHART OBJECT,
#TRADE PARAMETERS DATA, MANAGEMENT/ENTRY_EXECUTION DATA ETC
#RESPONSIBILITY: SHOW THE COMPLETE TRADE INFORMATION TO A USER.
#ERRORS: ALL METHODS CALLED BY THIS FUNCTION, ALL THEIR ERRORS APPLY TOO
#TBD: SPECIFIC DEFINITION OF THE ERRORS IS TO BE DETERMINED.
    def get_journal_entry(self, trade_id: int):
        pass

#ENTIRE TRADE DEFINITION: SAME AS ABOVE.
#INPUTS: TRADE OBJECT, TRADE_NOTE OBJECT, CHART OBJECT,
#TRADE PARAMETERS DATA, MANAGEMENT/ENTRY_EXECUTION DATA, ETC
#OUTPUT: SUCCESS/FAILURE MESSAGE TO SHOW SUCCESS OR FAILURE.
#RESPONSIBILITY: CREATE A FULL JOURNAL ENTRY THAT CONTAINS ALL THE
#TRADE DATA STATS TO BE JOURNALED AT ONCE.
#ERRORS: ALL METHODS CALLED BY THIS FUNCTION, ALL THEIR ERRORS APPLY TOO
#TBD: SPECIFIC DEFINITION OF THE ERRORS IS TO BE DETERMINED. 
    def record_journal_entry(self, trade: Trade, chart: TradeChart, trade_notes: TradeNotes):
        pass

#QUESTION TO PONDER: WHAT DOES AMEND JOURNALE ENTRY MEAN?
#I discovered something was wrong or incomplete. Change it.
#WHAT IS BEING AMENDED? TRADES TABLE OR ANY OTHER TABLE?
#INPUTS: TRADE_ID, TRADE CHANGES TO BE MADE.
#OUTPUTS: SUCCESS/FAILURE MESSAGE.
#RESPONSIBILITY: AMEND A TABLE IN DATABASE DEPENDING ON USER PREFERENCE.
#ERRORS: TRADE_NOT_FOUND_ERROR.
#CALLS UPDATE_TRADE_GRADE, UPDATE_TRADE_FIELD.
    def amend_journal_entry(self, trade_id: int, trade_changes):
        pass