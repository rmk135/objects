import json

# Runtime import to avoid syntax errors in samples on Python < 3.5 and reach top-dir
import os

_TOP_DIR = os.path.abspath(
    os.path.sep.join(
        (
            os.path.dirname(__file__),
            "../",
        )
    ),
)
_SAMPLES_DIR = os.path.abspath(
    os.path.sep.join(
        (
            os.path.dirname(__file__),
            "../samples/",
        )
    ),
)
import sys

sys.path.append(_TOP_DIR)
sys.path.append(_SAMPLES_DIR)

from wiringflask import web


def test_wiring_with_flask():
    client = web.app.test_client()

    with web.app.app_context():
        response = client.get("/")

    assert response.status_code == 200
    assert json.loads(response.data) == {"result": "OK"}


def test_wiring_with_annotated():
    client = web.app.test_client()

    with web.app.app_context():
        response = client.get("/annotated")

    assert response.status_code == 200
    assert json.loads(response.data) == {"result": "OK"}
