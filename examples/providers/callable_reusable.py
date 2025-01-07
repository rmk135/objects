"""`Callable` provider example with configurable parameters"""

import passlib.hash

from dependency_injector import containers, providers
from dependency_injector.wiring import Provide


class Service:
    def __init__(self, hasher):
        self.hasher = hasher

    def hash(self, value):
        return self.hasher(value)


class Container(containers.DeclarativeContainer):

    password_hasher = providers.Callable(
        passlib.hash.sha256_crypt.hash,
        salt_size=16,
        rounds=10000,
    )
    password_verifier = providers.Callable(passlib.hash.sha256_crypt.verify)

    service = providers.Factory(
        Service,
        hasher=password_hasher.provider
    )


if __name__ == "__main__":
    service: Service = Provide["service"]
    container = Container()
    container.wire(modules=[__name__])

    hashed_password = service.hash("super secret")
    assert container.password_verifier("super secret", hashed_password)
