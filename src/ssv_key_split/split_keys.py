import json
from subprocess import check_output
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
    CLI_PATH_LINUX_MAC = os.getcwd() + "/ssv/ssv-cli"
    CLI_PATH_WIN = os.getcwd() + "\\ssv\\ssv-cli.exe"
    ssv_share_file = None
    keystore_file = None
    keystore_pass = None

    def __init__(self, keystore_file, keystore_password):
        """
        :param keystore_folder:
        """
        self.keystore_file = keystore_file
        self.keystore_pass = keystore_password

    def generate_shares(self, operator_data: List[Operator], network_fees):
        """
        :return:
        """
        # todo clean
        print("===================================================================================")
        operator_ids = [str(operator.id) for operator in operator_data]
        operator_pubkeys = [operator.pubkey for operator in operator_data]
        total_ssv_fee = (sum([int(operator.fee) for operator in operator_data]) + network_fees) * 2628000
        output_folder = os.getcwd() + ("/keyshares" if 'Linux' in platform.system() or 'Darwin' in platform.system() else '\\keyshares')
        cli_path = self.CLI_PATH_LINUX_MAC if 'Linux' in platform.system() or 'Darwin' in platform.system() else self.CLI_PATH_WIN
        # output2=check_output(["ls","-la"])
        # print(output2) # todo clean
        output = check_output(
            [cli_path, "key-shares", "-ks", self.keystore_file, "-ps", self.keystore_pass, "-oid",
             ",".join(operator_ids), "-ok", ",".join(operator_pubkeys), "-ssv", str(total_ssv_fee), "-of",
             output_folder])
        print(output)# todo logger
        return output_folder + output.decode("utf-8").partition("keyshares")[2].partition(".json")[0] + ".json"

    def stake_shares(self, share_file_path):
        """
        :return:
        """
        print(share_file_path)# todo logger
        with open(share_file_path, "r") as file_path:
            print(file_path)# todo logger
            shares = json.load(file_path)
        file_path.close()
        return shares["payload"]["readable"]


def run_key_split(keystore_file, keystore_password, operator_ids=[], network_fee=0):
    path = os.getcwd() + ("/validator_keys/" if 'Linux' in platform.system() or 'Darwin' in platform.system() else '\\validator_keys\\')
    file_path = path + keystore_file
    ssv = SSV(
        file_path,
        keystore_password)
    op = OperatorData("https://api.ssv.network")
    operators = op.get_operator_data(operator_ids)
    share_file = str(ssv.generate_shares(operators, network_fee))
    ssv.stake_shares(share_file)
    return share_file


def get_shares_from_file(shares_file):
    with open(shares_file, "r") as file_path:
        print(file_path)
        shares = json.load(file_path)
    file_path.close()
    return shares['payload']['readable']
