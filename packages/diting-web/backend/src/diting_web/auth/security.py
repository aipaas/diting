"""Security utilities (JWT tokens and password hashing)."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from diting_web.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(
    subject: str | Any,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT access token.
    
    Args:
        subject: Token subject (usually user ID)
        expires_delta: Expiration time delta
        
    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
    }
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def create_refresh_token(
    subject: str | Any,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create JWT refresh token.
    
    Args:
        subject: Token subject (usually user ID)
        expires_delta: Expiration time delta
        
    Returns:
        Encoded JWT refresh token
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Refresh token有效期默认为7天
        expire = datetime.now(timezone.utc) + timedelta(days=7)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
    }
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[str]:
    """Decode JWT access token.
    
    Args:
        token: JWT token string
        
    Returns:
        Subject (user ID) if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        
        # 验证token类型
        token_type: str = payload.get("type", "access")
        if token_type != "access":
            return None
            
        subject: str = payload.get("sub")
        return subject
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[str]:
    """Decode JWT refresh token.
    
    Args:
        token: JWT refresh token string
        
    Returns:
        Subject (user ID) if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        
        # 验证token类型
        token_type: str = payload.get("type")
        if token_type != "refresh":
            return None
            
        subject: str = payload.get("sub")
        return subject
    except JWTError:
        return None

