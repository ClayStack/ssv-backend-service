import aiohttp

timeout = aiohttp.ClientTimeout(total=60 * 10)


async def post(url, json=None):
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url=url, json=json) as response:
            if response.status == 200:
                out = await response.json()
                return out
            else:
                reason = response.reason
                try:
                    body = await response.json()
                    reason = body['error']
                except:
                    pass
                return {
                    'code': response.status,
                    'error': reason
                }


async def get(url, params=None, headers=None):
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                out = await response.json()
                return out
            else:
                return response.status
