import math

from web3 import Web3

SPOT_PRICE = 0

DIGIT_OF_ETH = 18


def formatUnits(balance, decimals):
    multiplier = 10 ** decimals
    return balance / multiplier


def formatEther(value):
    isNegative = value < 0
    if isNegative:
        # Convert to positive value as `fromWei` doesn't take negative values.
        value = value * -1
    value = Web3.fromWei(value, "ether")
    if isNegative:
        # return the value as -ve
        value = -abs(value)
    return value


def bigNum2Big(val, decimals=DIGIT_OF_ETH):
    return float(val) / float(math.pow(10, decimals))


def big2BigNum(val, decimals=DIGIT_OF_ETH):
    x = 10 ** decimals
    return int(val * x)


def getLiquidationPrice(leverage, margin, openNotional, positionSize, mmr, k):
    liquidationPrice = calcLiquidationPrice(
        bigNum2Big(leverage),
        bigNum2Big(margin),
        bigNum2Big(openNotional),
        bigNum2Big(positionSize),
        bigNum2Big(mmr),
        bigNum2Big(k),
    )
    return big2BigNum(liquidationPrice)


def calcLiquidationPrice(leverage, margin, openNotional, positionSize, mmr, k):
    # NOTE: return zero for the case of no liquidation price
    # set 0.0001 as the deviation value
    if leverage <= 1.0001:
        return 0

    pn = (
        (margin - openNotional) / (mmr - 1)
        if positionSize >= 0
        else (margin + openNotional) / (mmr + 1)
    )
    if positionSize >= 0:
        x = positionSize * float(-0.5)
        y = math.pow((positionSize * pn), 2)
        y += pn * k * positionSize * 4
        y = math.sqrt(y) / (pn * 2)
        x = x + y
    else:
        x = positionSize * float(-0.5)
        y = math.pow((positionSize * pn), 2)
        y -= pn * k * positionSize * 4
        y = math.sqrt(y) / (pn * -2)
        x = x + y

    return k / (x ** 2)
