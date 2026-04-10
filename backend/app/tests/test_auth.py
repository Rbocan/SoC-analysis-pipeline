"""Tests for authentication, registration, and RBAC."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.auth_service import hash_password, verify_password, create_access_token, require_role
from app.models.schemas import UserCreate


# ── Password hashing ─────────────────────────────────────────────────────────

def test_hash_and_verify_password():
    hashed = hash_password("mysecret")
    assert verify_password("mysecret", hashed)
    assert not verify_password("wrong", hashed)


def test_hash_is_not_plaintext():
    assert hash_password("mysecret") != "mysecret"


# ── JWT token ─────────────────────────────────────────────────────────────────

def test_create_access_token_contains_subject():
    from jose import jwt
    from app.settings import settings

    token = create_access_token({"sub": "alice", "role": "viewer"})
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert payload["sub"] == "alice"
    assert payload["role"] == "viewer"


def test_create_access_token_expires():
    from datetime import timedelta
    from jose import jwt
    from app.settings import settings

    token = create_access_token({"sub": "alice"}, expires_delta=timedelta(seconds=10))
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    assert "exp" in payload


# ── UserCreate schema — role field removed ────────────────────────────────────

def test_user_create_has_no_role_field():
    """Clients must not be able to supply a role during self-registration."""
    fields = UserCreate.model_fields
    assert "role" not in fields, "role must not be a client-supplied field on UserCreate"


def test_user_create_valid():
    user = UserCreate(username="bob", email="bob@example.com", password="pass123")
    assert user.username == "bob"


# ── require_role dependency ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_require_role_allows_matching_role():
    admin_user = MagicMock()
    admin_user.role = "admin"

    with patch("app.services.auth_service.get_current_user", return_value=admin_user):
        checker = require_role("admin")
        result = await checker(current_user=admin_user)
        assert result == admin_user


@pytest.mark.asyncio
async def test_require_role_rejects_insufficient_role():
    from fastapi import HTTPException

    viewer_user = MagicMock()
    viewer_user.role = "viewer"

    checker = require_role("admin")
    with pytest.raises(HTTPException) as exc_info:
        await checker(current_user=viewer_user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_role_allows_any_matching_role():
    analyst_user = MagicMock()
    analyst_user.role = "analyst"

    checker = require_role("admin", "analyst")
    result = await checker(current_user=analyst_user)
    assert result == analyst_user


# ── Registration defaults role to viewer ──────────────────────────────────────

@pytest.mark.asyncio
async def test_register_forces_viewer_role():
    """Even if a client somehow passes role in the body, the endpoint must ignore it."""
    from fastapi import HTTPException
    from app.api.auth import register

    mock_user = MagicMock()
    mock_user.username = "charlie"
    mock_user.email = "charlie@example.com"
    mock_user.hashed_password = hash_password("secret")
    mock_user.role = "viewer"
    mock_user.is_active = True

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    mock_db.refresh = AsyncMock(return_value=None)

    body = UserCreate(username="charlie", email="charlie@example.com", password="secret")

    with patch("app.api.auth.User") as MockUser:
        MockUser.return_value = mock_user
        await register(body, db=mock_db)
        # Verify User was constructed with role="viewer"
        _, kwargs = MockUser.call_args
        assert kwargs.get("role") == "viewer", "register must hardcode role='viewer'"


@pytest.mark.asyncio
async def test_register_duplicate_returns_400_not_409():
    """Duplicate username must return 400 (not 409) to prevent username enumeration."""
    from fastapi import HTTPException
    from app.api.auth import register

    existing_user = MagicMock()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_db.execute.return_value = mock_result

    body = UserCreate(username="existing", email="x@example.com", password="pass")

    with pytest.raises(HTTPException) as exc_info:
        await register(body, db=mock_db)
    assert exc_info.value.status_code == 400
