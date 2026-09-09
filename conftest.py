import pytest

from continuum.app import create_app
from pathlib import Path

"""
BASEDIR = os.getenv("BASEDIR")

# BASEDIR = "/data/digital_collections_ocfl/ark_data/"
# DB = Path("/data/local/app_data/project.db")
DB = os.getenv("CONTINUUMDB")
#
#
TURTLE_FILE = os.getenv("CONTINUUM_TURTLE")
#
"""

BASEDIR = Path(__file__).parent / "tests/"
DB_PATH = Path(__file__).parent / "tests" / "test.db"
TURTLE_FILE = Path(__file__).parent / "tests" / "test_data.ttl"


# db_path=DB, basedir=BASEDIR, turtle_file=TURTLE_FILE
@pytest.fixture()
def app():
    app = create_app(
        basedir=BASEDIR,
        db_path=DB_PATH,
        turtle_file=TURTLE_FILE,
    )
    app.config.update({"TESTING": True})

    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()
