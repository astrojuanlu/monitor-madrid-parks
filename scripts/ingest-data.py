import asyncio
import datetime as dt
import os
from zoneinfo import ZoneInfo

from obstore.store import S3Store

from monitor_madrid_parks.io import fetch_alerts, ingest_alerts


async def main():
    now = dt.datetime.now(ZoneInfo("Europe/Madrid"))
    filename = f"raw/result_{now:%Y-%m-%dT%H:%M}.json"

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
