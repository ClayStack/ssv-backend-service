import re
import time

from web3 import Web3

from src.config import (KEY_STORE_PASSWORD, MNEMONIC_PASSWORD, PRIVATE_KEY,
                        USER_ADDRESS, WITHDRAW_CREDENTIALS, OPERATOR_IDS)
from src.ssv_key_split.split_keys import get_shares_from_file, run_key_split
from src.staking_deposit.generate_new_keystore import generate_keys
from src.TransactionManager import submitTransaction
from src.utils.ethers import Provider, getBalance, getContract

network = 'goerli'  # todo move to a config file


# TODO
# TODO 1. add unit tests for main paths (1 is enough)
# TODO 2. aligned functions and naming to lower case _ separated
# TODO 3. organize project like our repo and add the Dockerfile to allow a user to be able to run it fully
# TODO 4. add a README.md file with instructions on how to run the project, what it does. Base similar on the readme from liquid and fix with ChatGPT


# todo method used once, you can move to the in-function
def getNetworkFee(contract_object):
    networkFee = contract_object.functions.getNetworkFee().call()
    return networkFee

# todo function move to in-line to simplify
def get_ssv_network_contract():
    provider = Provider(network)
    contract_object = getContract(network, 'SSVNetworkContract', provider)
    return contract_object

# todo same here
def get_liquid_staking_contract():
    provider = Provider(network)
    contract_object = getContract(network, 'LiquidStakingContract', provider)
    return contract_object


async def check_and_register():
    provider = Provider(network)
    contract = getContract(network, 'LiquidStakingContract', provider)

    # todo is this the logic of the contract? what about ETH for claims thought?
    # todo from te contract rather seems you need to figure out how many extra nodes you want
    # todo or how many ready, function _selectNextValidator() internal returns (Validator memory validator) {
    # todo this can be a setting in ENV, e.g. always have one ready, so I may need 2 more + 1 idle
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
            # todo I think best not to include tx manager in this code instead a simple liners submitting the tx directly
            # todo have the code wait for it to complete and/or rather handle and raise expection
            item = await submitTransaction(
                provider,
                contract,
                "registerValidator",
                USER_ADDRESS,
                PRIVATE_KEY,
                [credential.deposit_datum_dict["pubkey"], credential.deposit_datum_dict["withdrawal_credentials"],
                 credential.deposit_datum_dict["signature"], credential.deposit_datum_dict["deposit_data_root"]])
            print(item) # todo use logger as we are declaring it in the config
    else:
        # todo use logger as we are declaring it in the config
        print("Contract balance is not greater than 32 ETH.")


async def generate_keys_register_ssv(num_validators):
    credentials = []
    for i in range(num_validators):
        [credential, keystore_file] = await generate_validator_credentials()
        ssv_network_contract = get_ssv_network_contract()
        network_fee = await getNetworkFee(ssv_network_contract)

        # Select the Operator IDs for the validator
        # todo make sure to add the logic to select the operator ids in the readme
        # todo what is your logic? seems you are doing it sequentially? what is I am adding 10 validators and my array is of only 4 operators, then this will fail
        # todo you can still do sequentially roundrobin and you can randomize the starting point from the list e.g. say I have 6 operators and I start at 3, then I select, 3, 4,,5,6
        # todo better would be select 4 at random (without replacement ensures no duplicate as you need 4 unique) and then select the operator ids
        start_index = i * 4
        end_index = start_index + 4
        operator_ids_for_validator = OPERATOR_IDS[start_index:end_index]

        # Split the keys and save it in a file, distribute the shares to the operators
        share_file = split_keys(keystore_file, keystore_password=KEY_STORE_PASSWORD,
                                operator_ids=operator_ids_for_validator,
                                network_fee=network_fee)

        # Register the validator to SSV
        await register_validator_to_ssv(share_file, operator_ids_for_validator)

        credentials.append(credential)
    return credentials


# todo organize this function in a diff file connected to validator
async def generate_validator_credentials():
    [credentials, keystore_file_folders] = generate_keys(mnemonic_password=MNEMONIC_PASSWORD,
                                                         validator_start_index=0,
                                                         num_validators=1, chain='goerli', # todo remove hardcoded
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
    print(share_file) # todo logger
    return share_file


# todo this doesn't work yet, make sure it's async
# Run the script every 5 mins
while True:
    check_and_register()
    time.sleep(60 * 5)
