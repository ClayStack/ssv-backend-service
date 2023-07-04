import asyncio
import random
import logging
from web3 import Web3

from src.config import (KEY_STORE_PASSWORD, PRIVATE_KEY,
                        USER_ADDRESS, OPERATOR_IDS, NETWORK, RPC_URL, CONTRACTS, VALIDATOR_COUNT_ON_HAND)
from src.ssv_key_split.split_keys import get_shares_from_file, run_key_split
from src.transactions import submitTransaction
from src.utils.ethers import Provider, getBalance, getContract
from src.validators import generate_validator_credentials


async def check_and_register():
    provider = Provider(NETWORK)
    contract = getContract(NETWORK, 'LiquidStakingContract', provider)

    num_validators_needed = 0
    try:
        # Get the contract balance in ETH
        contract_balance = await getBalance(contract.address, provider)
        contract_balance_eth = Web3.from_wei(contract_balance, 'ether')
        # Get pending withdrawals in ETH
        pending_withdrawals = await contract.functions.pendingWithdrawals().call()
        pending_withdrawals_eth = Web3.from_wei(pending_withdrawals, 'ether')
        # Calculate the existing registered validators
        validator_count = await contract.functions.validatorNonce().call()
        deposited_validators = await contract.functions.depositedValidators().call()
        existing_registered_validators = validator_count - deposited_validators
        # Calculate the number of validators needed to be registered
        to_deposit_validator_count = (contract_balance_eth - pending_withdrawals_eth) / 32
        num_validators_needed = to_deposit_validator_count - existing_registered_validators + VALIDATOR_COUNT_ON_HAND
    except Exception as e:
        logging.log(logging.ERROR, e)

    if num_validators_needed > 0:

        # Generate credentials for all validators
        credentials = await generate_keys_and_register_ssv(num_validators_needed)

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
