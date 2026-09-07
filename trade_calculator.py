from datetime import date, datetime, time, timedelta

import exceptions as t
from models import PositionSizing, TradeAsset, TradeDirection, TradeSetup

INSTRUMENT_SPECS = {
    "NQ" : {"type" : "futures", "contract_size" : 20},
    "ES" : {"type" : "futures", "contract_size" : 50},
    "XAUUSD" : {"type" : "cfd", "contract_size" : 100},
    "XAGUSD" : {"type" : "cfd", "contract_size" : 5000},
}

MULTIPLIER = {"long" : 1, "short" : -1}
def _input_validation(setup: TradeSetup) -> TradeSetup:

    valid_types = [
        #(field_name, value, expected_type, positive_check)
        ("entry_price", setup.entry_price, (float, int), True),
        ("exit_price", setup.exit_price, (float, int), True),
        ("stop_loss", setup.stop_loss, (float, int), True),
        ("take_profit", setup.take_profit, (float, int), True),
        ("asset", setup.asset, TradeAsset, False),
        ("direction", setup.direction, TradeDirection, False),
        ("position_size", setup.position_size, (float, int), True),
        ("account_balance", setup.account_balance, (float, int), True),
        ("entry_time", setup.entry_time, (time, type(None)), False),
        ("exit_time", setup.exit_time, (time, type(None)), False),
        ("date", setup.date, (date, type(None)), False)
    ]

    for field_name, value, expected_type, positive_check in valid_types:
        if not isinstance(value, expected_type):
            raise t.Trade_Validation_Error(f"{field_name} MUST BE OF TYPE {expected_type}. GOT {type(value).__name__}")

        if positive_check and value <= 0:
            raise t.Trade_Validation_Error(f"{field_name} MUST BE GREATER THAN 0. GOT {value}.")

    return setup

def calculate_profit_loss(setup: TradeSetup) -> dict:
    #INPUTS: ASSET, DIRECTION, EXIT_PRICE, ENTRY_PRICE, POSITION_SIZE, ACCOUNT_BALANCE

    #ASSET AND DIRECTION IS A SELECT OPTION IN THE UI. USER CAN'T CHOOSE SOMETHING
    #OUTSIDE THE OPTIONS PROVIDED.
    valid_setup = _input_validation(setup)

    contract_size = INSTRUMENT_SPECS[valid_setup.asset]["contract_size"]
    multiplier = MULTIPLIER[valid_setup.direction]

    dollar_amount = (valid_setup.exit_price - valid_setup.entry_price) * multiplier * valid_setup.position_size * contract_size
    dollar_percent = (dollar_amount / valid_setup.account_balance) * 100

    verdict = "PROFIT" if dollar_amount > 0 else "LOSS"

    return {
        "RESULT" : verdict,
        "DOLLAR_AMOUNT" : round(dollar_amount, 2),
        "DOLLAR_PERCENT" : round(dollar_percent, 2),
        "DIRECTION" : valid_setup.direction
    }

def calculate_risk_reward_multiple(setup: TradeSetup) -> dict:
    #INPUTS: ASSET, TAKE_PROFIT, EXIT_PRICE, ENTRY_PRICE, STOP_LOSS, POSITION_SIZE
    valid_setup = _input_validation(setup)

    if valid_setup.entry_price in (valid_setup.take_profit, valid_setup.stop_loss):
        raise t.Trade_Validation_Error("ENTRY PRICE CAN'T BE EQUAL TO TAKE PROFIT OR STOP LOSS")

    contract_size = INSTRUMENT_SPECS[valid_setup.asset]["contract_size"]

    if valid_setup.take_profit == valid_setup.exit_price:
        profit_distance = abs(valid_setup.take_profit - valid_setup.entry_price)
    else:
        profit_distance = abs(valid_setup.exit_price - valid_setup.entry_price)
    
    risk_distance = abs(valid_setup.stop_loss - valid_setup.entry_price)

    risk_amount = risk_distance * valid_setup.position_size * contract_size
    profit_amount = profit_distance * valid_setup.position_size * contract_size
    risk_percent = risk_amount / valid_setup.account_balance

    rr_multiple = round(profit_distance / risk_distance, 2)

    return {
        "RR_MULTIPLE" : rr_multiple,
        "RISK_PERCENT": round(risk_percent, 2),
        "RISK_AMOUNT" : round(risk_amount, 2),
        "REWARD_AMOUNT" : round(profit_amount, 2),
    }


#THERE IS A PROPER DIFFERENCE BETWEEN WHAT I USE FOR LOT SIZE IN LIVE TRADING
#AND WHAT THE TRADING CALCULATOR OFFERS AS THE OPTIMAL LOT SIZE.
#THIS IS VALUABLE INSIGHT.
#SHOULD I BE RECORDING THIS DIFFERENCE???
def calculate_position_size(sizing: PositionSizing) -> float | int:
    #RETURNS LOT SIZE GIVEN INPUTS.
    #INPUTS: ENTRY_PRICE, STOP_LOSS, ASSET, ACCOUNT_BALANCE, RISK_PERCENT
    #CORE FORMULA: RISK_AMOUNT/(ENTRY_PRICE - STOP_LOSS) * CONTRACT_SIZE

    rules = [
        #(field_name, value, expected_type, positive_check)
        ("entry_price", sizing.entry_price, (float, int), True),
        ("stop_loss", sizing.stop_loss, (float, int), True),
        ("asset", sizing.asset, TradeAsset, False),
        ("account_balance", sizing.account_balance, (float, int), True),
        ("risk_percent", sizing.risk_percent, (float, int), True),
    ]

    for field_name, value, expected_type, positive_check in rules:
        if not isinstance(value, expected_type):
            raise t.Trade_Validation_Error(f"{field_name} MUST BE OF TYPE {expected_type}. GOT {type(value).__name__}")

        if positive_check and value <= 0:
            raise t.Trade_Validation_Error(f"{field_name} MUST BE GREATER THAN 0. GOT {value}.")
        
    if sizing.entry_price == sizing.stop_loss:
        raise t.Trade_Validation_Error("ENTRY PRICE CAN'T EQUAL STOP LOSS")
    
    contract_size = INSTRUMENT_SPECS[sizing.asset]["contract_size"]
    risk_distance = abs(sizing.entry_price - sizing.stop_loss)
    risk_amount = sizing.account_balance * (sizing.risk_percent/100)

    return round(risk_amount / (risk_distance * contract_size), 2)


def calculate_trade_duration(setup: TradeSetup) -> timedelta:
    #INPUTS: ENTRY_TIME, EXIT_TIME, DATE
    valid_setup = _input_validation(setup)
    entry_dt = datetime.combine(valid_setup.date, valid_setup.entry_time) # type: ignore
    exit_dt = datetime.combine(valid_setup.date, valid_setup.exit_time) # type: ignore

    if exit_dt < entry_dt:
        raise t.Trade_Validation_Error("EXIT TIME CAN'T BE LESS THAN ENTRY TIME.")

    return exit_dt - entry_dt 

