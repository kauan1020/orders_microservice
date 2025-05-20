from http import HTTPStatus

from fastapi import FastAPI

from tech.api import orders_router
from tech.interfaces.schemas.message_schema import (
    Message,
)


app = FastAPI()
app.include_router(orders_router.router, prefix='/orders', tags=['orders'])


@app.get('/', status_code=HTTPStatus.OK, response_model=Message)
def read_root():
    return {'message': 'Tech Challenge FIAP - Kauan Silva!   Orders Microservice'}
