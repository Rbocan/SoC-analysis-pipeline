from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.database import User
from app.models.schemas import Token, LoginRequest, UserCreate, UserOut
from app.services.auth_service import verify_password, hash_password, create_access_token, get_current_user

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": user.username, "role": user.role})
    return Token(access_token=token)


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(User).where(User.username == body.username))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already taken")
    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/profile", response_model=UserOut)
async def profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/permissions")
async def permissions(current_user: User = Depends(get_current_user)):
    perms = {
        "admin": ["read", "write", "delete", "admin"],
        "analyst": ["read", "write"],
        "viewer": ["read"],
    }
    return {"role": current_user.role, "permissions": perms.get(current_user.role, ["read"])}
