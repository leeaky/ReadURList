import pytest

from readurlist.db import reset_engine


@pytest.fixture(autouse=True)
def _reset_db():
    yield
    reset_engine()
