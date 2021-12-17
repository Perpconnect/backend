import json

import requests
from web3 import Web3

from api.constant import (
    ARTIFACT_BASE_PATH,
    TEMPLATE_BASE_PATH,
    ETHEREUM_PROVIDER_INFURA,
)


def read_artifacts(fname: str):
    with open(ARTIFACT_BASE_PATH + fname) as f:
        return json.load(f)


def get_template(fname):
    with open(TEMPLATE_BASE_PATH + fname) as f:
        return json.load(f)


def fetch_data(url: str) -> dict:
    resp = requests.get(url)
    return resp.json()


def get_layer1_provider():
    return Web3(Web3.WebsocketProvider(ETHEREUM_PROVIDER_INFURA))


def get_layer2_provider(config):
    wsUrlFromConfig = config["L2_WEB3_ENDPOINTS"][0]["url"]
    if wsUrlFromConfig:
        return Web3(Web3.WebsocketProvider(wsUrlFromConfig))


def get_provider(layer, config=None):
    if layer == "layer1":
        return get_layer1_provider()
    if layer == "layer2":
        return get_layer2_provider(config)
    else:
        raise Exception("provider not exists")


def get_contract(address, abi, provider):
    return provider.eth.contract(address=address, abi=abi)


def bytes_to_str(value):
    value = value.hex().rstrip("0")
    if len(value) % 2 != 0:
        value = value + "0"
    return bytes.fromhex(value).decode("utf8")
