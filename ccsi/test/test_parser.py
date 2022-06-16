import pytest
from pydantic import BaseModel, Field

from ccsi.resource.parser import Tag, Entry
from ccsi import init_storage
from ccsi import create_app


@pytest.fixture(autouse=True)
def storage():
    return init_storage()


@pytest.fixture()
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })

    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture(autouse=True)
def onda_id_tag_example():
    return {'source_tag': 'id',
            'tag': 'link',
            'tag_spec': 'onda_id_to_esn',
            'text': '368d412a-811b-4d0f-9673-0ca9484b2c23'}


def test_tag(onda_id_tag_example):
    # TODO: better testing xml tag creation
    tag = Tag(**onda_id_tag_example)
    try:
        tag.xml()
    except Exception as exc:
        assert False, f"Tag creation failed: {exc}"


def test_entry(onda_id_tag_example):
    tag = Tag(**onda_id_tag_example)
    entry = Entry()
    entry.add_tag(tag)
    try:
        entry.xml()
    except Exception as exc:
        assert False, f"Entry creation failed: {exc}"
