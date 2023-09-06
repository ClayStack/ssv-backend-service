import asyncio
import httpx
import logging
from web3 import Web3

from src.config import (PRIVATE_KEY,
                        USER_ADDRESS, NETWORK)
from src.transactions import submitTransaction
from src.utils.ethers import Provider, getBalance, getContract


async def node_exit_service():
    provider = Provider(NETWORK)
    contract = getContract(NETWORK, 'LiquidStakingContract', provider)

    exit_count = 0
    try:
        # Get the contract balance in ETH
        contract_balance = await getBalance(contract.address, provider)
        contract_balance_eth = Web3.from_wei(contract_balance, 'ether')
        # Get pending withdrawals in ETH
        pending_withdrawals = await contract.functions.pendingWithdrawals().call()
        pending_withdrawals_eth = Web3.from_wei(pending_withdrawals, 'ether')
        # Calculate the number of validators needed to be exited
        exit_count = (pending_withdrawals_eth - contract_balance_eth) / 32
        if exit_count < 1 and pending_withdrawals_eth > contract_balance_eth:
            exit_count = 1
    except Exception as e:
        logging.log(logging.ERROR, e)

    if exit_count > 0:
        # Exits the validators from the liquid staking contract
        for i in range(exit_count):
            try:
                # Get the validator's public key, the validator
                exit_validators_nonce = await contract.functions.exitValidatorNonce().call()
                validator_index = exit_validators_nonce
                validator = await contract.functions.validators(validator_index).call()
                public_key = validator[0]
                # Get the validator's operator ids
                operator_ids_for_validator, cluster_id = await get_ssv_operators_for_validator(public_key, NETWORK)
                # Get the cluster data for the validator
                cluster_snapshot = await get_ssv_cluster_snapshot(cluster_id, NETWORK)
                # Exit the validator from ssv network
                ssv_network_contract = getContract(NETWORK, 'SSVNetworkContract', Provider(NETWORK))
                await submitTransaction(
                    Provider(NETWORK),
                    ssv_network_contract,
                    "removeValidator",
                    USER_ADDRESS,
                    PRIVATE_KEY,
                    [
                        public_key,
                        operator_ids_for_validator,
                        cluster_snapshot
                    ])
                # Mark validator as inactive in liquid staking contract
                await submitTransaction(
                    provider,
                    contract,
                    "exitValidator",
                    USER_ADDRESS,
                    PRIVATE_KEY,
                    []
                )
            except Exception as e:
                logging.log(logging.ERROR, e)
    else:
        logging.log(logging.INFO, "No exits needed.")


async def get_ssv_operators_for_validator(pub_key, network):
    ssv_network = 'prater' if network == 'goerli' else 'mainnet'

    async with httpx.AsyncClient() as client:
        url = f'https://api.ssv.network/api/v4/{ssv_network}/validators/{pub_key}'
        headers = {'accept': '*/*'}

        response = await client.get(url, headers=headers)
        formatted_response = response.json()
        operator_ids = [operator["id"] for operator in formatted_response["operators"]]
        return operator_ids, formatted_response["cluster"]


async def get_ssv_cluster_snapshot(cluster_id, network):
    ssv_network = 'prater' if network == 'goerli' else 'mainnet'

    async with httpx.AsyncClient() as client:
        url = f'https://api.ssv.network/api/v4/{ssv_network}/clusters/{cluster_id}'
        headers = {'accept': '*/*'}

        response = await client.get(url, headers=headers)
        formatted_response = response.json()
        return (
            formatted_response["cluster"]["validatorCount"],
            formatted_response["cluster"]["networkFeeIndex"],
            formatted_response["cluster"]["index"],
            formatted_response["cluster"]["active"],
            formatted_response["cluster"]["balance"]
        )


# Run the script every 5 mins
if __name__ == "__main__":
    asyncio.run(node_exit_service())
