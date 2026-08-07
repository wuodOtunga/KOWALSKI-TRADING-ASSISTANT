PRAGMA foreign_keys = ON;

--ADD DURATION, RESULT TO THE CALCULATED/DERIVED COLUMNS.
CREATE TABLE IF NOT EXISTS "trades" (
    "trade_id" INTEGER,
    "entry_price" NUMERIC NOT NULL,
    "exit_price" NUMERIC NOT NULL,
    "take_profit" NUMERIC NOT NULL,
    "stop_loss" NUMERIC NOT NULL,
    "position_size" REAL NOT NULL,
    "entry_time" TEXT NOT NULL,
    "exit_time" TEXT NOT NULL,
    "date" TEXT NOT NULL,
    "model_id" INTEGER NOT NULL,
    "account_id" INTEGER NOT NULL,
    "management_id" INTEGER NOT NULL,
    "entry_execution_id" INTEGER NOT NULL,

    "asset" TEXT NOT NULL CHECK("asset" IN ('XAUUSD', 'XAGUSD', 'NQ', 'ES')),
    "direction" TEXT NOT NULL CHECK("direction" IN ('long', 'short')),

    "dollar_amount" NUMERIC,  --calculated from trading_calculator.py
    "duration" NUMERIC, --calculated from trading_calculator.py
    "result" NUMERIC,    --calculated from trading_calculator.py
    "rr_multiple" NUMERIC,       --calculated from trading_calculator.py
    "overall_trade_grade" TEXT CHECK("overall_trade_grade" IN ('A+', 'B', 'C', 'D', 'F') OR "overall_trade_grade" IS NULL),
    
    PRIMARY KEY("trade_id"),
    FOREIGN KEY("model_id") REFERENCES "models"("model_id"),
    FOREIGN KEY("account_id") REFERENCES "accounts"("account_id"),
    FOREIGN KEY("management_id") REFERENCES "trade_management"("management_id"),
    FOREIGN KEY("entry_execution_id") REFERENCES "entry_execution"("entry_execution_id")
);

--STATIC REFERENCE TABLE
--STORED ONCE NEVER TOUCHED AGAIN
CREATE TABLE IF NOT EXISTS "models" (
    "model_id" INTEGER,
    "model_name" TEXT NOT NULL UNIQUE,
    "description" TEXT,
    PRIMARY KEY("model_id")
);

INSERT INTO "models" ("model_name", "description") VALUES 
('BREAD AND BUTTER MODEL', NULL),
('ONE SHOT ONE KILL MODEL', NULL),
('2022 FVG MODEL', NULL),
('NO MODEL USED', NULL);

--STATIC REFERENCE LOOKUP TABLE
--STORED ONCE NEVER TOUCHED AGAIN
CREATE TABLE IF NOT EXISTS "entry_execution" (
    "entry_execution_id" INTEGER,
    "archetype" TEXT NOT NULL UNIQUE,
    "description" TEXT,
    "points" INTEGER NOT NULL CHECK("points" BETWEEN 1 AND 5),
    "grade" TEXT NOT NULL CHECK("grade" IN ("A+", "B", "C", "D", "F")),
    PRIMARY KEY("entry_execution_id")
);

INSERT INTO "entry_execution" ("archetype", "description", "points", "grade") VALUES
('THE ALGORITHM', 'EXECUTED THE PLAN WITH MACHINE LIKE PRECISION. USED A LIMIT ORDER AT THE CISD/IFVG LEVEL THEN WAITED PATIENTLY.', 5, 'A+'),
('IMPATIENT BUT DISCIPLINED', 'KNEW THE LEVEL BUT FEARED MISSING THE MOVE. USED A MARKETORDER CLOSE TO EXACT LEVEL DUE TO IMPATIENCE', 4, 'B'),
('SLOPPY ANALYST', 'ENTERED THE RIGHT ZONE BUT THE WRONG PRICE. MISSED OPTIMAL PRICE DUE TO TECHNICAL ISSUES', 3, 'C'),
('THE GAMBLER', 'ABANDONED THE PLAN DUE TO EMOTION. ENTERED WITH A MARKETORDER DUE TO FOMO OR REVENGE TRADING.', 2, 'D'),
('THE REBEL', 'TRADED AGAINST THE MODEL ENTIRELY. TRADE ENTRY DOESNT CORRESPOND TO ANY MODEL OR LEVEL. GHOST TRADE', 1, 'F');

