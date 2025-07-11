import asyncio
import os

import structlog
from obstore.store import S3Store
from whenever import Instant

from monitor_madrid_parks.io import fetch_alerts, ingest_alerts

# TODO: This configuration should happen only once,
# see https://www.structlog.org/en/25.4.0/configuration.html
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S.%fZ", utc=True),
        structlog.dev.ConsoleRenderer(),
    ],
)

logger = structlog.get_logger()


async def main():
    now = Instant.now().to_tz("Europe/Madrid")
    filename = f"raw/result_{now.py_datetime():%Y-%m-%dT%H:%M}.json"

    data = await fetch_alerts()

    client_options = {}
    if os.environ.get("S3_CLIENT_ALLOW_HTTP", "false").lower() == "true":
        client_options["allow_http"] = True

    store = S3Store(
        os.environ["S3_BUCKET"],
        client_options=client_options,
        endpoint=os.environ["S3_ENDPOINT"],
        access_key_id=os.environ["S3_ACCESS_KEY_ID"],
        secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
        region=os.environ["S3_REGION"],
    )

    await ingest_alerts(data, filename, store)


if __name__ == "__main__":
    asyncio.run(main())
