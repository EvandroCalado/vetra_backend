from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_admin: bool = False
    is_verified: bool = False


class UserRegister(UserBase):
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class PasswordChange(BaseModel):
    old_password: str = Field(...)
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if value.lower() == value or value.upper() == value:
            raise ValueError(
                'Password must contain both uppercase and lowercase letters'
            )
        if not any(char.isdigit() for char in value):
            raise ValueError('Password must contain at least one digit')

        return value


class UserOut(UserBase):
    id: int

    model_config = {'from_attributes': True}
