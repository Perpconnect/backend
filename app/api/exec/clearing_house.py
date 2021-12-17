from api.utils.contract import get_contract, read_artifacts, bytes_to_str
from api.utils.trader import big2BigNum
import math

ClearingHouseArtifact = read_artifacts("ClearingHouseArtifact.json")


def get_suggested_gas(contract, funcName, args, account):

    print("args: ", args)
    gasLimit = contract.functions.openPosition(
        args[0], args[1], args[2], args[3], args[4]
    ).estimateGas()
    # ['openPosition(address,uint8,tuple,tuple,tuple)'] approve_clearing_house_to_use_usdc
    print("gasLimit: ", gasLimit)


def isApproved(user_address, amm_addr, layer2_usdc, quoteAssetAmount):
    value = layer2_usdc.functions.allowance(amm_addr, user_address).call()
    return value > quoteAssetAmount


def openPosition(layer2Contracts, layer2provider, wallet, layer2_usdc, args, options):
    quoteAssetAmount = big2BigNum(args["quoteAssetAmount"])
    ammAddresses = "0x8d22F1a9dCe724D8c1B4c688D75f17A2fE2D32df"
    print("wallet.address", wallet.address)
    if not isApproved(wallet.address, ammAddresses, layer2_usdc, quoteAssetAmount):
        nonce = layer2provider.eth.get_transaction_count(wallet.address)

        estimate = layer2_usdc.functions.approve(
            layer2Contracts["ClearingHouse"]["address"], 2 ** 256 - 1
        ).estimateGas()

        tx = layer2_usdc.functions.approve(
            layer2Contracts["ClearingHouse"]["address"], 2 ** 256 - 1
        ).buildTransaction(
            {
                "nonce": nonce,
                "gas": 70000,
                "gasPrice": math.ceil(estimate * 1.1),
            }
        )
        signed_tx = layer2provider.eth.account.sign_transaction(
            tx, private_key=wallet.key
        )
        approve_tx_hash = layer2provider.eth.send_raw_transaction(
            signed_tx.rawTransaction
        )
        receipt = layer2provider.eth.wait_for_transaction_receipt(approve_tx_hash)
        print("receipt: ", receipt)

    clearingHouse = get_contract(
        layer2Contracts["ClearingHouse"]["address"],
        ClearingHouseArtifact,
        layer2provider,
    )

    gas_limit = options.get("gas_limit")
    if not gas_limit:

        print(args["quoteAssetAmount"])
        print(args["leverage"])
        print(args["baseAssetAmountLimit"])

        options.gasLimit = get_suggested_gas(
            clearingHouse,
            "openPosition",
            [
                args["amm"],  # 0
                args["side"],  # 1
                {"d": big2BigNum(args["quoteAssetAmount"])},
                {"d": big2BigNum(args["leverage"])},
                {"d": big2BigNum(args["baseAssetAmountLimit"])},
            ],
            wallet.address,
        )

        # Found 1 function(s) with the name `openPosition`: ['openPosition(address,uint8,tuple,tuple,tuple)']

        # options.gasLimit = await getSuggestedGas(
        #     clearingHouse,
        #     "openPosition",
        #     [
        #         openPositionArgs.amm,
        #         openPositionArgs.side,
        #         { d: utils.parseEther(openPositionArgs.quoteAssetAmount.toString()) },
        #         { d: utils.parseEther(openPositionArgs.leverage.toString()) },
        #         { d: utils.parseEther(openPositionArgs.baseAssetAmountLimit.toString()) },
        #     ],
        #     await signer.getAddress(),
        # )


#         export async function getSuggestedGas(
#     contract: Contract,
#     funcName: string,
#     args: any[],
#     account: string,
# ): Promise<BigNumber> {
#     console.log("funcName: ", funcName)
#     const gasLimit = await contract.estimateGas[funcName](...args, { from: account })
#     console.log("gasLimit: ", gasLimit)
#     // multiple estimated gas usage by 1.5
#     return gasLimit.mul(15).div(10)
# }
