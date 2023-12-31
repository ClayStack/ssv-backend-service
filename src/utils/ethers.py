import time

from web3 import Web3
from web3.middleware import geth_poa_middleware

from src.abi import abis
from src.config import CONTRACTS, RPC_URLS, logger
from src.utils.async_utils import force_async


class Provider:
    web3 = None
    index = 0
    rotate = False
    loops = 0
    MAX_LOOPS = 10
    limit = None
    isLocal = False
    rpc = None

    def __init__(self, network, rotateRPC=True, isLocal=False):
        self.network = network
        self.rotate = rotateRPC
        self.isLocal = isLocal
        self.selectNextProvider()

    def selectNextProvider(self):
        urls = RPC_URLS[self.network] if not self.isLocal else RPC_URLS['localnet']
        if len(urls) == self.index:
            if self.rotate and self.loops < self.MAX_LOOPS:
                self.index = 0
                self.loops += 1
            else:
                self.index = 0
                logger.exception(f"RPC Failed for {self.network}")
                time.sleep(60)

        self.rpc = urls[self.index]
        self.limit = 10000
        self.web3 = Web3(Web3.HTTPProvider(
            self.rpc, request_kwargs={'timeout': 900}))
        self.web3.middleware_onion.inject(
            geth_poa_middleware, layer=0)  # Inject poa middleware
        self.index = self.index + 1

        if not self.web3.is_connected():
            logger.info(f"RPC: {self.rpc} disconnected, next provider")
            return self.selectNextProvider()

def getContract(network, contractName, provider: Provider):
    address = CONTRACTS[network][contractName]
    abi = abis.ABI[contractName]
    contract = provider.web3.eth.contract(address=address, abi=abi)
    return contract


@force_async
def getBalance(address, provider: Provider):
    balance = provider.web3.eth.get_balance(address)
    return balance

