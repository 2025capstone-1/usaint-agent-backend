from pydantic import BaseModel


class SigninResponse(BaseModel):
    token_type: str
    access_token: str
