from unittest import IsolatedAsyncioTestCase

from src.main import check_and_register
from src.ssv_key_split.split_keys import run_key_split


class Test(IsolatedAsyncioTestCase):
    async def test_stats(self):
        await run_key_split("keystore-m_12381_3600_0_0_0-1675095410.json", "1234567890", [2])
        await check_and_register(True)