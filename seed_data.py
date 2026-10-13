import pandas as pd

#DECLARATIVE TABLE DATA FOR SEED DATA IDEMPOTENCY FOR STATIC LOOKUP TABLES.
models: list[tuple[str, str]] = [
    ('BREAD AND BUTTER MODEL', 'REVERSAL OR CONTINUATION USING WEEKLY AND DAILY PROFILES. ENTRY FRAMED ON CISD ORDERBLOCK LIMIT ENTRY.'),  # noqa: E501
    ('ONE SHOT ONE KILL', 'USE ICT WEEKLY PROFILES TO NARROW DOWN REVERSAL DAY OF THE WEEK. ENTRY ON PREMIUM/DISCOUNT PD ARRAYS.'),  # noqa: E501
    ('2022 FVG MODEL', 'STOP RAID IN OPPOSITE DIRECTION OF DAILY BIAS. MARKET STRUCTURE SHIFT. ENTRY ON FIRST FVG AFTER REVERSAL.'),  # noqa: E501
    ('ERL TO IRL MODEL', 'PRICE TRADES BELOW OLD LOW (ERL) LEADING TO A MOVE HIGHER INTO FVG (IRL). ENTRY USING LTF CISD PATTERN.'),  # noqa: E501
    ('NO MODEL USED', 'NO TRADING MODEL WAS USED FOR THIS TRADE. IT WAS A YOLO TRADE AKA A GHOST TRADE. INSTANT F GRADE.'),  # noqa: E501
]

entry_execution: list[tuple[str, str, int, str]] = [
    ('THE ALGORITHM', 'EXECUTED THE PLAN WITH MACHINE LIKE PRECISION. USED A LIMIT ORDER AT THE CISD/IFVG LEVEL THEN WAITED PATIENTLY.', 5, 'A+'),  # noqa: E501
    ('THE RESILIENT', 'KNEW THE LEVEL BUT FEARED MISSING THE MOVE. USED A MARKETORDER CLOSE TO EXACT LEVEL DUE TO IMPATIENCE', 4, 'B'),  # noqa: E501
    ('SLOPPY ANALYST', 'ENTERED THE RIGHT ZONE BUT THE WRONG PRICE. MISSED OPTIMAL PRICE DUE TO TECHNICAL ISSUES', 3, 'C'),  # noqa: E501
    ('THE GAMBLER', 'ABANDONED THE PLAN DUE TO EMOTION. ENTERED WITH A MARKETORDER DUE TO FOMO OR REVENGE TRADING.', 2, 'D'),  # noqa: E501
    ('THE REBEL', 'TRADED AGAINST THE MODEL ENTIRELY. TRADE ENTRY DOESNT CORRESPOND TO ANY MODEL OR LEVEL. GHOST TRADE', 1, 'F'),  # noqa: E501
]

trade_management: list[tuple[str, str, int, str]] = [
    ('THE ZEN MASTER', 'SET THE ORDER AND PHYSICALLY WALKED AWAY. NO CHART WATCHING. 1 HOUR CHECK IN RULE WAS FOLLOWED PERFECTLY', 5, 'A+'),  # noqa: E501
    ('THE RESILIENT', 'FELT STRONG URGE TO CHECK AND MICROMANAGE. OPENED CHART BRIEFLY BUT QUICKLY CLOSED WITHOUT TOUCHING ORDERS', 4, 'B'),  # noqa: E501
    ('TORTURED ARTIST', 'WATCHED CHART ENTIRE TIME FEELING STRESS AND FEAR. DEBATED CLOSING ORDERS BUT DID NOT. MENTALLY EXAUSTING TRADE', 3, 'C'),  # noqa: E501
    ('MICROMANAGER', 'SUCCUMBED TO FEAR OR GREED. ACTIVELY MANAGED AND INTERFERED WITH THE LIMIT ORDERS. BROKE 1 HOUR RULE', 2, 'D'),  # noqa: E501
    ('THE SABOTEUR','COMPLETELY ABANDONED THE PLAN. DELETED THE TRADE BEFORE TP/SL OR EVEN REVERSED THE POSITION. PSYCHOLOGICAL BREAKDOWN', 1, 'F'),  # noqa: E501
]

