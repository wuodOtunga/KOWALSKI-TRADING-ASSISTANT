from dataclasses import dataclass

@dataclass
class Trade:
    entry_price : float
    exit_price : float
    take_profit : float
    stop_loss : float
    