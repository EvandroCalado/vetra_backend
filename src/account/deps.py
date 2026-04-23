from typing import Annotated

from fastapi import Depends

from src.account.services import AccountService
from src.db.config import SessionDep


def get_account_service(session: SessionDep) -> AccountService:
    return AccountService(session)


AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]
