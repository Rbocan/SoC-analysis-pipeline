"""
Report generator: Jinja2 templates → embedded charts → WeasyPrint PDF.
"""
from __future__ import annotations

import base64
import uuid
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import polars as pl
from jinja2 import Environment, FileSystemLoader, select_autoescape
import structlog

from app.settings import settings
from app.config.loader import get_product
from app.services.data_processor import processor

logger = structlog.get_logger()

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _fig_to_b64(fig: plt.Figure) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def _build_trend_chart(product_id: str, metric: str, date_from: Optional[datetime], date_to: Optional[datetime]) -> str:
    try:
        trend = processor.get_trend(product_id, metric=metric, period="day", date_from=date_from, date_to=date_to)
        data = trend["data"]
        if not data:
            raise ValueError("no data")
        dates = [row["timestamp"] for row in data]
        means = [row["mean"] for row in data]
        mins = [row["min"] for row in data]
        maxs = [row["max"] for row in data]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.fill_between(dates, mins, maxs, alpha=0.15, color="#2563eb", label="Min–Max range")
        ax.plot(dates, means, color="#2563eb", linewidth=2, label=f"Avg {metric}")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.set_xlabel("Date", fontsize=11)
        ax.set_ylabel(metric, fontsize=11)
        ax.set_title(f"{metric.capitalize()} Trend", fontsize=13, fontweight="bold")
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        fig.autofmt_xdate()
        return _fig_to_b64(fig)
    except Exception as e:
        logger.warning("Failed to build trend chart", error=str(e))
        return ""


def _build_pass_fail_chart(product_id: str, date_from: Optional[datetime], date_to: Optional[datetime]) -> str:
    try:
        result = processor.query(product_id, date_from=date_from, date_to=date_to, limit=10_000)
        if not result["data"]:
            raise ValueError("no data")

        df = pl.DataFrame(result["data"])
        grouped = (
            df.group_by(["test_id", "status"])
            .agg(pl.len().alias("count"))
            .sort("test_id")
        )

        tests = sorted(df["test_id"].unique().to_list())
        passed = []
        failed = []
        for t in tests:
            sub = grouped.filter(pl.col("test_id") == t)
            p = sub.filter(pl.col("status") == "passed")["count"].sum() if not sub.filter(pl.col("status") == "passed").is_empty() else 0
            f = sub.filter(pl.col("status") == "failed")["count"].sum() if not sub.filter(pl.col("status") == "failed").is_empty() else 0
            passed.append(p)
            failed.append(f)

        x = np.arange(len(tests))
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(x - 0.2, passed, 0.4, label="Passed", color="#16a34a", alpha=0.85)
        ax.bar(x + 0.2, failed, 0.4, label="Failed", color="#dc2626", alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(tests, rotation=30, ha="right")
        ax.set_xlabel("Test ID")
        ax.set_ylabel("Count")
        ax.set_title("Pass / Fail Distribution by Test", fontsize=13, fontweight="bold")
        ax.legend()
        ax.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        return _fig_to_b64(fig)
    except Exception as e:
        logger.warning("Failed to build pass/fail chart", error=str(e))
        return ""


def _get_failing_batches(product_id: str, date_from: Optional[datetime], date_to: Optional[datetime]) -> list[dict]:
    try:
        result = processor.query(product_id, date_from=date_from, date_to=date_to, limit=50_000)
        if not result["data"]:
            return []
        df = pl.DataFrame(result["data"])
        grouped = (
            df.group_by("batch_id")
            .agg([
                pl.len().alias("total"),
                (pl.col("status") == "failed").sum().alias("failed"),
            ])
        )
        grouped = grouped.with_columns(
            (pl.col("failed") / pl.col("total") * 100).round(1).alias("fail_rate")
        ).sort("fail_rate", descending=True)
        return grouped.head(10).to_dicts()
    except Exception as e:
        logger.warning("Failed to get failing batches", error=str(e))
        return []


class ReportGenerator:
    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(["html"]),
        )
        self.env.filters["format_number"] = lambda v: f"{int(v):,}"
        self.reports_dir = Path(settings.reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        product_id: str,
        report_type: str = "daily_validation",
        template_name: str = "daily_validation.html",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> dict[str, Any]:
        report_id = str(uuid.uuid4())[:8].upper()
        product = get_product(product_id)
        if not product:
            raise ValueError(f"Unknown product: {product_id}")

        now = datetime.utcnow()
        if not date_from:
            from datetime import timedelta
            date_from = now - timedelta(days=1)
        if not date_to:
            date_to = now

        # Gather data
        metrics = processor.get_metrics_summary(product_id, date_from=date_from, date_to=date_to)
        metric_stats = {k: v for k, v in metrics.items() if isinstance(v, dict)}
        charts = {
            "trend": _build_trend_chart(product_id, product["metrics"][0]["name"], date_from, date_to),
            "pass_fail": _build_pass_fail_chart(product_id, date_from, date_to),
        }
        failing_batches = _get_failing_batches(product_id, date_from, date_to)

        template = self.env.get_template(template_name)
        html_content = template.render(
            product_id=product_id,
            product_name=product["name"],
            data_source=product.get("data_source", ""),
            generated_at=now.strftime("%Y-%m-%d %H:%M UTC"),
            date_from=date_from.strftime("%Y-%m-%d"),
            date_to=date_to.strftime("%Y-%m-%d"),
            metrics=metrics,
            metric_stats=metric_stats,
            charts=charts,
            failing_batches=failing_batches,
        )

        # Save HTML
        html_path = self.reports_dir / f"{report_id}_{product_id}_{report_type}.html"
        html_path.write_text(html_content)

        # Generate PDF
        pdf_path = html_path.with_suffix(".pdf")
        try:
            from weasyprint import HTML as WP_HTML
            WP_HTML(string=html_content).write_pdf(str(pdf_path))
            logger.info("Generated PDF report", path=str(pdf_path))
        except Exception as e:
            logger.warning("WeasyPrint PDF failed, HTML only", error=str(e))
            pdf_path = None

        return {
            "report_id": report_id,
            "product_id": product_id,
            "report_type": report_type,
            "template": template_name,
            "html_path": str(html_path),
            "pdf_path": str(pdf_path) if pdf_path else None,
            "generated_at": now,
            "status": "completed",
        }


report_generator = ReportGenerator()
