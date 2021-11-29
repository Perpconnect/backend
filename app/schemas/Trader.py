from pydantic import BaseModel


class TraderAddress(BaseModel):
    address: str


class Portfolio(BaseModel):
    ammAddress: str
    symbol: str
    pairName: str
    size: float
    margin: float
    margin_ratio: float
    leverage: float
    liq_price: float
    open_notional: float
    PnL: float
    last_open_at_block: float

class Market(BaseModel):
    ammAddress: str
    symbol: str
    pairName: str
    markPrice: str
    indexPrice: str
    imageUrl: str
    fundingRate: str
