from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.account.exceptions import DomainError
from src.account.routers import router as account_router
from src.db.settings import settings

app = FastAPI(
    title='Vetra API',
    description='API documentation for Vetra',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(
        status_code=exc.status_code,
        content={'detail': exc.detail},
    )


app.include_router(account_router, prefix='/api/v1/account', tags=['Account'])
