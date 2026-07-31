from dataclasses import dataclass


@dataclass
class TradeSetup:
    entry_price : float
    exit_price : float
    stop_loss : float
    take_profit : float
    account_balance : int
    risk_percent : int
    lot_size : float
    symbol : str
    direction : str

INSTRUMENT_SPECS = {
    "NQ" : {"type" : "futures", "contract_size" : 20},
    "ES" : {"type" : "futures", "contract_size" : 50},
    "XAUUSD" : {"type" : "cfd", "contract_size" : 100},
    "XAGUSD" : {"type" : "cfd", "contract_size" : 5000}
}

MULTIPLIER = {"long" : 1, "short" : -1}

#WHEN WE PASS SYMBOL AND DIRECTION TO GET_USER_INPUT(),
#DOES TRADESETUP AUTOMATICALLY ADD THEM TO ITSELF?
def main():
    symbol = get_instrument_symbol()
    direction = get_trade_direction()
    trade = get_user_input(symbol, direction)

    results = calculate_profit_loss(trade)
    for k, v in results.items():
        print(f"THE {k} IS {v}.")

    rr_multiple_metrics = calculate_risk_reward_multiple(trade)
    for k, v in rr_multiple_metrics.items():
        print(f"THE {k} IS {v}.")

    print(f"POTENTIAL POSITION SIZE: {calculate_position_size(trade)}")

def calculate_profit_loss(trade: TradeSetup):
    contract_size = INSTRUMENT_SPECS[trade.symbol]["contract_size"]
    multiplier = MULTIPLIER[trade.direction]

    dollar_amount = (trade.exit_price - trade.entry_price) * multiplier * trade.lot_size * contract_size
    dollar_percent = (dollar_amount / trade.account_balance) * 100

    verdict = "PROFIT" if dollar_amount > 0 else "LOSS"

    return {
        "RESULT" : verdict,
        "DOLLAR_AMOUNT" : round(dollar_amount, 2),
        "DOLLAR_PERCENT" : round(dollar_percent, 2),
        "DIRECTION" : trade.direction
    }

def get_trade_direction():
    accepted_values = ["long", "short"]

    while True:
        direction = input("ENTER THE TRADE DIRECTION: ").lower().strip()
        if direction in accepted_values:
            return direction
        else:
            continue

def calculate_risk_reward_multiple(trade: TradeSetup):
    contract_size = INSTRUMENT_SPECS[trade.symbol]["contract_size"]

    if trade.take_profit == trade.exit_price:
        profit_distance = abs(trade.take_profit - trade.entry_price)
    else:
        profit_distance = abs(trade.exit_price - trade.entry_price)
    
    risk_distance = abs(trade.stop_loss - trade.entry_price)

    risk_amount = risk_distance * trade.lot_size * contract_size
    profit_amount = profit_distance * trade.lot_size * contract_size

    rr_multiple = round(profit_distance / risk_distance, 2)

    return {
        "RR_MULTIPLE" : rr_multiple,
        "RISK_AMOUNT" : round(risk_amount, 2),
        "REWARD_AMOUNT" : round(profit_amount, 2)
    }


def calculate_position_size(trade: TradeSetup):
    #RETURNS LOT SIZE GIVEN INPUTS.
    #INPUTS INCLUDE: ENTRY_PRICE, STOP_LOSS, DIRECTION, INSTRUMENT/SYMBOL
    #CORE FORMULA: RISK_AMOUNT/(ENTRY_PRICE - STOP_LOSS) * CONTRACT_SIZE
    contract_size = INSTRUMENT_SPECS[trade.symbol]["contract_size"]
    risk_distance = abs(trade.entry_price - trade.stop_loss)
    risk_amount = trade.account_balance * (trade.risk_percent/100)

    return round(risk_amount / (risk_distance * contract_size), 2)

def get_valid_float(prompt, min_value=None, max_value=None, extend=None):
    #WE CREATE A HELPER FUNCTION THAT GETS A VALID FLOAT.
    #THIS FUNCTION IS NOW CALLED INSIDE GET_USER_INPUT HENCE GUARRANTEES FLOATS.
    while True:
        raw = input(prompt)
        try:
            value = float(raw)
        except ValueError:
            print("ENTER A NUMERIC VALUE.")
            continue

        if value <= 0:
            print("VALUE CAN'T BE LESS THAN OR EQUAL TO ZERO.")
            continue
        if min_value is not None and value < min_value:
            print(f"VALUE CAN'T BE LESS THAN {min_value}")
            continue
        if max_value is not None and value > max_value:
            print(f"VALUE CAN'T BE GREATER THAN {max_value}")
            continue
        if extend is not None and value in extend:
            print("THIS VALUE CAN'T BE LESS THAN THE PREVIOUS VALUE.")
            continue

        return value

def get_user_input(symbol, direction):
    #DATA FROM USER: ENTRY_PRICE, EXIT_PRICE, STOP_LOSS, TAKE_PROFIT, SYMBOL, RISK_PERCENT
    #ACCOUNT_BALANCE, LOT_SIZE
    entry_price = get_valid_float("ENTRY PRICE: ")
    exit_price = get_valid_float("EXIT PRICE: ")
    stop_loss = get_valid_float("STOP LOSS: ", extend=[entry_price])
    take_profit = get_valid_float("TAKE PROFIT: ", extend=[entry_price])
    risk_percent = get_valid_float("RISK PERCENT: ", max_value=100)
    account_balance = get_valid_float("ACCOUNT BALANCE: ")

    if INSTRUMENT_SPECS[symbol]["type"] == "futures":
        lot_size = get_valid_float("CONTRACTS: ", min_value=1)
    else:
        lot_size = get_valid_float("LOT SIZE: ")

    return TradeSetup(
        entry_price = entry_price,
        exit_price = exit_price,
        stop_loss = stop_loss,
        take_profit = take_profit,
        account_balance = account_balance,
        risk_percent = risk_percent,
        lot_size = lot_size,
        symbol = symbol,
        direction = direction
    )

def get_instrument_symbol():
    valid_instruments = ["NQ", "ES", "XAUUSD", "XAGUSD"]
    while True:
        symbol = input("ENTER THE INSTRUMENT SYMBOL: ").upper().strip()
        if symbol in valid_instruments:
            return symbol
        else:
            continue

if __name__ == "__main__":
    main()
