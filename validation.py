from datetime import date, time

import exceptions as t
from models import Trade, TradeDirection

#INPUTS: TRADE OBJECT.
#OUTPUTS: RETURN VALIDATED TRADE OBJECT.
#RESPONSIBILITY: MAKE SURE THE TRADE DATA IS ERROR FREE.
#ERRORS: TYPE VALIDATION, STRUCTURAL VALIDATION: REQUIRED FIELDS EXIST -> ENFORCED BY TRADE DATACLASS.
#BUSINESS RULES VALIDATION EG. CROSS FIELD VALIDATION.

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
def validate_trade_data(trade: Trade) -> Trade:
    type_validation(trade)
    validate_price_logic(trade)

    return Trade

def type_validation(trade: Trade) -> None:
    """RESPONSIBLE FOR DATA TYPE VALIDATION FOR ALL TRADE FIELDS"""

    #MAKE THE CODE DECLARATIVE.
    #STATE WHAT SHOULD BE TRUE, NOT HOW TO CHECK IT.
    valid_types = [
        #(field_name, field_value, expected_type, positive_check)
        ("entry_price", trade.entry_price, float, True),
        ("exit_price", trade.exit_price, float, True),
        ("take_profit", trade.take_profit, float, True),
        ("stop_loss", trade.stop_loss, float, True),
        ("position_size", trade.position_size, float, True),
        ("entry_time", trade.entry_time, time, False),
        ("exit_time", trade.exit_time, time, False),
        ("date", trade.date, date, False),
        ("model_id", trade.model_id, int, True),
        ("account_id", trade.account_id, int, True),
        ("management_id", trade.management_id, int, True),
        ("entry_execution_id", trade.entry_execution_id, int, True),
        ("dollar_amount", trade.dollar_amount, float, False),
        ("profit_loss", trade.profit_loss, float, False),
        ("rr_multiple", trade.rr_multiple, float, False),
    ]

    for name, value, expected_type, positive_check in valid_types:
        if not isinstance(value, expected_type):
            raise t.Trade_Validation_Error(f"{name} MUST BE {expected_type}. GOT {type(value).__name__}")

        if positive_check and value <= 0:
            raise t.Trade_Validation_Error(f"{name} MUST EXCEED ZERO. GOT {value} WHICH IS <= 0.")

def validate_price_logic(trade: Trade) -> None:
    """RESPONSIBLE FOR CROSS FIELD VALIDATION."""
    """BUSINESS RULES LOGIC VALIDATION."""
    
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