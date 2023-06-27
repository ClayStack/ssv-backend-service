import re
import time

from web3 import Web3

from src.config import (KEY_STORE_PASSWORD, MNEMONIC_PASSWORD, PRIVATE_KEY,
                        USER_ADDRESS, WITHDRAW_CREDENTIALS, OPERATOR_IDS)
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


async def check_and_register():
    provider = Provider(network)
    contract = getContract(network, 'LiquidStakingContract', provider)
    # Get the contract balance in wei
    contract_balance = getBalance(contract.address, provider)

    # Convert the contract balance from wei to ETH
    contract_balance_eth = Web3.fromWei(contract_balance, 'ether')

    if contract_balance_eth > 32:
        num_validators_pending_deposit = contract.functions.validatorNonce().call() - contract.functions.depositedValidators().call()
        num_validators_needed = contract_balance_eth / 32 - num_validators_pending_deposit

        # Generate credentials for all validators
        credentials = await generate_keys_register_ssv(num_validators_needed)

        # Register validators in liquid staking contract
        for credential in credentials:
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


async def generate_keys_register_ssv(num_validators):
    credentials = []
    for i in range(num_validators):
        [credential, keystore_file] = await generate_validator_credentials()
        ssv_network_contract = get_ssv_network_contract()
        network_fee = await getNetworkFee(ssv_network_contract)

        # Select the Operator IDs for the validator
        start_index = i * 4
        end_index = start_index + 4
        operator_ids_for_validator = OPERATOR_IDS[start_index:end_index]

        # Split the keys and save it in a file, distribute the shares to the operators
        share_file = split_keys(keystore_file, keystore_password=KEY_STORE_PASSWORD, operator_ids=operator_ids_for_validator,
                                network_fee=network_fee)

        # Register the validator to SSV
        await register_validator_to_ssv(share_file, operator_ids_for_validator)

        credentials.append(credential)
    return credentials


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


async def register_validator_to_ssv(share_file, operator_ids):
    contract = get_ssv_network_contract()
    provider = Provider(network)
    shares = get_shares_from_file(share_file)
    await submitTransaction(
        provider,
        contract,
        "registerValidator",
        USER_ADDRESS,
        PRIVATE_KEY,
        [
            shares["validatorPublicKey"],
            operator_ids,
            shares["sharePublicKeys"],
            shares["sharePrivateKey"],
            int(shares["ssvAmount"])
        ])


def split_keys(keystore_file, keystore_password, operator_ids=[], network_fee=0):
    share_file = run_key_split(keystore_file, keystore_password, operator_ids, network_fee=network_fee)
    print(share_file)
    return share_file


# Run the script every 5 mins
while True:
    check_and_register()
    time.sleep(60 * 5)
