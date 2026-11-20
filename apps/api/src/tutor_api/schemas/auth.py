from typing import Literal

from pydantic import BaseModel, Field, model_validator

from tutor_api.schemas.accounts import UserPublic


class LoginRequest(BaseModel):
    school_code: str | None = Field(default=None, max_length=32)
    username: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=254)
    password: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def require_one_identity(self) -> "LoginRequest":
        if self.email:
            if self.school_code or self.username:
                raise ValueError("Use either an email or a school code and username.")
            return self
        if not self.school_code or not self.username:
            raise ValueError("A school code and username are required.")
        return self


class SessionTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    must_change_password: bool
    user: UserPublic


class RefreshRequest(BaseModel):
    refresh_token: str | None = Field(default=None, max_length=200)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    preferred_language: Literal["en", "rw"] | None = None


class ConsentRequest(BaseModel):
    accepted: Literal[True]
