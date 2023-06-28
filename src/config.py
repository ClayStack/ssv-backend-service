import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

ENVIRONMENT = os.getenv("ENVIRONMENT", "")


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def getABI(contractName):
    root = get_project_root()
    if ENVIRONMENT == 'dev':
        path = f'{root}/src/abi/'
    else:
        path = './abi/'
    with open(f"{path}{contractName}.json") as f:
        info_json = json.load(f)
    abi = info_json["abi"]
    return abi


USER_ADDRESS = os.getenv('USER_ADDRESS', '')
WITHDRAW_CREDENTIALS = os.getenv('WITHDRAW_CREDENTIALS', '')
PRIVATE_KEY = os.getenv('PRIVATE_KEY', '')
KEY_STORE_PASSWORD = os.getenv('KEY_STORE_PASSWORD', '')
MNEMONIC_PASSWORD = os.getenv('MNEMONIC_PASSWORD', '')
OPERATOR_IDS = os.getenv('OPERATOR_IDS', '').split(',')  # Assume there are many operator IDs in hand
NETWORK = os.getenv('NETWORK', 'goerli')
LIQUID_STAKING_CONTRACT_ADDRESS = os.getenv('LIQUID_STAKING_CONTRACT_ADDRESS', '0x22863d2a3b5Ba97675fEF8D0C901F31de5F690Ee')
RPC_URL = os.getenv('RPC_URL', 'https://rpc.ankr.com/eth_goerli')

# RPC URLs
RPC_URLS = {
    "goerli": [
        RPC_URL
    ]
}

CONTRACTS = {
    "goerli": {
        "SSVTokenContract": "0x3a9f01091C446bdE031E39ea8354647AFef091E7",
        "SSVNetworkContract": "0xAfdb141Dd99b5a101065f40e3D7636262dce65b3",
        "SSVNetworkViewsContract": "0x8dB45282d7C4559fd093C26f677B3837a5598914",
        "LiquidStakingContract": LIQUID_STAKING_CONTRACT_ADDRESS
    },
}
