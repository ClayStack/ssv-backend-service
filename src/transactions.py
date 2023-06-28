from datetime import datetime

from src.utils.async_utils import force_async


@force_async
def submitTransaction(provider, contract, function_name, account, private_key, params, overrides={}):
    nonce = provider.web3.eth.get_transaction_count(account)
    if contract:
        contractFunction = contract.functions[function_name]
        details = {
            "from": account,
            "nonce": nonce,
        }
        if 'value' in overrides:
            details['value'] = overrides['value']
        transaction = contractFunction(*params).build_transaction(details)
    else:
        transaction = {
            "from": account,
            'gas': 21000,
            'gasPrice': provider.web3.eth.gas_price,
            'nonce': nonce,
            'chainId': provider.web3.eth.chainId
        }
    transaction.update(overrides)
    signed_tx = provider.web3.eth.account.sign_transaction(transaction, private_key)
    tx = provider.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

    del transaction['data']
    del transaction['value']
    del transaction['chainId']
    now = datetime.utcnow()

    item = {
        "_id": tx.hex(),
        **transaction,
        'method': function_name,
        'network': provider.network,
        "sent": now,
        "status": None,
    }
    return item
