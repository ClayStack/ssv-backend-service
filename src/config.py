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


# API
# todo clean unsued ones
HTTP_PORT = os.getenv('HTTP_PORT', 5001)
API_KEY = os.getenv('API_KEY', '123')
SKIP_STARTUP = os.getenv('SKIP_STARTUP', 'False')
USER_ADDRESS = os.getenv('USER_ADDRESS', '')
WITHDRAW_CREDENTIALS = os.getenv('WITHDRAW_CREDENTIALS', '')
PRIVATE_KEY = os.getenv('PRIVATE_KEY', '')
KEY_STORE_PASSWORD = os.getenv('KEY_STORE_PASSWORD', '')
MNEMONIC_PASSWORD = os.getenv('MNEMONIC_PASSWORD', '')
OPERATOR_IDS = os.getenv('OPERATOR_IDS', '').split(',')  # Assume there are many operator IDs in hand

# RPC URLs
# todo remove all and read single item from env. You can still leave as array to avoid changing the util code
RPC_URLS = {
    "mainnet": [
        'https://mainnet.infura.io/v3/6292442a776d4d2ca339570c510876c5',
        'https://mainnet.infura.io/v3/94a687f398b24310a4f6b48ee9d80869',
        'https://mainnet.infura.io/v3/2ce17bba00d04226a02dc6d69fe9cb99',
        'https://mainnet.infura.io/v3/90f112e4496f4817a561dc440332f492',
        'http://195.201.160.24:5555',
    ],
    "local": ["http://127.0.0.1:8545/"],
    "goerli": [
        'https://goerli.infura.io/v3/90f112e4496f4817a561dc440332f492',
        'https://goerli.infura.io/v3/2ce17bba00d04226a02dc6d69fe9cb99',
        'https://goerli.infura.io/v3/94a687f398b24310a4f6b48ee9d80869',
    ]
}

# todo same, read address from env
CONTRACTS = {
    "mainnet": {
    },
    "goerli": {
        "SSVTokenContract": "0x3a9f01091C446bdE031E39ea8354647AFef091E7",
        "SSVNetworkContract": "0xb9e155e65B5c4D66df28Da8E9a0957f06F11Bc04",
        "LiquidStakingContract": "0x"  # Update deployment address
    },
}
