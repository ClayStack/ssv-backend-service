import asyncio

from src.node_exits import node_exit_service
from src.node_registration import node_regsitry_service


async def main():
    while True:
        await node_regsitry_service()
        await node_exit_service()
        await asyncio.sleep(60 * 5)  # Sleep for 5 minutes


# Run the script every 5 mins
if __name__ == "__main__":
    asyncio.run(main())
