"""
Bootstrap script: create admin user + generate synthetic data for all products.
Run once after first docker-compose up:

    docker exec soc-backend python -m app.seed
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


async def create_admin():
    from app.database import AsyncSessionLocal
    from app.models.database import User
    from app.services.auth_service import hash_password
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none():
            print("Admin user already exists")
            return
        user = User(
            username="admin",
            email="admin@soc-dashboard.local",
            hashed_password=hash_password("admin123"),
            role="admin",
        )
        db.add(user)
        await db.commit()
        print("Created admin user (admin / admin123)")


def generate_data():
    from app.config.loader import load_products_config
    from app.services.synthetic_generator import generate_soc_data, save_synthetic_data

    load_products_config()
    products = load_products_config()
    for product_id in products:
        print(f"Generating 100,000 records for {product_id}…")
        df = generate_soc_data(product_id, num_records=100_000, num_batches=100)
        path = save_synthetic_data(product_id, df)
        pass_rate = df.filter(df["status"] == "passed").height / len(df) * 100
        print(f"  → {path} ({pass_rate:.1f}% pass rate)")


async def main():
    from app.database import engine, Base
    import app.models.database  # noqa: F401 — registers ORM models with Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created")

    await create_admin()
    generate_data()
    print("\nSeed complete. Start the app and navigate to http://localhost:3000")


if __name__ == "__main__":
    asyncio.run(main())
