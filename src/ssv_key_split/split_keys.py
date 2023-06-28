import json
import re
import subprocess
import requests
from collections import namedtuple
import os
import platform

from typing import List

Operator = namedtuple("Operator", "id pubkey fee name")


class OperatorData:
    API_URL = None
    operator_call = "/api/v3/prater/operators/"

    def __init__(self, api_url):
        """
        :param api_url:
        """
        self.API_URL = api_url

    def make_call(self, url):
        for tries in range(3):
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return response.raise_for_status()
            if tries == 2:
                response.raise_for_status()

    def get_operator_data(self, ids: List[int]):
        operators_data = []
        for id in ids:
            operator_url_id = self.API_URL + self.operator_call + str(id)
            operator_data = self.make_call(operator_url_id)
            operator = Operator(operator_data["id"], operator_data["public_key"], operator_data["fee"],
                                operator_data["name"])
            operators_data.append(operator)
        return operators_data


class SSV:
    CLI_PATH_LINUX_MAC = os.getcwd()
    CLI_PATH_WIN = os.getcwd()
    ssv_share_file = None
    keystore_file = None
    keystore_pass = None

    def __init__(self, keystore_file, keystore_password):
        """
        :param keystore_folder:
        """
        self.keystore_file = keystore_file
        self.keystore_pass = keystore_password

    def get_owner_nonce(self, owner_address="", ssv_contract_address="", eth_node_url=""):
        cli_path = self.CLI_PATH_LINUX_MAC + "/ssv-scanner" if 'Linux' in platform.system() or 'Darwin' in platform.system() else self.CLI_PATH_WIN + "\\ssv-keys"
        os.chdir(cli_path)
        output = subprocess.run(["yarn", "cli", "nonce", "-n", eth_node_url, "-ca", ssv_contract_address, "-oa", owner_address],
                                capture_output=True)
        if output.stderr == None:
            return int(output.stdout.decode("utf-8").replace("Next nonce: ", ""))
        else:
            return 0

    def generate_shares(self, operator_data: List[Operator], network_fees, owner_address, owner_nonce):
        """
        :return:
        """
        operator_ids = [str(operator.id) for operator in operator_data]
        operator_pubkeys = [operator.pubkey for operator in operator_data]
        total_ssv_fee = (sum([int(operator.fee) for operator in operator_data]) + network_fees) * 2628000
        cli_path = self.CLI_PATH_LINUX_MAC + "/ssv-keys" if 'Linux' in platform.system() or 'Darwin' in platform.system() else self.CLI_PATH_WIN + "\\ssv-keys"
        os.chdir(cli_path)
        output_folder = os.getcwd().replace("/ssv-keys","") + (
            "/keyshares" if 'Linux' in platform.system() or 'Darwin' in platform.system() else '\\keyshares')
        output = subprocess.run(["yarn", "cli", "shares", "-ks", self.keystore_file, "-ps", self.keystore_pass, "-oid",
             ",".join(operator_ids), "-ok", ",".join(operator_pubkeys), "-of",
             output_folder, "-oa", owner_address, "-on", str(owner_nonce)], capture_output=True)
        match = re.search(r"Find your key shares file at (.*?)\n", output.stdout.decode("utf-8"))
        if match:
            file_path = match.group(1)
            return file_path, total_ssv_fee
        else:
            return None


def run_key_split(keystore_file, keystore_password, operator_ids=[], network_fee=0, owner_address="", eth_node_url="", ssv_contract_address=""):
    path = os.getcwd() + ("/validator_keys/" if 'Linux' in platform.system() or 'Darwin' in platform.system() else '\\validator_keys\\')
    file_path = path + keystore_file
    ssv = SSV(
        file_path,
        keystore_password)
    op = OperatorData("https://api.ssv.network")
    operators = op.get_operator_data(operator_ids)
    nonce = ssv.get_owner_nonce(owner_address, ssv_contract_address, eth_node_url)
    share_file, total_ssv_fee = ssv.generate_shares(operators, network_fee, owner_address, nonce)
    return share_file, total_ssv_fee


def get_shares_from_file(shares_file):
    with open(shares_file, "r") as file_path:
        shares = json.load(file_path)
    file_path.close()
    return shares['payload']