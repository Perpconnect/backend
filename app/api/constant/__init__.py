import os 

BASE_PATH = "api/artifacts/portfolio/"
STAGE_NAME = "production"
ONE_ETH = 10 ** 18
ETHEREUM_PROVIDER_INFURA = os.getenv("ETHEREUM_PROVIDER_INFURA")
METADATA_URL = f"https://metadata.perp.exchange/{STAGE_NAME}.json"
CONFIG_URL = f"https://metadata.perp.exchange/config.{STAGE_NAME}.json"