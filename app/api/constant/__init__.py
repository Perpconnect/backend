import os

ARTIFACT_BASE_PATH = "api/artifacts/portfolio/"
TEMPLATE_BASE_PATH = "template/"
STAGE_NAME = "production"
ONE_ETH = 10 ** 18
ETHEREUM_PROVIDER_INFURA = os.getenv("ETHEREUM_PROVIDER_INFURA")
METADATA_URL = f"https://metadata.perp.exchange/{STAGE_NAME}.json"
CONFIG_URL = f"https://metadata.perp.exchange/config.{STAGE_NAME}.json"
LAYER1 = "layer1"
DEFAULT_LAYER2_GAS_PRICE = 1_000_000_000
LAYER2 = "layer2"
