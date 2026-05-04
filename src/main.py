from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app.include_router(account_router, prefix='/api/v1/account', tags=['Account'])
