import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from web3 import Web3
from typing import List
import os

from schemas.Trader import TraderAddress, Portfolio, MarketAddress
from api.utils.trader import (
    formatUnits,
    formatEther,
    SPOT_PRICE,
    getLiquidationPrice,
    big2BigNum,
    bigNum2Big,
)
from api.constant import (
    ONE_ETH,
    METADATA_URL,
    CONFIG_URL,
    LAYER1,
    LAYER2,
    DEFAULT_LAYER2_GAS_PRICE,
)
from api.utils.contract import (
    read_artifacts,
    get_template,
    fetch_data,
    get_provider,
    get_contract,
    bytes_to_str,
)
from api.exec.clearing_house import openPosition

trader_route = APIRouter()


TetherTokenArtifact = read_artifacts("TetherToken.json")
AmmArtifact = read_artifacts("AmmArtifact.json")
InsuranceFundArtifact = read_artifacts("InsuranceFundArtifact.json")
ClearingHouseArtifact = read_artifacts("ClearingHouseArtifact.json")
ClearingHouseViewerArtifact = read_artifacts("ClearingHouseViewerArtifact.json")


metadata = fetch_data(url=METADATA_URL)
config = fetch_data(url=CONFIG_URL)

layer1provider = get_provider("layer1")
layer2provider = get_provider("layer2", config)
layer2Contracts = metadata["layers"]["layer2"]["contracts"]

layer1_address = metadata["layers"]["layer1"]["externalContracts"]["usdc"]
layer1_address = Web3.toChecksumAddress(layer1_address)

layer1Usdc = get_contract(
    layer1_address,
    TetherTokenArtifact,
    layer1provider,
)

layer2Usdc = get_contract(
    metadata["layers"]["layer2"]["externalContracts"]["usdc"],
    TetherTokenArtifact,
    layer2provider,
)

insuranceFund = get_contract(
    layer2Contracts["InsuranceFund"]["address"],
    InsuranceFundArtifact,
    layer2provider,
)

clearingHouse = get_contract(
    layer2Contracts["ClearingHouse"]["address"],
    ClearingHouseArtifact,
    layer2provider,
)

clearingHouseViewer = get_contract(
    layer2Contracts["ClearingHouseViewer"]["address"],
    ClearingHouseViewerArtifact,
    layer2provider,
)

decimal = layer2Usdc.functions.decimals().call()
symbol = layer2Usdc.functions.symbol().call()
ammAddressList = insuranceFund.functions.getAllAmms().call()
tokenSymbolMap = {}


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

        amm = get_contract(addr, AmmArtifact, layer2provider)
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


@trader_route.post("/market")
async def market(address: MarketAddress):
    address = address.address
    amm_addresses = ammAddressList  # master address_list, do not change.
    if address:
        check_valid = Web3.toChecksumAddress(address)
        if not check_valid:
            raise HTTPException(status_code=400, detail="Invalid market address.")
        amm_addresses = [address]

    results = []
    for addr in amm_addresses:
        amm = get_contract(addr, AmmArtifact, layer2provider)
        priceFeedKey = amm.functions.priceFeedKey().call()
        priceFeedKey = bytes_to_str(priceFeedKey)
        quoteAssetAddress = amm.functions.quoteAsset().call()

        symbol = tokenSymbolMap.get(quoteAssetAddress)
        if not symbol:
            token = get_contract(quoteAssetAddress, TetherTokenArtifact, layer2provider)
            symbol = token.functions.symbol().call()
            tokenSymbolMap[quoteAssetAddress] = symbol

        marketPrice = amm.functions.getSpotPrice().call()
        marketPrice = marketPrice[0]
        marketPrice = formatEther(marketPrice)

        indexPrice = amm.functions.getUnderlyingPrice().call()
        indexPrice = indexPrice[0]
        indexPrice = formatEther(indexPrice)

        time_now = datetime.datetime.now()
        durationFromSharp = time_now.minute * 60
        twapPrice = amm.functions.getTwapPrice(durationFromSharp).call()
        twapPrice = twapPrice[0]
        underlyingTwapPrice = amm.functions.getUnderlyingTwapPrice(
            durationFromSharp
        ).call()
        underlyingTwapPrice = underlyingTwapPrice[0]
        fundingPeriod = amm.functions.fundingPeriod().call()

        # marketPrice = formatEther(marketPrice)
        oneDayInSec = 60 * 60 * 24
        marketTwapPrice = bigNum2Big(twapPrice)
        indexTwapPrice = bigNum2Big(underlyingTwapPrice)

        premium = marketTwapPrice - indexTwapPrice
        premiumFraction = (premium * fundingPeriod) / oneDayInSec

        final_funding_rate = premiumFraction / indexTwapPrice
        final_funding_rate = big2BigNum(final_funding_rate)
        final_funding_rate = formatEther(final_funding_rate) * 100
        results.append(
            {
                "markPrice": str(marketPrice),
                "fundingRate": str(final_funding_rate),
                "indexPrice": str(indexPrice),
                "ammAddress": addr,
                "pairName": f"{priceFeedKey}/{symbol}",
                "symbol": symbol,
            }
        )

    if not results:
        raise HTTPException(status_code=400, detail="No results found.")
    return results


actions = get_template("open_position.json")


def open_position():
    # The use of the Mnemonic features of Account is disabled by default until its API stabilizes.
    # Web3().eth.account.enable_unaudited_hdwallet_features()
    private_key = os.getenv("PRIVATE_KEY")
    wallet = Web3().eth.account.privateKeyToAccount(private_key)

    # signed_message = w3.eth.account.sign_message(message, private_key=private_key)
    for a in actions:
        functionName = a["action"]
        layer = LAYER2
        gasPrice = DEFAULT_LAYER2_GAS_PRICE
        options = {"gasPrice": gasPrice, "gasLimit": None, "nonce": None}
        openPosition(
            layer2Contracts,
            layer2provider,
            wallet,
            layer2Usdc,
            a["args"],
            options,
        )
