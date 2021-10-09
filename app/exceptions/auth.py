from fastapi import HTTPException
from fastapi import status

USER_NOT_FOUND = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect username or password",
    headers={"WWW-Authenticate": "Bearer"}
)

INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials.",
    headers={"WWW-Authenticate": "Bearer"}
)

INVALID_SCOPE= HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate permission scope.",
    headers={"WWW-Authenticate": "Bearer"}
)

DISABLED_USER = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Inactive user",
    headers={"WWW-Authenticate": "Bearer"}
)