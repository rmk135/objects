from typing_extensions import Annotated

from flask import Flask, jsonify, request, current_app, session, g
from dependency_injector import containers, providers
from dependency_injector.wiring import inject, Provide

# This is here for testing wiring bypasses these objects without crashing
request, current_app, session, g  # noqa


class Service:
    def process(self) -> str:
        return "OK"


class Container(containers.DeclarativeContainer):

    service = providers.Factory(Service)


app = Flask(__name__)


@app.route("/")
@inject
def index(service: Service = Provide[Container.service]):
    result = service.process()
    return jsonify({"result": result})


@app.route("/annotated")
@inject
def annotated(service: Annotated[Service, Provide[Container.service]]):
    result = service.process()
    return jsonify({"result": result})


container = Container()
container.wire(modules=[__name__])
