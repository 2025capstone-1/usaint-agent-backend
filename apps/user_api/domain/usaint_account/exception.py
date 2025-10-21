from fastapi import status, HTTPException


class UsaintAccountNotFound(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="U-Saint Account Not Found",
        )


class UsaintAccountAlreadyExists(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="U-Saint Account already exists for this user",
        )
