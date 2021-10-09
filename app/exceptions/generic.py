from fastapi import HTTPException
from fastapi import status

NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Resource not found.",
    headers={"WWW-Authenticate": "Bearer"}
)


ERROR = HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail="An internal server error occurred.",
    headers={"WWW-Authenticate": "Bearer"}
)