parameter_values: list[tuple[str]] = [
    ('LIQUIDITY RAID ON BUYSTOPS/SELLSTOPS ABOVE OR BELOW MARKET PRICE.',),
    ('DISPLACEMENT TO THE OPPOSITE DIRECTION.',),
    ('CISD CLOSE AND/OR MARKET STRUCTURE SHIFT.',),
    ('TRADE SETUP MUST OCCUR WITHIN 7 AM TO 12 NOON NEW YORK SESSION.',),
    ('SETUP DIRECTION MUST ALIGN WITH HIGHER TIMEFRAME BIAS.',),
    ('SELL ABOVE MIDNIGHT OPENING PRICE, BUY BELOW MIDNIGHT OPENING PRICE.',),
    ('SELL AT A PREMIUM, BUY AT A DISCOUNT.',)
]

accounts = [
    ('GFT 5K FUNDED ACCOUNT', 'FUNDED CHALLENGE', None, 5000, 1),
    ('GFT 10K PAY LATER CHALLENGE', 'FUNDED CHALLENGE', None, 10000, 1),
    ('FBS LIVE ACCOUNT', 'PERSONAL LIVE', 'FBS BROKER,', 1000, 0),
]

parameters = [
    'LIQUIDITY RAID ON BUYSTOPS/SELLSTOPS ABOVE OR BELOW MARKET PRICE.',
    'DISPLACEMENT TO THE OPPOSITE DIRECTION.',
    'CISD CLOSE AND/OR MARKET STRUCTURE SHIFT.',
    'TRADE SETUP MUST OCCUR WITHIN 7 AM TO 12 NOON NEW YORK SESSION.',
    'SETUP DIRECTION MUST ALIGN WITH HIGHER TIMEFRAME BIAS.',
    'SELL ABOVE MIDNIGHT OPENING PRICE, BUY BELOW MIDNIGHT OPENING PRICE.',
    'SELL AT A PREMIUM, BUY AT A DISCOUNT.'
]

#FORMATTING ISSUES SHOULDN'T BE RAISING ERRORS LIKE ATTRIBUTEERROR, FIND A FIX
column_names = [
    "entry_price", "exit_price", "take_profit", "stop_loss", "position_size",
    "entry_time", "exit_time", "date", "management_id", "entry_execution", "asset",
    "direction", "account_balance", "risk_percent"]

accounts_df = pd.DataFrame([(index,) + row for index, row in enumerate(accounts, start=1)],  # noqa: RUF005
            columns=["account_id", "account_name", "account_type", "broker", "starting_balance", "is_active"])

models_df = pd.DataFrame([(index,) + row for index, row in enumerate(models, start=1)],  # noqa: RUF005
             columns=["model_id", "model_name", "model_description"])

entry_execution_df = pd.DataFrame([(index,) + row for index, row in enumerate(entry_execution, start=1)],   # noqa: RUF005
             columns=["id", "archetype", "description", "points", "grade"])

trade_management_df = pd.DataFrame([(index,) + row for index, row in enumerate(trade_management, start=1)],  # noqa: RUF005
             columns=["id", "archetype", "description", "points", "grade"])

parameters_df = pd.DataFrame([(index,) + row for index, row in enumerate(parameter_values, start=1)],  # noqa: RUF005
             columns=["parameter_id", "parameter_name"])

#DICTIONARY MAPPING OF IDS TO NAMES AND ARCHETYPES
#FOR FORMAT_FUNC PARAMETER FORMATTING IN THE STREAMLIT TRADE DETAILS FORM
models_options = models_df.set_index("model_id")["model_name"].to_dict()
account_options = accounts_df.set_index("account_id")["account_name"].to_dict()
entry_execution_options = entry_execution_df.set_index("id")["archetype"].to_dict()
trade_management_options = trade_management_df.set_index("id")["archetype"].to_dict()
