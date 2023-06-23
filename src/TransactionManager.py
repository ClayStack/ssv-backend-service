import asyncio
from datetime import datetime

from web3 import Web3

from config import logger
from src.utils.async_utils import force_async
from utils import fetch

API = 'https://api.etherscan.io/api?module=gastracker&action=gasoracle&apikey=7XA3GMX2WBVPZA9NSVRHP87J2BV2I2SHM2'


async def getGasPrices():
    result = await fetch.get(API)
    return result['result']

GAS_PRICES = {
    'mainnet': {
        'initial': {
            'maxFeePerGas': 28,
            'maxPriorityFeePerGas': 1.5
        },
        'max': {
            'maxFeePerGas': 60,
            'maxPriorityFeePerGas': 30
        }
    },
    'goerli': {
        'initial': {
            'maxFeePerGas': 2,
            'maxPriorityFeePerGas': 1
        }
    },
    'mumbai': {
        'initial': {
            'maxFeePerGas': 2,
            'maxPriorityFeePerGas': 1
        }
    }
}

PRICING_POLICY = {
    '2days': {
        'startIncrease': 30,
        'endIncrease': 36,
        'hourlyUpdate': 1
    },
    'hourly': {
        'startIncrease': 0,
        'endIncrease': 24,
        'hourlyUpdate': 1
    }
}


@force_async
def submitTransaction(provider, contract, functionName, account, privateKey, params, overrides={}):
    nonce = provider.web3.eth.get_transaction_count(account)
    if contract:
        contractFunction = contract.functions[functionName]
        details = {
            "from": account,
            "nonce": nonce,
        }
        if 'value' in overrides:
            details['value'] = overrides['value']
        transaction = contractFunction(*params).buildTransaction(details)
    else:
        transaction = {
            "from": account,
            'gas': 21000,
            'gasPrice': provider.web3.eth.gas_price,
            'nonce': nonce,
            'chainId': provider.web3.eth.chainId
        }
    transaction.update(overrides)
    signed_tx = provider.web3.eth.account.sign_transaction(transaction, privateKey)
    tx = provider.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

    del transaction['data']
    del transaction['value']
    del transaction['chainId']
    now = datetime.utcnow()

    item = {
        "_id": tx.hex(),
        **transaction,
        'method': functionName,
        'network': provider.network,
        "sent": now,
        "status": None,
    }
    return item


def isMainnet(network):
    return network in ['mainnet', 'polygon']


