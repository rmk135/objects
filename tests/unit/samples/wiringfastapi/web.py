import sys

from typing_extensions import Annotated

from fastapi import FastAPI, Depends
from fastapi import (
    Request,
)  # See: https://github.com/ets-labs/python-dependency-injector/issues/398
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from dependency_injector import containers, providers
from dependency_injector.wiring import inject, Provide


class Service:
    async def process(self) -> str:
        return "Ok"


class Container(containers.DeclarativeContainer):

    service = providers.Factory(Service)


app = FastAPI()
security = HTTPBasic()


@app.api_route("/")
@inject
async def index(service: Service = Depends(Provide[Container.service])):
    result = await service.process()
    return {"result": result}


@app.api_route("/annotated")
@inject
async def annotated(service: Annotated[Service, Depends(Provide[Container.service])]):
    result = await service.process()
    return {"result": result}


@app.get("/auth")
@inject
def read_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    return {"username": credentials.username, "password": credentials.password}


container = Container()
container.wire(modules=[sys.modules[__name__]])
