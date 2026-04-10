from fastapi import APIRouter, Depends
from app.models.schemas import SyntheticDataRequest
from app.services.synthetic_generator import generate_soc_data, save_synthetic_data
from app.config.loader import get_products
from app.services.auth_service import require_role
from app.models.database import User

router = APIRouter()


@router.post("/generate")
async def generate_synthetic(
    body: SyntheticDataRequest,
    _: User = Depends(require_role("admin", "analyst")),
):
    df = generate_soc_data(
        product_id=body.product_id,
        num_records=body.num_records,
        num_batches=body.num_batches,
        start_date=body.start_date,
        end_date=body.end_date,
        anomaly_rate=body.anomaly_rate,
    )
    path = save_synthetic_data(body.product_id, df, append=False)
    return {
        "product_id": body.product_id,
        "records_generated": len(df),
        "output_path": str(path),
        "pass_rate": round(df.filter(df["status"] == "passed").height / len(df) * 100, 2),
    }


@router.post("/generate-all")
async def generate_all_products(
    num_records: int = 50_000,
    _: User = Depends(require_role("admin")),
):
    results = []
    for product_id in get_products():
        df = generate_soc_data(product_id=product_id, num_records=num_records)
        path = save_synthetic_data(product_id, df)
        results.append({"product_id": product_id, "records": len(df), "path": str(path)})
    return {"generated": results}


@router.get("/config")
async def get_generation_config():
    from app.config.loader import get_products
    products = get_products()
    return {
        pid: {
            "metrics": p["metrics"],
            "tests": p["tests"],
        }
        for pid, p in products.items()
    }
