from fastapi import APIRouter, status

from src.account.deps import AccountServiceDep
from src.account.schemas import UserCreate, UserOut

router = APIRouter()


@router.post(
    '/register/', response_model=UserOut, status_code=status.HTTP_201_CREATED
)
async def register_user(service: AccountServiceDep, user: UserCreate):
    return await service.create(user)
