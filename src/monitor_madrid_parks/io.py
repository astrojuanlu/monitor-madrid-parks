import typing as t
from io import BytesIO
from urllib.parse import urljoin

import deltalake
import httpx
import obstore as obs
import polars as pl
from obstore.store import ObjectStore
from structlog import get_logger

from .models import AlertData

BASE_URL = "https://sigma.madrid.es/hosted/rest/services/MEDIO_AMBIENTE/ALERTAS_PARQUES/MapServer/"

logger = get_logger()


class DeltaMergeOptions(t.TypedDict):
    predicate: t.Required[str]
    source_alias: str
    target_alias: str
    merge_schema: bool
    error_on_type_mismatch: bool
    writer_properties: deltalake.WriterProperties | None
    streamed_exec: bool
    post_commithook_properties: deltalake.PostCommitHookProperties | None
    commit_properties: deltalake.CommitProperties | None


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
        file=BytesIO(data.model_dump_json(indent=2, by_alias=True).encode("utf-8")),
    )
    logger.debug("Data ingested successfully", result=result)


async def process_alerts(data: AlertData, filename: str) -> pl.DataFrame:
    # Schema is consistent with data.fields
    schema = {
        "attributes": pl.Struct(
            [
                pl.Field("zona_verde", pl.Utf8),
                pl.Field("alerta_descripcion", pl.Int64),
                pl.Field("fecha_incidencia", pl.Utf8),
                pl.Field("horario_incidencia", pl.Utf8),
                pl.Field("prevision_apertura", pl.Int64),
                pl.Field("observaciones", pl.Utf8),
                pl.Field("object_id", pl.Int64),
            ]
        ),
    }

    df = (
        pl.DataFrame(data.features, schema=schema)
        .unnest("attributes")
        .with_columns(
            pl.lit(filename).alias("source_file"),
        )
    )
    # TODO: Add pandera validation here?
    return df


async def ingest_table(
    df: pl.DataFrame, dt: deltalake.DeltaTable, delta_merge_options: DeltaMergeOptions
) -> None:
    table_merger = dt.merge(df, **delta_merge_options)

    metrics_dict = (
        table_merger.when_matched_update_all().when_not_matched_insert_all().execute()
    )
    logger.debug(
        "Delta table merged successfully", table_uri=dt.table_uri, metrics=metrics_dict
    )
