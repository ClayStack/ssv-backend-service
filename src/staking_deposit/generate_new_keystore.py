import os

from eth_typing import HexAddress
from eth_utils import is_hex_address, to_normalized_address

from src.staking_deposit.credentials import CredentialList
from src.staking_deposit.exceptions import ValidationError
from src.staking_deposit.key_handling.key_derivation.mnemonic import \
    get_mnemonic
from src.staking_deposit.settings import get_chain_setting
from src.staking_deposit.utils.constants import (
    DEFAULT_VALIDATOR_KEYS_FOLDER_NAME, MAX_DEPOSIT_AMOUNT, WORD_LISTS_PATH)
from src.staking_deposit.utils.intl import load_text
from src.staking_deposit.utils.validation import verify_deposit_data_json


def new_mnemonic() -> str:
    mnemonic = get_mnemonic(language='english', words_path=WORD_LISTS_PATH)
    return mnemonic


def validate_eth1_withdrawal_address(address: str) -> HexAddress:
    if address is None:
        return None
    if not is_hex_address(address):
        raise ValueError(load_text(['err_invalid_ECDSA_hex_addr']))

    normalized_address = to_normalized_address(address)
    return normalized_address


def generate_keys(mnemonic_password: str, validator_start_index: int,
                  num_validators: int, chain, keystore_password: str,
                  eth1_withdrawal_address: HexAddress):
    # Validate address
    validate_eth1_withdrawal_address(eth1_withdrawal_address)
    mnemonic = new_mnemonic()
    mnemonic_password = mnemonic_password
    amounts = [MAX_DEPOSIT_AMOUNT] * num_validators
    folder = os.path.join(DEFAULT_VALIDATOR_KEYS_FOLDER_NAME)
    chain_setting = get_chain_setting(chain)
    if not os.path.exists(folder):
        os.mkdir(folder)
    credentials = CredentialList.from_mnemonic(
        mnemonic=mnemonic,
        mnemonic_password=mnemonic_password,
        num_keys=num_validators,
        amounts=amounts,
        chain_setting=chain_setting,
        start_index=validator_start_index,
        hex_eth1_withdrawal_address=eth1_withdrawal_address,
    )
    keystore_filefolders = credentials.export_keystores(
        password=keystore_password, folder=folder)
    deposits_file = credentials.export_deposit_data_json(folder=folder)
    if not credentials.verify_keystores(keystore_filefolders=keystore_filefolders, password=keystore_password):
        raise ValidationError(load_text(['err_verify_keystores']))
    if not verify_deposit_data_json(deposits_file, credentials.credentials):
        raise ValidationError(load_text(['err_verify_deposit']))
    return [credentials, keystore_filefolders]
