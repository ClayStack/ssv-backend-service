from unittest import IsolatedAsyncioTestCase

from src.main import check_and_register
from src.ssv_key_split.split_keys import run_key_split
from src.validators import generate_validator_credentials


class Test(IsolatedAsyncioTestCase):
    async def test_stats(self):
        await check_and_register(True)