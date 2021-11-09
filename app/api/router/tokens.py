from fastapi import APIRouter, HTTPException
import requests

from typing import List
from schemas.TokenBalance import TokenBalance

router = APIRouter()


@router.get("/tokens/{chain}/{address}")
async def tokens(chain: int, address: str) -> List[TokenBalance]:

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
            logo_url="https://logos.covalenthq.com/tokens/{}.png".format(
                token["contractAddress"]
            ),
            usd=str(int(token["balance"]) / pow(10, int(token["decimals"]))),
        )

        all_tokens.append(balance)

    if all_tokens == []:
        all_tokens.append(
            TokenBalance(
                balance="0",
                contractAddress="0xfc8b2690f66b46fec8b3ceeb95ff4ac35a0054bc",
                decimals="18",
                name="Dai Token on xDai",
                symbol="DAI",
                type="ERC-20",
                logo_url="https://cryptoicons.org/api/icon/DAI/200",
                usd="0.0",
            )
        )
    return all_tokens
