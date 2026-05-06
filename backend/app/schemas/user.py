from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    designation: str
    department: str
    role: UserRole
    is_active: bool
