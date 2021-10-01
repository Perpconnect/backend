from fastapi import APIRouter, HTTPException
from enum import Enum

router = APIRouter()

class Chain(Enum):
    xDai = 64
    mainnet = 1

@router.post('/tokens/{chain}/{address}')
async def get_tokens(chain: Chain, address: str):

    res = "fesjb"

    # Error response.
    if chain == Chain.mainnet: raise HTTPException(status_code=505, detail="Ethereum mainnet is not currently supported.")

    # Return User Data.
    return address
