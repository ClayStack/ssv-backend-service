import re
import time

import web3 as web3

from src.config import (KEY_STORE_PASSWORD, MNEMONIC_PASSWORD, PRIVATE_KEY,
                        USER_ADDRESS, WITHDRAW_CREDENTIALS)
from src.ssv_key_split.split_keys import get_shares_from_file, run_key_split
from src.staking_deposit.generate_new_keystore import generate_keys
from src.TransactionManager import submitTransaction
from src.utils.ethers import Provider, getBalance, getContract

network = 'goerli'


def getNetworkFee(contract_object):
    networkFee = contract_object.functions.getNetworkFee().call()
    return networkFee


def get_ssv_network_contract():
    provider = Provider(network)
    contract_object = getContract(network, 'SSVNetworkContract', provider)
    return contract_object


def get_liquid_staking_contract():
    provider = Provider(network)
    contract_object = getContract(network, 'LiquidStakingContract', provider)
    return contract_object


async def check_and_deposit():
    provider = Provider(network)
    contract = getContract(network, 'LiquidStakingContract', provider)
    # Get the contract balance in wei
    contract_balance = getBalance(contract.address, provider)

    # Convert the contract balance from wei to ETH
    contract_balance_eth = web3.fromWei(contract_balance, 'ether')

    if contract_balance_eth > 32:
        share_file, credential = generate_keys_register_ssv()
        shares = get_shares_from_file(share_file)
        # TODO Register the validator to ssv network with the shares

        # Regsiter validator in liquid staking contract
        contract = get_liquid_staking_contract()
        provider = Provider(network)
        item = await submitTransaction(
            provider,
            contract,
            "registerValidator",
            USER_ADDRESS,
            PRIVATE_KEY,
            [credential.deposit_datum_dict["pubkey"], credential.deposit_datum_dict["withdrawal_credentials"],
             credential.deposit_datum_dict["signature"], credential.deposit_datum_dict["deposit_data_root"]])
        print(item)
    else:
        print("Contract balance is not greater than 32 ETH.")


async def generate_keys_register_ssv():
    [credential, keystore_file] = await generate_validator_credentials()
    ssv_network_contract = get_ssv_network_contract()
    network_fee = await getNetworkFee(ssv_network_contract)
    operator_ids = [1, 2, 192, 42]
    share_file = split_keys(keystore_file, keystore_password=KEY_STORE_PASSWORD, operator_ids=operator_ids,
                            network_fee=network_fee)
    return share_file, credential


async def generate_validator_credentials():
    [credentials, keystore_file_folders] = generate_keys(mnemonic_password=MNEMONIC_PASSWORD,
                                                         validator_start_index=0,
                                                         num_validators=1, chain='goerli',
                                                         keystore_password=KEY_STORE_PASSWORD,
                                                         eth1_withdrawal_address=WITHDRAW_CREDENTIALS)
    credential = credentials.credentials[0]
    match = re.search(r'keystore.*\.json', keystore_file_folders[0])
    keystore_file = match.group()
    return [credential, keystore_file]


def split_keys(keystore_file, keystore_password, operator_ids=[], network_fee=0):
    share_file = run_key_split(keystore_file, keystore_password, operator_ids, network_fee=network_fee)
    print(share_file)
    return share_file


# Run the script every 5 mins
while True:
    check_and_deposit()
    time.sleep(60 * 5)  # Sleep for 5 mins
