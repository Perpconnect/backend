from fastapi import APIRouter, HTTPException
import requests

from schemas.TokenBalance import TokenBalance

router = APIRouter()


@router.get("/tokens/{chain}/{address}")
async def tokens(chain: int, address: str) -> [TokenBalance]:

    # Error response.
    if chain == 1:
        raise HTTPException(
            status_code=505, detail="Ethereum mainnet is not currently supported."
        )

    url = "https://blockscout.com/xdai/mainnet/api?module=account&action=tokenlist&address={}".format(
        address
    )
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers)

    all_tokens = []

    for token in response.json()["result"]:
        if token["type"] != "ERC-20":
            continue
        balance = TokenBalance(
            balance=token["balance"],
            contractAddress=token["contractAddress"],
            decimals=token["decimals"],
            name=token["name"],
            symbol=token["symbol"],
            type=token["type"],
            logo_url="https://cryptoicons.org/api/icon/{}/200".format(token["symbol"]),
        )

        all_tokens.append(balance)

    return all_tokens
