import asyncio
import os

import obstore as obs
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import TableNotFoundError
from obstore.store import S3Store
from structlog import get_logger

from monitor_madrid_parks.io import get_dt_schema, ingest_table, process_alerts
from monitor_madrid_parks.models import AlertData

logger = get_logger()


async def main():
    # TODO: Duplicated logic with scripts/ingest-data.py
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

    table_uri = f"s3://{os.environ['S3_BUCKET']}/processed/alerts"
    storage_options = {
        "AWS_ENDPOINT_URL": os.environ["S3_ENDPOINT"],
        "AWS_ACCESS_KEY_ID": os.environ["S3_ACCESS_KEY_ID"],
        "AWS_SECRET_ACCESS_KEY": os.environ["S3_SECRET_ACCESS_KEY"],
        "AWS_REGION": os.environ["S3_REGION"],
        "AWS_EC2_METADATA_DISABLED": "true",
        "AWS_S3_ALLOW_UNSAFE_RENAME": "true",
    }
    if os.environ.get("S3_CLIENT_ALLOW_HTTP", "false").lower() == "true":
        storage_options["AWS_ALLOW_HTTP"] = "true"

    # TODO: Move this initialisation logic somewhere else
    try:
        dt = DeltaTable(table_uri, storage_options=storage_options)
    except TableNotFoundError:
        logger.warning("Table does not exist, creating it", table_uri=table_uri)
        schema = get_dt_schema()

        write_deltalake(
            table_uri,
            pa.Table.from_batches([], schema=schema),
            storage_options=storage_options,
        )

        dt = DeltaTable(table_uri, storage_options=storage_options)

    for result_list in obs.list(store, prefix="raw/"):
        for obj in result_list:
            logger.info("Processing object", obj=obj)

            # TODO: Write higher level API to get the object bytes
            get_result = await obs.get_async(store, obj["path"])
            result_bytes = await get_result.bytes_async()
            data = AlertData.model_validate_json(result_bytes.to_bytes())

            df = await process_alerts(data, obj["path"])

            await ingest_table(
                df,
                dt,
                delta_merge_options={
                    "predicate": (
                        "t.object_id = s.object_id AND t.source_file = s.source_file"
                    ),
                    "source_alias": "s",
                    "target_alias": "t",
                },
            )


if __name__ == "__main__":
    asyncio.run(main())
