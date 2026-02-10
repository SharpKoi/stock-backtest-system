"""API routes for user authentication (registration, login, profile)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, get_current_user, hash_password, verify_password
from app.db import get_db
from app.models.models import User
from app.models.schemas import Token, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user account.

    Args:
        user_data: User registration data (email, password)
        db: Database session

    Returns:
        Created user information (without password)

    Raises:
        HTTPException 400: If email already exists
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        created_at=new_user.created_at.isoformat(),
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login with email and password to receive JWT token.

    Args:
        credentials: Login credentials (email, password)
        db: Database session

    Returns:
        JWT access token

    Raises:
        HTTPException 401: If credentials are invalid
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    # Verify password (use constant-time comparison to prevent timing attacks)
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )

    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user's information.

    This is a protected route that requires authentication.

    Args:
        current_user: Current authenticated user (injected by dependency)

    Returns:
        Current user information
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        created_at=current_user.created_at.isoformat(),
    )
