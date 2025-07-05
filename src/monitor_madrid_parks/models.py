import datetime as dt
import typing as t
from enum import IntEnum

from pydantic import BaseModel, Field, RootModel, field_validator
from structlog import get_logger

logger = get_logger()


class LeyendaItem(BaseModel):
    description: str
    color: list[int]


class AlertLevel(IntEnum):
    ABIERTO = 1
    INCIDENCIAS = 2
    ALERTA_AMARILLA = 3
    ALERTA_NARANJA = 4
    ALERTA_ROJA = 5
    CERRADO = 6


Leyenda = RootModel[dict[AlertLevel, LeyendaItem]]


class AlertDataField(BaseModel):
    name: str
    type: str
    alias: str
    length: int | None = None


class AlertAttributes(BaseModel):
    zona_verde: t.Annotated[str, Field(alias="ZONA_VERDE")]
    alerta_descripcion: t.Annotated[AlertLevel, Field(alias="ALERTA_DESCRIPCION")]
    fecha_incidencia: t.Annotated[str, Field(alias="FECHA_INCIDENCIA")]
    horario_incidencia: t.Annotated[str | None, Field(alias="HORARIO_INCIDENCIA")]
    prevision_apertura: t.Annotated[str | None, Field(alias="PREVISION_APERTURA")]
    observaciones: t.Annotated[str | None, Field(alias="OBSERVACIONES")]
    object_id: t.Annotated[int, Field(alias="OBJECTID")]

    @field_validator("fecha_incidencia", mode="before")
    @classmethod
    def parse_fecha(cls, value: str) -> str:
        try:
            dt.datetime.strptime(value, "%d/%m/%Y")
        except ValueError:
            logger.warning("Failed to parse fecha_incidencia as date", value=value)

        return value


class AlertDataFeature(BaseModel):
    attributes: AlertAttributes


class AlertData(BaseModel):
    display_field_name: t.Annotated[str, Field(alias="displayFieldName")]
    field_aliases: t.Annotated[dict[str, str], Field(alias="fieldAliases")]
    fields: list[AlertDataField]
    features: list[AlertDataFeature]
