from pydantic import BaseModel


class TokenBalance(BaseModel):
    balance: str
    contractAddress: str
    decimals: str
    name: str
    symbol: str
    type: str
    logo_url: str
    usd: str
