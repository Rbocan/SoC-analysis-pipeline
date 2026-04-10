from fastapi import APIRouter, Depends, HTTPException
from app.config.loader import get_products, get_product, reload_configs
from app.models.schemas import ProductOut
from app.services.auth_service import get_current_user, require_role
from app.models.database import User

router = APIRouter()


@router.get("/", response_model=list[ProductOut])
async def list_products():
    products = get_products()
    return [ProductOut(**p) for p in products.values()]


@router.get("/{product_id}", response_model=ProductOut)
async def get_product_detail(product_id: str):
    product = get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return ProductOut(**product)


@router.post("/reload")
async def reload_product_configs(_: User = Depends(require_role("admin"))):
    """Hot-reload YAML configs without restart (admin only)."""
    reload_configs()
    return {"message": "Configs reloaded successfully"}