async def getGasPrice(network, current, last, policy='2days'):
    lastTime = None
    if network == 'mainnet':
        if last and policy == '2days':
            lastTime = last['updated']
        elif current:
            lastTime = current['sent']

        now = datetime.utcnow()
        hoursLast = (now - lastTime).total_seconds() / 3600 if lastTime else 0
        hoursUpdate = (now - current['sent']).total_seconds() / 3600 if current else 0
        prices = GAS_PRICES[network]['initial']
        latest = await getGasPrices()
        hoursPolicy = PRICING_POLICY[policy]

        # if 30 + 36 hours bid mid-amount increase by 11% every hour (as safety of the min 10%)
        if hoursLast > hoursPolicy['startIncrease'] and hoursLast <= hoursPolicy['endIncrease']:
            factor = 1.11 if hoursUpdate >= hoursPolicy['hourlyUpdate'] else 1
            prices = {
                'maxFeePerGas': Web3.fromWei(current['maxFeePerGas'] * factor, 'gwei'),
                'maxPriorityFeePerGas': Web3.fromWei(current['maxPriorityFeePerGas'] * factor, 'gwei')
            }
        # if 36 + 48 + bid the lowest amount
        elif hoursLast > hoursPolicy['startIncrease']:
            prices = {
                'maxFeePerGas': int(latest['SafeGasPrice']),
                'maxPriorityFeePerGas': Web3.fromWei(current['maxPriorityFeePerGas'] * 1.11, 'gwei') if current else
                prices['maxPriorityFeePerGas']
            }

        # adjust to limits
        prices_max = GAS_PRICES[network]['max']
        prices['maxFeePerGas'] = min(int(latest['SafeGasPrice']) * 1.1, prices['maxFeePerGas'])
        prices['maxFeePerGas'] = min(prices['maxFeePerGas'], prices_max['maxFeePerGas'])
        prices['maxPriorityFeePerGas'] = min(prices['maxPriorityFeePerGas'], prices_max['maxPriorityFeePerGas'])

        prices_wei = {
            'maxFeePerGas': Web3.toWei(prices['maxFeePerGas'], 'gwei'),
            'maxPriorityFeePerGas': Web3.toWei(prices['maxPriorityFeePerGas'], 'gwei')
        }

        # adjust to previous
        if current:
            prices_wei['maxFeePerGas'] = max(current['maxFeePerGas'], prices_wei['maxFeePerGas'])
            prices_wei['maxPriorityFeePerGas'] = max(current['maxPriorityFeePerGas'],
                                                     prices_wei['maxPriorityFeePerGas'])

        return prices_wei
    else:
        if not current:
            prices = GAS_PRICES[network]['initial']
            prices_wei = {
                'maxFeePerGas': Web3.toWei(prices['maxFeePerGas'], 'gwei'),
                'maxPriorityFeePerGas': Web3.toWei(prices['maxPriorityFeePerGas'], 'gwei')
            }
        else:
            prices_wei = {
                'maxFeePerGas': int(current['maxFeePerGas'] * 1.11),
                'maxPriorityFeePerGas': int(current['maxPriorityFeePerGas'] * 1.11)
            }

        # adjust to previous
        if current:
            prices_wei['maxFeePerGas'] = max(current['maxFeePerGas'], prices_wei['maxFeePerGas'])
            prices_wei['maxPriorityFeePerGas'] = max(current['maxPriorityFeePerGas'],
                                                     prices_wei['maxPriorityFeePerGas'])

        # ensure max is higher
        prices_wei['maxFeePerGas'] = max(prices_wei['maxFeePerGas'], prices_wei['maxPriorityFeePerGas'])

        return prices_wei


class TransactionManager:

    async def sendTransaction(self, serviceId, provider, info, contract, functionName, account, privateKey, params=[],
                              overrides={}, maxTries=10, current=None, last=None, policy='2days', eventName=None):
        # check if existing transaction
        current = await self.getPending(serviceId, provider, info,
                                        filters={'method': functionName},
                                        eventName=eventName) if not current else current
        last = await self.getLastSuccessful(serviceId, filters={'method': functionName}) if not last else last
        reprice = False
        current_gas = current

        tries = 0
        excep = Exception
        while tries < maxTries:
            try:
                tries += 1

                if provider.network == 'mainnet' or reprice:
                    gas = await getGasPrice(provider.network, current_gas, last, policy=policy)
                    overrides.update(gas)
                    reprice = False
                    if current_gas and (current_gas['maxFeePerGas'] * 1.1 > gas['maxFeePerGas'] or current_gas[
                        'maxPriorityFeePerGas'] * 1.1 > gas['maxPriorityFeePerGas']):
                        return current
                    else:
                        current_gas = gas

                tx: dict = await submitTransaction(provider, contract, functionName, account, privateKey, params,
                                                   overrides)
                return tx
            except Exception as e:
                error = getError(e)
                excep = e
                if 'replacement transaction underpriced' in error or 'already known' in error:
                    reprice = True
                    logger.warning(f'{serviceId}: repricing')
                else:
                    break

        # couldn't submit
        raise excep


def getError(e):
    if isinstance(e, ValueError) and isinstance(e.args[0], str):
        return e.args[0]
    elif isinstance(e, ValueError) and e.args[0].get('message'):
        return e.args[0]['message']
    else:
        return str(e)
