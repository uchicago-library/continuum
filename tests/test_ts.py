from continuum.triplestore import TripleStore, RdfFormat
from continuum.app import construct_file_arguments
from pathlib import Path
import pytest

from pyoxigraph import Store

import shutil


def create_store():
    db_path = "tests/test.db"
    shutil.rmtree(db_path)

    temp_store = Store(db_path)
    with open("tests/test_data.ttl", "r") as tp:
        temp_store.bulk_load(tp, format=RdfFormat.TURTLE)
    temp_store.flush()
    return db_path


@pytest.fixture
def triplestore(app):
    db_path = create_store()
    ts = TripleStore(Path(db_path), app.logger)
    return ts


def test_store_creation(triplestore):
    assert isinstance(triplestore, TripleStore)


def test_retriveal(triplestore, app):
    file_obj = construct_file_arguments(app.logger, "b2k86bv2x025", "mets")

    results = triplestore.find_file_path(file_obj)
    assert len(results) == 1
