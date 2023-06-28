import asyncio
import random
import logging
from web3 import Web3

from src.config import (KEY_STORE_PASSWORD, PRIVATE_KEY,
                        USER_ADDRESS, OPERATOR_IDS, NETWORK, RPC_URL, CONTRACTS)
from src.ssv_key_split.split_keys import get_shares_from_file, run_key_split
from src.transactions import submitTransaction
from src.utils.ethers import Provider, getBalance, getContract
from src.validators import generate_validator_credentials


# TODO 1. add unit tests for main paths (1 is enough)

async def check_and_register(is_test=False):
    provider = Provider(NETWORK)
    contract = getContract(NETWORK, 'LiquidStakingContract', provider)

    # todo is this the logic of the contract? what about ETH for claims thought?
    # todo from te contract rather seems you need to figure out how many extra nodes you want
    # todo or how many ready, function _selectNextValidator() internal returns (Validator memory validator) {
    # todo this can be a setting in ENV, e.g. always have one ready, so I may need 2 more + 1 idle
    # Get the contract balance in wei
    contract_balance = await getBalance(contract.address, provider)

    # Convert the contract balance from wei to ETH
    contract_balance_eth = Web3.from_wei(contract_balance, 'ether')

    # Check the active validators pending deposit
    next_validator_exists = False
    try:
        deposited_validators = await contract.functions.depositedValidators().call()
        next_validator = await contract.functions.validators(++deposited_validators).call()
        next_validator_exists = len(next_validator.pubkey) == 48
    except Exception as e:
        logging.log(logging.ERROR, e)
    # Calculate the number of validators needed to be registered
    num_validators_needed = contract_balance_eth / 32 + 1

    if (next_validator_exists and num_validators_needed > 0) or is_test:

        # Generate credentials for all validators
        credentials = await generate_keys_and_register_ssv(1 if is_test else num_validators_needed)

        # Register validators in liquid staking contract
        for credential in credentials:
            try:
                await submitTransaction(
                    provider,
                    contract,
                    "registerValidator",
                    USER_ADDRESS,
                    PRIVATE_KEY,
                    [credential.deposit_datum_dict["pubkey"], credential.deposit_datum_dict["withdrawal_credentials"],
                    credential.deposit_datum_dict["signature"], credential.deposit_datum_dict["deposit_data_root"]])
            except Exception as e:
                logging.log(logging.ERROR, e)
    else:
        logging.log(logging.INFO, "Contract balance is not greater than 32 ETH.")


async def generate_keys_and_register_ssv(num_validators):
    credentials = []
    operator_ids = [int(operator_id) for operator_id in OPERATOR_IDS]
    ssv_network_views_contract = getContract(NETWORK, 'SSVNetworkViewsContract', Provider(NETWORK))
    ssv_network_contract = getContract(NETWORK, 'SSVNetworkContract', Provider(NETWORK))
    for i in range(num_validators):
        [credential, keystore_file] = await generate_validator_credentials()
        network_fee = ssv_network_views_contract.functions.getNetworkFee().call()

        # Select the Operator IDs for the validator
        operator_ids_for_validator = random.sample(operator_ids, 4)
        # Remove the selected Operator IDs from the list of Operator IDs
        operator_ids = [ID for ID in operator_ids if ID not in operator_ids_for_validator]

        # Split the keys and save it in a file, distribute the shares to the operators
        share_file, total_ssv_fee = run_key_split(keystore_file, keystore_password=KEY_STORE_PASSWORD,
                                                  operator_ids=operator_ids_for_validator,
                                                  network_fee=network_fee, owner_address=USER_ADDRESS,
                                                  eth_node_url=RPC_URL,
                                                  ssv_contract_address=CONTRACTS[NETWORK]['SSVNetworkContract'])

        # Register the validator to SSV
        shares = get_shares_from_file(share_file)
        publicKey_bytes = bytes(shares["publicKey"], 'utf-8')
        sharesData_bytes = bytes(shares["sharesData"], 'utf-8')
        try:
            await submitTransaction(
                Provider(NETWORK),
                ssv_network_contract,
                "registerValidator",
                USER_ADDRESS,
                PRIVATE_KEY,
                [
                    publicKey_bytes,
                    operator_ids_for_validator,
                    sharesData_bytes,
                    total_ssv_fee,
                    (0, 0, 0, True, 0)
                ])
        except Exception as e:
            logging.log(logging.ERROR, e)

        # Add the credentials to the list
        credentials.append(credential)

    return credentials


async def main():
    while True:
        await check_and_register()
        await asyncio.sleep(60 * 5)  # Sleep for 5 minutes


# Run the script every 5 mins
if __name__ == "__main__":
    asyncio.run(main())
