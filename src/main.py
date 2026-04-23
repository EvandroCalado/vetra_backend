from fastapi import FastAPI

from src.account.routers import router as account_router

app = FastAPI(
    title='Vetra API',
    description='API documentation for Vetra',
)

app.include_router(account_router, prefix='/account', tags=['Account'])
