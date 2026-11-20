from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

RoleName = Literal["admin", "teacher", "student"]


class UserPublic(BaseModel):
    id: UUID
    school_id: UUID
    role: RoleName
    username: str
    email: str | None
    display_name: str
    preferred_language: Literal["en", "rw"]
    must_change_password: bool
    is_super_admin: bool
    is_active: bool


class UserCreated(UserPublic):
    temporary_password: str | None = None


class UserCreate(BaseModel):
    school_id: UUID | None = None
    role: RoleName
    username: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    display_name: str = Field(min_length=1, max_length=160)
    email: str | None = Field(default=None, max_length=254)
    password: str | None = Field(default=None, min_length=10, max_length=200)
    preferred_language: Literal["en", "rw"] = "en"


class UserUpdate(BaseModel):
    is_active: bool | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=160)


class PasswordResetResult(BaseModel):
    user_id: UUID
    temporary_password: str


class SchoolPublic(BaseModel):
    id: UUID
    name: str
    code: str
    teacher_can_view_transcripts: bool


class SchoolCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9-]+$")


class SchoolUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    teacher_can_view_transcripts: bool | None = None


class ClassPublic(BaseModel):
    id: UUID
    school_id: UUID
    teacher_id: UUID
    name: str
    subject_code: str


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    subject_code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]+$")
    teacher_id: UUID | None = None


class EnrollRequest(BaseModel):
    student_id: UUID


class ImportedStudent(BaseModel):
    id: UUID
    username: str
    display_name: str
    temporary_password: str


class ImportResult(BaseModel):
    created: list[ImportedStudent]


class UserPage(BaseModel):
    items: list[UserPublic]
    next_cursor: str | None


class SchoolPage(BaseModel):
    items: list[SchoolPublic]
    next_cursor: str | None


class ClassPage(BaseModel):
    items: list[ClassPublic]
    next_cursor: str | None


class AccountExport(BaseModel):
    user: UserPublic
    classes: list[ClassPublic]
    conversation_count: int
    exported_at: datetime
