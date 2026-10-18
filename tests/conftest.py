import pytest

import helpers  # noqa: F401  (puts tests/fixtures on sys.path)


@pytest.fixture
def docs(tmp_path):
    """previous.docx, draft.docx and deck.pdf, generated fresh per test."""
    import build
    return build.build_all(tmp_path)
