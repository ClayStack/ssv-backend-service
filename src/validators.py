import re

from src.config import MNEMONIC_PASSWORD, NETWORK, KEY_STORE_PASSWORD, WITHDRAW_CREDENTIALS
from src.staking_deposit.generate_new_keystore import generate_keys


async def generate_validator_credentials():
    [credentials, keystore_file_folders] = generate_keys(mnemonic_password=MNEMONIC_PASSWORD,
                                                         validator_start_index=0,
                                                         num_validators=1, chain=NETWORK,
                                                         keystore_password=KEY_STORE_PASSWORD,
                                                         eth1_withdrawal_address=WITHDRAW_CREDENTIALS)
    credential = credentials.credentials[0]
    match = re.search(r'keystore.*\.json', keystore_file_folders[0])
    keystore_file = match.group()
    return [credential, keystore_file]