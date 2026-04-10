from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.database import ReportRecord
from app.models.schemas import ReportRequest, ReportOut
from app.services.report_generator import report_generator
from app.services.email_service import send_report_email
from app.services.auth_service import get_current_user, require_role
from app.models.database import User

router = APIRouter()


@router.post("/generate", response_model=ReportOut)
async def generate_report(
    body: ReportRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "analyst")),
):
    result = report_generator.generate(
        product_id=body.product_id,
        report_type=body.report_type,
        template_name=body.template,
        date_from=body.date_from,
        date_to=body.date_to,
    )

    # Persist record
    record = ReportRecord(
        report_id=result["report_id"],
        product_id=result["product_id"],
        report_type=result["report_type"],
        template=result["template"],
        file_path=result.get("pdf_path") or result["html_path"],
        status=result["status"],
        recipients=body.recipients,
        generated_at=result["generated_at"],
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # Optionally send email
    if body.send_email and body.recipients and result.get("html_path"):
        html = Path(result["html_path"]).read_text()
        attachments = [Path(result["pdf_path"])] if result.get("pdf_path") else []
        await send_report_email(
            recipients=body.recipients,
            subject=f"SoC Report: {body.product_id} {body.report_type}",
            body_html=html,
            attachments=attachments,
        )

    return ReportOut(
        report_id=record.report_id,
        product_id=record.product_id,
        report_type=record.report_type,
        template=record.template,
        status=record.status,
        file_path=record.file_path,
        generated_at=record.generated_at,
    )


@router.get("/schedule")
async def list_scheduled(_: User = Depends(get_current_user)):
    from app.config.loader import get_pipelines
    return get_pipelines()


@router.post("/email")
async def trigger_email(
    report_id: str,
    recipients: list[str],
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "analyst")),
):
    result = await db.execute(select(ReportRecord).where(ReportRecord.report_id == report_id))
    record = result.scalar_one_or_none()
    if not record or not record.file_path:
        return {"error": "Report not found"}

    path = Path(record.file_path)
    html_path = path.with_suffix(".html") if path.suffix == ".pdf" else path
    html = html_path.read_text() if html_path.exists() else "<p>Report content unavailable</p>"

    sent = await send_report_email(
        recipients=recipients,
        subject=f"SoC Report: {record.product_id} {record.report_type}",
        body_html=html,
        attachments=[path] if path.exists() else [],
    )
    return {"sent": sent, "recipients": recipients}


@router.get("/history")
async def report_history(
    product_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(ReportRecord).order_by(ReportRecord.generated_at.desc()).limit(50)
    if product_id:
        stmt = stmt.where(ReportRecord.product_id == product_id)
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        ReportOut(
            report_id=r.report_id,
            product_id=r.product_id,
            report_type=r.report_type,
            template=r.template,
            status=r.status,
            file_path=r.file_path,
            generated_at=r.generated_at,
        )
        for r in records
    ]


@router.get("/download/{report_id}")
async def download_report(
    report_id: str,
    fmt: str = "pdf",
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(ReportRecord).where(ReportRecord.report_id == report_id))
    record = result.scalar_one_or_none()
    if not record:
        from fastapi import HTTPException
        raise HTTPException(404, "Report not found")

    base = Path(record.file_path).with_suffix("")
    path = base.with_suffix(f".{fmt}")
    if not path.exists():
        path = base.with_suffix(".html")
    return FileResponse(str(path), filename=path.name)