--STATIC REFERENCE LOOKUP TABLE
--STORED ONCE NEVER TOUCHED AGAIN
CREATE TABLE IF NOT EXISTS "trade_management" (
    "management_id" INTEGER,
    "archetype" TEXT NOT NULL UNIQUE,
    "description" TEXT,
    "points" INTEGER NOT NULL CHECK("points" BETWEEN 1 AND 5),
    "grade" TEXT NOT NULL CHECK("grade" IN ('A+', 'B', 'C', 'D', 'F')),
    PRIMARY KEY("management_id")
);

INSERT INTO "trade_management" ("archetype", "description", "points", "grade") VALUES
('THE ZEN MASTER', 'SET THE ORDER AND PHYSICALLY WALKED AWAY. NO CHART WATCHING. 1 HOUR CHECK IN RULE WAS FOLLOWED PERFECTLY', 5, 'A+'),
('THE RESILIENT', 'FELT STRONG URGE TO CHECK AND MICROMANAGE. OPENED CHART BRIEFLY BUT QUICKLY CLOSED WITHOUT TOUCHING ORDERS', 4, 'B'),
('TORTURED ARTIST', 'WATCHED CHART ENTIRE TIME FEELING STRESS AND FEAR. DEBATED CLOSING ORDERS BUT DID NOT. MENTALLY EXAUSTING TRADE', 3, 'C'),
('MICROMANAGER', 'SUCCUMBED TO FEAR OR GREED. ACTIVELY MANAGED AND INTERFERED WITH THE LIMIT ORDERS. BROKE 1 HOUR RULE', 2, 'D'),
('THE SABOTEUR','COMPLETELY ABANDONED THE PLAN. DELETED THE TRADE BEFORE TP/SL OR EVEN REVERSED THE POSITION. PSYCHOLOGICAL BREAKDOWN', 1, 'F');

CREATE TABLE IF NOT EXISTS "accounts" (
    "account_id" INTEGER,
    "account_name" TEXT NOT NULL,
    "account_type" TEXT NOT NULL CHECK("account_type" IN ('FUNDED CHALLENGE', 'FUNDED LIVE', 'PERSONAL LIVE')),
    "broker" TEXT,
    "starting_balance" NUMERIC NOT NULL,
    "is_active" BOOLEAN NOT NULL DEFAULT 1,
    PRIMARY KEY("account_id")
);

--STATIC REFERENCE LOOKUP TABLE
CREATE TABLE IF NOT EXISTS "parameters" (
    "parameter_id" INTEGER,
    "parameter_name" TEXT NOT NULL UNIQUE,
    PRIMARY KEY("parameter_id")
);

INSERT INTO "parameters" ("parameter_name") VALUES
('LIQUIDITY RAID ON BUYSTOPS/SELLSTOPS ABOVE OR BELOW MARKET PRICE.'),
('DISPLACEMENT TO THE OPPOSITE DIRECTION.'),
('CISD CLOSE AND/OR MARKET STRUCTURE SHIFT.'),
('TRADE SETUP MUST OCCUR WITHIN 7 AM TO 12 NOON NEW YORK SESSION.'),
('SETUP DIRECTION MUST ALIGN WITH HIGHER TIMEFRAME BIAS.'),
('SELL ABOVE MIDNIGHT OPENING PRICE, BUY BELOW MIDNIGHT OPENING PRICE.'),
('SELL AT A PREMIUM, BUY AT A DISCOUNT.'),
('EXECUTION GRADE > B. PRE TRADE + AVG(ENTRY EXECUTION AND TRADE MANAGEMENT).');

--JUNCTION TABLE SHOWING RELATIONSHIP BETWEEN TRADES AND PARAMETERS
CREATE TABLE IF NOT EXISTS "trade_parameters" (
    "trade_id" INTEGER,
    "parameter_id" INTEGER,
    PRIMARY KEY ("trade_id", "parameter_id"),
    FOREIGN KEY("trade_id") REFERENCES "trades"("trade_id"),
    FOREIGN KEY("parameter_id") REFERENCES "parameters"("parameter_id")
);

CREATE TABLE IF NOT EXISTS "trade_notes" (
    "trade_id" INTEGER,
    "emotions" TEXT NOT NULL,
    "mistakes" TEXT NOT NULL,
    "thoughts" TEXT NOT NULL,
    PRIMARY KEY("trade_id"),
    FOREIGN KEY("trade_id") REFERENCES "trades"("trade_id")
);

CREATE TABLE IF NOT EXISTS "charts" (
    "chart_id" INTEGER,
    "trade_id" INTEGER,
    "filepath" TEXT NOT NULL,
    "timeframe" TEXT NOT NULL CHECK("timeframe" in ("4H", "1H", "5M")),
    PRIMARY KEY("chart_id"),
    FOREIGN KEY("trade_id") REFERENCES "trades"("trade_id")
);
