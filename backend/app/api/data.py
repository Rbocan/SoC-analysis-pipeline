from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app.models.schemas import DataQuery, PivotRequest
from app.services.data_processor import processor
from app.services.cache_service import cache_get, cache_set, cached_query_key
from app.services.auth_service import get_current_user, require_role
from app.models.database import User

router = APIRouter()


@router.post("/query")
async def query_data(body: DataQuery, _: User = Depends(get_current_user)):
    key = cached_query_key(
        body.product_id,
        date_from=str(body.date_from),
        date_to=str(body.date_to),
        limit=body.limit,
        offset=body.offset,
        status=body.status,
    )
    cached = await cache_get(key)
    if cached:
        return cached

    result = processor.query(
        product_id=body.product_id,
        date_from=body.date_from,
        date_to=body.date_to,
        test_ids=body.test_ids,
        batch_ids=body.batch_ids,
        status=body.status,
        limit=body.limit,
        offset=body.offset,
    )
    await cache_set(key, result, ttl=120)
    return result


@router.get("/metrics")
async def get_metrics(
    product_id: str = Query(...),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    _: User = Depends(get_current_user),
):
    from datetime import datetime
    df = None
    dt = None
    if date_from:
        df = datetime.fromisoformat(date_from)
    if date_to:
        dt = datetime.fromisoformat(date_to)
    return processor.get_metrics_summary(product_id, date_from=df, date_to=dt)


@router.post("/pivot")
async def pivot_data(body: PivotRequest, _: User = Depends(get_current_user)):
    return processor.pivot(
        product_id=body.product_id,
        index=body.index,
        columns=body.columns,
        values=body.values,
        agg_func=body.agg_func,
        date_from=body.date_from,
        date_to=body.date_to,
    )


@router.get("/export")
async def export_data(
    product_id: str = Query(...),
    format: str = Query("csv"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    _: User = Depends(get_current_user),
):
    from datetime import datetime
    df = datetime.fromisoformat(date_from) if date_from else None
    dt = datetime.fromisoformat(date_to) if date_to else None
    path = processor.export(product_id, fmt=format, date_from=df, date_to=dt)
    media = "text/csv" if format == "csv" else "application/octet-stream"
    return FileResponse(str(path), media_type=media, filename=path.name)


@router.get("/trend")
async def get_trend(
    product_id: str = Query(...),
    metric: str = Query("voltage"),
    period: str = Query("day"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    _: User = Depends(get_current_user),
):
    from datetime import datetime
    df = datetime.fromisoformat(date_from) if date_from else None
    dt = datetime.fromisoformat(date_to) if date_to else None
    return processor.get_trend(product_id, metric=metric, period=period, date_from=df, date_to=dt)


@router.get("/anomalies")
async def detect_anomalies(
    product_id: str = Query(...),
    metric: str = Query("voltage"),
    z_threshold: float = Query(3.0),
    _: User = Depends(get_current_user),
):
    return processor.detect_anomalies(product_id, metric=metric, z_threshold=z_threshold)


@router.post("/sql")
async def sql_query(
    product_id: str,
    sql: str,
    _: User = Depends(require_role("admin")),
):
    return processor.sql_query(product_id, sql)
