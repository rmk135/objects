from httpx import ASGITransport, AsyncClient
from pytest import fixture, mark
from pytest_asyncio import fixture as aio_fixture

# Runtime import to avoid syntax errors in samples on Python < 3.5 and reach top-dir
import os

_SAMPLES_DIR = os.path.abspath(
    os.path.sep.join(
        (
            os.path.dirname(__file__),
            "../samples/",
        )
    ),
)
import sys

sys.path.append(_SAMPLES_DIR)


from wiringfastapi import web


@aio_fixture
async def async_client():
    client = AsyncClient(transport=ASGITransport(app=web.app), base_url="http://test")
    yield client
    await client.aclose()


@mark.asyncio
async def test_depends_marker_injection(async_client: AsyncClient):
    class ServiceMock:
        async def process(self):
            return "Foo"

    with web.container.service.override(ServiceMock()):
        response = await async_client.get("/")

    assert response.status_code == 200
    assert response.json() == {"result": "Foo"}


@mark.asyncio
async def test_depends_with_annotated(async_client: AsyncClient):
    class ServiceMock:
        async def process(self):
            return "Foo"

    with web.container.service.override(ServiceMock()):
        response = await async_client.get("/")

    assert response.status_code == 200
    assert response.json() == {"result": "Foo"}


@mark.asyncio
async def test_depends_injection(async_client: AsyncClient):
    response = await async_client.get("/auth", auth=("john_smith", "secret"))
    assert response.status_code == 200
    assert response.json() == {"username": "john_smith", "password": "secret"}
