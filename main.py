
class Trade:
    def __init__(self, entry_price, exit_price, stop_loss, take_profit, account_balance, risk_percent, lot_size, symbol, direction):
        self.entry_price = entry_price
        self.exit_price = exit_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.account_balance = account_balance
        self.risk_percent = risk_percent
        self.lot_size = lot_size
        self.symbol = symbol
        self.direction = direction

    def calculate_risk_reward_ratio(self):
        contract_size = 100
        reward_distance = abs(self.take_profit - self.entry_price)
        risk_distance = abs(self.stop_loss - self.entry_price)

        risk_amount = risk_distance * self.lot_size * contract_size
        reward_amount = reward_distance * self.lot_size * contract_size

        rr_ratio = round(reward_distance / risk_distance, 2)

        return {
            "RR_RATIO" : rr_ratio,
            "RISK_AMOUNT" : round(risk_amount, 2),
            "REWARD_AMOUNT" : round(reward_amount, 2)
        }


trade_1 = Trade(3345.67, 3378.98, 3330.25, 3378.98, 50000, 2, 0.1, "XAUUSD", "long")
trade_2 = Trade(4567.55, 4325.78, 4580.34, 4325.78, 50000, 5, 0.8, "XAUUSD", "short")
print(trade_1.calculate_risk_reward_ratio())
print(trade_2.calculate_risk_reward_ratio())