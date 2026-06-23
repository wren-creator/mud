import asyncio
import logging
from server import MUDServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

async def main():
    server = MUDServer(host="0.0.0.0", port=4000)
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())
