import typing as t
from io import BytesIO
from urllib.parse import urljoin

import httpx
import obstore as obs
from obstore.store import ObjectStore
from structlog import get_logger

from .models import AlertData

BASE_URL = "https://sigma.madrid.es/hosted/rest/services/MEDIO_AMBIENTE/ALERTAS_PARQUES/MapServer/"

logger = get_logger()


async def _fetch_alerts_raw(base_url=BASE_URL) -> t.Any:
    async with httpx.AsyncClient() as client:
        result = await client.get(
            urljoin(base_url, "0/query"),
            params={
                "where": "1=1",
                "outFields": "*",
                "f": "json",
                "returnGeometry": "false",
            },
        )

    result.raise_for_status()

    return result.json()


async def fetch_alerts(base_url=BASE_URL) -> AlertData:
    result = await _fetch_alerts_raw(base_url)
    return AlertData.model_validate(result)


async def ingest_alerts(data: AlertData, filename: str, store: ObjectStore) -> None:
    result = await obs.put_async(
        store,
        path=filename,
        file=BytesIO(data.model_dump_json(indent=2).encode("utf-8")),
    )
    logger.debug("Data ingested successfully", result=result)
