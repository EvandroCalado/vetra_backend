from fastapi import APIRouter

from src.account.schemas import UserCreate, UserOut
from src.account.services import create_user
from src.db.config import SessionDep

router = APIRouter()


@router.post('/register/', response_model=UserOut)
async def register_user(session: SessionDep, user: UserCreate):
    return await create_user(session, user)
