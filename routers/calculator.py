from typing import Any

from fastapi import APIRouter, status

import services as s
from http_errors import to_http_error
from schemas import CalculatorInputs, CalculatorResultsResponse, LotSizeInputs, LotSizeResponse

router = APIRouter()

@router.post(
        path="/trade-metrics",
        response_model=CalculatorResultsResponse,
        status_code=status.HTTP_201_CREATED,
)
def calculate_trade_metrics(inputs: CalculatorInputs):
    results: s.CalculatorResults = s.run_calculator(setup_values=inputs.model_dump())

    if not results.success:
        raise to_http_error(exc=results.error)

    profit_loss: dict[str, Any] = results.profit_loss # pyright: ignore[reportAssignmentType]
    risk_reward: dict[str, float] = results.risk_reward # pyright: ignore[reportAssignmentType]

    calculator_results = {}
    result = profit_loss["RESULT"]
    rr_multiple = risk_reward["RR_MULTIPLE"]
    risk_percent = risk_reward["RISK_PERCENT"]
    risk_amount = risk_reward["RISK_AMOUNT"]
    reward_amount = risk_reward["REWARD_AMOUNT"]
    dollar_amount = profit_loss["DOLLAR_AMOUNT"]
    dollar_percent = profit_loss["DOLLAR_PERCENT"]

    calculator_results["result"] = result
    calculator_results["rr_multiple"] = rr_multiple
    calculator_results["risk_percent"] = risk_percent
    calculator_results["risk_amount"] = risk_amount
    calculator_results["reward_amount"] = reward_amount
    calculator_results["dollar_amount"] = dollar_amount
    calculator_results["dollar_percent"] = dollar_percent

    return calculator_results

@router.post(
        path="/position-size",
        response_model=LotSizeResponse,
        status_code=status.HTTP_201_CREATED,
)
def calculate_lot_size(inputs: LotSizeInputs) -> LotSizeResponse:
    results: s.PositionSizingInput = s.position_sizing(position_sizing_inputs=inputs.model_dump())

    if not results.success:
        raise to_http_error(exc=results.error)

    lot_size: float | int = results.position_size # pyright: ignore[reportAssignmentType]

    return LotSizeResponse(lot_size= lot_size)
