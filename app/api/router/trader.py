import os
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from web3 import Web3
from typing import List
import requests


from schemas.Trader import TraderAddress, Portfolio
from api.utils.trader import formatUnits, formatEther, SPOT_PRICE, getLiquidationPrice

trader_route = APIRouter()

BASE_PATH = "api/artifacts/portfolio/"
STAGE_NAME = "production"
ONE_ETH = 10 ** 18
ETHEREUM_PROVIDER_INFURA = os.getenv("ETHEREUM_PROVIDER_INFURA")
metadata_url = f"https://metadata.perp.exchange/{STAGE_NAME}.json"
config_url = f"https://metadata.perp.exchange/config.{STAGE_NAME}.json"


def read_artifacts(fname: str):
    with open(BASE_PATH + fname) as f:
        return json.load(f)


def fetch_data(url: str) -> dict:
    resp = requests.get(url)
    return resp.json()


def getLayer1Provider():
    return Web3(Web3.WebsocketProvider(ETHEREUM_PROVIDER_INFURA))


def getLayer2Provider(config):
    wsUrlFromConfig = config["L2_WEB3_ENDPOINTS"][0]["url"]
    if wsUrlFromConfig:
        return Web3(Web3.WebsocketProvider(wsUrlFromConfig))


def getProvider(layer, config=None):
    if layer == "layer1":
        return getLayer1Provider()
    if layer == "layer2":
        return getLayer2Provider(config)
    else:
        raise Exception("provider not exists")


def getContract(address, abi, provider):
    return provider.eth.contract(address=address, abi=abi)


def bytes_to_str(value):
    value = value.hex().rstrip("0")
    if len(value) % 2 != 0:
        value = value + "0"
    return bytes.fromhex(value).decode("utf8")


TetherTokenArtifact = read_artifacts("TetherToken.json")
AmmArtifact = read_artifacts("AmmArtifact.json")
InsuranceFundArtifact = read_artifacts("InsuranceFundArtifact.json")
ClearingHouseArtifact = read_artifacts("ClearingHouseArtifact.json")
ClearingHouseViewerArtifact = read_artifacts("ClearingHouseViewerArtifact.json")


metadata = fetch_data(url=metadata_url)
config = fetch_data(url=config_url)

layer1provider = getProvider("layer1")
layer2provider = getProvider("layer2", config)
layer2Contracts = metadata["layers"]["layer2"]["contracts"]

layer1_address = metadata["layers"]["layer1"]["externalContracts"]["usdc"]
layer1_address = Web3.toChecksumAddress(layer1_address)

layer1Usdc = getContract(
    layer1_address,
    TetherTokenArtifact,
    layer1provider,
)

layer2Usdc = getContract(
    metadata["layers"]["layer2"]["externalContracts"]["usdc"],
    TetherTokenArtifact,
    layer2provider,
)

insuranceFund = getContract(
    layer2Contracts["InsuranceFund"]["address"],
    InsuranceFundArtifact,
    layer2provider,
)

clearingHouse = getContract(
    layer2Contracts["ClearingHouse"]["address"],
    ClearingHouseArtifact,
    layer2provider,
)

clearingHouseViewer = getContract(
    layer2Contracts["ClearingHouseViewer"]["address"],
    ClearingHouseViewerArtifact,
    layer2provider,
)

decimal = layer2Usdc.functions.decimals().call()
symbol = layer2Usdc.functions.symbol().call()
ammAddressList = insuranceFund.functions.getAllAmms().call()


def get_portfolio(trader_addr: str) -> List[Portfolio]:
    all_meta = []
    for addr in ammAddressList:
        pos = clearingHouseViewer.functions.getPersonalPositionWithFundingPayment(
            addr, trader_addr
        ).call()

        (
            size,
            margin,
            openNotional,
            lastUpdatedCumulativePremiumFraction,
            liquidityHistoryIndex,
            blockNumber,
        ) = pos

        size = size[0]
        if not size:
            continue

        margin = margin[0]
        openNotional = openNotional[0]
        lastUpdatedCumulativePremiumFraction = lastUpdatedCumulativePremiumFraction[0]

        amm = getContract(addr, AmmArtifact, layer2provider)
        priceFeedKey = amm.functions.priceFeedKey().call()
        priceFeedKey = bytes_to_str(priceFeedKey)

        marginRatio = clearingHouseViewer.functions.getMarginRatio(
            addr, trader_addr
        ).call()
        marginRatio = marginRatio[0]
        quote = amm.functions.quoteAssetReserve().call()
        base = amm.functions.baseAssetReserve().call()
        k = formatEther(quote * base)
        posNotionalNPnl = clearingHouse.functions.getPositionNotionalAndUnrealizedPnl(
            addr,
            trader_addr,
            SPOT_PRICE,
        ).call()

        positionNotional, unrealizedPnl = posNotionalNPnl
        positionNotional = positionNotional[0]
        unrealizedPnl = unrealizedPnl[0]

        leverage = (positionNotional * ONE_ETH) / (margin + unrealizedPnl)
        MAINTENANCE_MARGIN_RATIO = (ONE_ETH * 625) / 10000

        liquidationPrice = getLiquidationPrice(
            leverage=leverage,
            margin=margin,
            openNotional=openNotional,
            positionSize=size,
            mmr=MAINTENANCE_MARGIN_RATIO,
            k=k,
        )

        resp = {
            "ammAddress": addr,
            "symbol": symbol,
            "pairName": f"{priceFeedKey}/{symbol}",
            "size": formatEther(size),
            "margin": formatEther(margin),
            "margin_ratio": formatEther(marginRatio * 100),
            "leverage": formatEther(leverage),
            "liq_price": formatEther(liquidationPrice),
            "open_notional": formatEther(openNotional),
            "PnL": formatEther(unrealizedPnl),
            "last_open_at_block": blockNumber,
        }
        all_meta.append(resp)
    return all_meta


@trader_route.post("/portfolio", response_model=List[Portfolio])
def portfolio(trader: TraderAddress):
    trader_address = trader.address
    if not trader_address:
        raise HTTPException(status_code=400, detail="No address found.")

    trader = Web3.toChecksumAddress(trader_address)
    if not trader:
        raise HTTPException(status_code=400, detail="Invalid trader address.")

    portfolio = get_portfolio(trader_addr=trader)
    if not portfolio:
        raise HTTPException(status_code=400, detail="No results found.")
    return portfolio


@trader_route.post("/balance")
def get_balance(trader: TraderAddress):
    trader_address = trader.address
    if not trader_address:
        raise HTTPException(status_code=400, detail="No address found.")

    trader = Web3.toChecksumAddress(trader_address)
    if not trader:
        raise HTTPException(status_code=400, detail="Invalid trader address.")

    raw_layer1_balance = layer1Usdc.functions.balanceOf(trader).call()
    raw_layer2_balance = layer2Usdc.functions.balanceOf(trader).call()
    layer1Balance = formatUnits(balance=raw_layer1_balance, decimals=decimal)
    layer2Balance = formatUnits(balance=raw_layer2_balance, decimals=decimal)
    return JSONResponse(
        content={
            "Layer 1": f"{layer1Balance} {symbol}",
            "Layer 2": f"{layer2Balance} {symbol}",
        }
    )
