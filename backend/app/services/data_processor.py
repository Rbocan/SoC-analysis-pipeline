"""
High-performance data processing using Polars (primary) + DuckDB (SQL queries).
Targets: <1s for 1M rows, <5s pivot on 10M rows.
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import duckdb
import polars as pl
import pandas as pd
import numpy as np
from scipy import stats
import structlog

from app.settings import settings

logger = structlog.get_logger()


class DataProcessor:
    def __init__(self):
        self.parquet_dir = Path(settings.parquet_dir)
        self._duck = duckdb.connect(":memory:")

    def _parquet_path(self, product_id: str) -> Path:
        return self.parquet_dir / f"{product_id}.parquet"

    def _scan(self, product_id: str) -> pl.LazyFrame:
        path = self._parquet_path(product_id)
        if not path.exists():
            raise FileNotFoundError(f"No data for product '{product_id}'. Generate synthetic data first.")
        return pl.scan_parquet(str(path))

    # ── Query ────────────────────────────────────────────────────────────────

    def query(
        self,
        product_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        test_ids: Optional[list[str]] = None,
        batch_ids: Optional[list[str]] = None,
        status: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> dict[str, Any]:
        lf = self._scan(product_id)

        if date_from:
            lf = lf.filter(pl.col("timestamp") >= date_from)
        if date_to:
            lf = lf.filter(pl.col("timestamp") <= date_to)
        if test_ids:
            lf = lf.filter(pl.col("test_id").is_in(test_ids))
        if batch_ids:
            lf = lf.filter(pl.col("batch_id").is_in(batch_ids))
        if status:
            lf = lf.filter(pl.col("status") == status)

        total = lf.select(pl.len()).collect().item()
        df = lf.slice(offset, limit).collect()

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "data": df.to_dicts(),
        }

    # ── Metrics summary ──────────────────────────────────────────────────────

    def get_metrics_summary(self, product_id: str, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> dict[str, Any]:
        lf = self._scan(product_id)
        if date_from:
            lf = lf.filter(pl.col("timestamp") >= date_from)
        if date_to:
            lf = lf.filter(pl.col("timestamp") <= date_to)

        numeric_cols = [
            c for c, t in zip(lf.columns, lf.dtypes)
            if t in (pl.Float64, pl.Float32, pl.Int64, pl.Int32)
            and c not in ("id",)
        ]

        aggs = []
        for col in numeric_cols:
            aggs.extend([
                pl.col(col).mean().alias(f"{col}_mean"),
                pl.col(col).min().alias(f"{col}_min"),
                pl.col(col).max().alias(f"{col}_max"),
                pl.col(col).std().alias(f"{col}_std"),
            ])

        summary_df = lf.select(aggs).collect()
        row = summary_df.row(0, named=True)

        metrics: dict[str, Any] = {}
        for col in numeric_cols:
            metrics[col] = {
                "mean": round(row[f"{col}_mean"], 4) if row[f"{col}_mean"] is not None else None,
                "min": round(row[f"{col}_min"], 4) if row[f"{col}_min"] is not None else None,
                "max": round(row[f"{col}_max"], 4) if row[f"{col}_max"] is not None else None,
                "std": round(row[f"{col}_std"], 4) if row[f"{col}_std"] is not None else None,
            }

        # Pass rate
        total = lf.select(pl.len()).collect().item()
        passed = lf.filter(pl.col("status") == "passed").select(pl.len()).collect().item()
        metrics["pass_rate"] = round(passed / total * 100, 2) if total > 0 else 0
        metrics["total_records"] = total

        return metrics

    # ── Pivot ────────────────────────────────────────────────────────────────

    def pivot(
        self,
        product_id: str,
        index: str = "batch_id",
        columns: str = "test_id",
        values: str = "voltage",
        agg_func: str = "mean",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> dict[str, Any]:
        lf = self._scan(product_id)
        if date_from:
            lf = lf.filter(pl.col("timestamp") >= date_from)
        if date_to:
            lf = lf.filter(pl.col("timestamp") <= date_to)

        df = lf.collect()

        agg_expr = {
            "mean": pl.col(values).mean(),
            "min": pl.col(values).min(),
            "max": pl.col(values).max(),
            "sum": pl.col(values).sum(),
            "count": pl.col(values).count(),
        }.get(agg_func, pl.col(values).mean())

        grouped = df.group_by([index, columns]).agg(agg_expr.alias(values))

        try:
            pivoted = grouped.pivot(index=index, on=columns, values=values)
        except Exception as e:
            logger.warning("Polars pivot failed, falling back to pandas", error=str(e))
            pdf = grouped.to_pandas()
            pivoted_pd = pdf.pivot_table(index=index, columns=columns, values=values, aggfunc=agg_func)
            pivoted_pd.columns = [str(c) for c in pivoted_pd.columns]
            pivoted_pd = pivoted_pd.reset_index()
            return {
                "index": index,
                "columns": columns,
                "values": values,
                "agg_func": agg_func,
                "data": pivoted_pd.fillna(0).to_dict("records"),
                "shape": list(pivoted_pd.shape),
            }

        return {
            "index": index,
            "columns": columns,
            "values": values,
            "agg_func": agg_func,
            "data": pivoted.fill_null(0).to_dicts(),
            "shape": list(pivoted.shape),
        }

    # ── DuckDB ad-hoc SQL ────────────────────────────────────────────────────

    def sql_query(self, product_id: str, sql: str) -> dict[str, Any]:
        """Execute a safe, read-only SQL query via DuckDB over parquet data."""
        path = self._parquet_path(product_id)
        if not path.exists():
            raise FileNotFoundError(f"No data for product '{product_id}'.")

        # Prevent mutation queries
        forbidden = ("insert", "update", "delete", "drop", "create", "alter", "truncate")
        if any(kw in sql.lower() for kw in forbidden):
            raise ValueError("Only SELECT queries are allowed.")

        conn = duckdb.connect(":memory:")
        conn.execute(f"CREATE VIEW measurements AS SELECT * FROM read_parquet('{path}')")
        result = conn.execute(sql).fetchdf()
        return {"data": result.to_dict("records"), "columns": list(result.columns)}

    # ── Trend ────────────────────────────────────────────────────────────────

    def get_trend(
        self,
        product_id: str,
        metric: str = "voltage",
        period: str = "day",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> dict[str, Any]:
        lf = self._scan(product_id)
        if date_from:
            lf = lf.filter(pl.col("timestamp") >= date_from)
        if date_to:
            lf = lf.filter(pl.col("timestamp") <= date_to)

        trunc_map = {"hour": "1h", "day": "1d", "week": "1w"}
        every = trunc_map.get(period, "1d")

        df = (
            lf.sort("timestamp")
            .group_by_dynamic("timestamp", every=every)
            .agg([
                pl.col(metric).mean().alias("mean"),
                pl.col(metric).min().alias("min"),
                pl.col(metric).max().alias("max"),
                pl.col(metric).std().alias("std"),
                pl.len().alias("count"),
            ])
            .collect()
        )

        return {"metric": metric, "period": period, "data": df.to_dicts()}

    # ── Export ───────────────────────────────────────────────────────────────

    def export(self, product_id: str, fmt: str = "csv", date_from: Optional[datetime] = None, date_to: Optional[datetime] = None) -> Path:
        lf = self._scan(product_id)
        if date_from:
            lf = lf.filter(pl.col("timestamp") >= date_from)
        if date_to:
            lf = lf.filter(pl.col("timestamp") <= date_to)

        df = lf.collect()
        out_dir = Path(settings.reports_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        out_path = out_dir / f"{product_id}_export_{ts}.{fmt}"

        if fmt == "csv":
            df.write_csv(str(out_path))
        elif fmt == "parquet":
            df.write_parquet(str(out_path))
        else:
            raise ValueError(f"Unsupported format: {fmt}")

        logger.info("Exported data", product=product_id, format=fmt, rows=len(df), path=str(out_path))
        return out_path

    # ── Anomaly detection ────────────────────────────────────────────────────

    def detect_anomalies(self, product_id: str, metric: str, z_threshold: float = 3.0) -> dict[str, Any]:
        lf = self._scan(product_id)
        df = lf.select(["batch_id", "test_id", "timestamp", metric, "status"]).collect()
        values = df[metric].to_numpy()

        try:
            from sklearn.ensemble import IsolationForest
            clf = IsolationForest(n_estimators=100, contamination=0.03, random_state=42, n_jobs=-1)
            clf.fit(values.reshape(-1, 1))
            anomaly_mask = clf.predict(values.reshape(-1, 1)) == -1
            method = "IsolationForest"
        except ImportError:
            anomaly_mask = np.abs(stats.zscore(values)) > z_threshold
            method = "zscore"

        anomalies = df.filter(pl.Series(anomaly_mask)).to_dicts()
        return {
            "metric": metric,
            "method": method,
            "z_threshold": z_threshold,
            "total_records": len(df),
            "anomaly_count": int(anomaly_mask.sum()),
            "anomalies": anomalies[:100],
        }


# Module-level singleton
processor = DataProcessor()
