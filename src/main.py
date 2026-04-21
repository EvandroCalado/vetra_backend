from fastapi import FastAPI

app = FastAPI(
    title='Vetra API',
    description='API documentation for Vetra',
)


@app.get('/')
async def root():
    return {'message': 'Hello World'}
