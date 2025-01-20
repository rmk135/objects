"""Wiring example."""

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide, inject
from typing import Annotated


class Service: ...


class Container(containers.DeclarativeContainer):

    service = providers.Factory(Service)


# You can place marker on parameter default value
@inject
def main(service: Service = Provide[Container.service]) -> None: ...


# Also, you can place marker with typing.Annotated
@inject
def main_with_annotated(
    service: Annotated[Service, Provide[Container.service]]
) -> None: ...


if __name__ == "__main__":
    container = Container()
    container.wire(modules=[__name__])

    main()
