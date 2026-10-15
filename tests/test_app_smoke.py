"""Smoke tests: render every dashboard page headlessly with Streamlit's AppTest and check for exceptions."""

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from pathlib import Path  # noqa: E402

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")
PAGES = ["Overview", "Run Tests", "Failure Analysis", "Before vs After", "Audit Report"]


def fresh_app():
    return AppTest.from_file(APP_PATH, default_timeout=60).run()


def test_app_starts_without_exceptions():
    at = fresh_app()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["result"] is not None
    assert len(at.session_state["result"].records) >= 24


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders(page):
    at = fresh_app()
    at.sidebar.radio(key="page").set_value(page).run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]


def test_rerun_button_and_category_filter_work():
    at = fresh_app()
    at.sidebar.radio(key="page").set_value("Run Tests").run()
    at.multiselect(key="category_filter").set_value(["Emergency escalation"]).run()
    at.button(key="run_btn").click().run()
    assert not at.exception, [e.value for e in at.exception]
    records = at.session_state["result"].records
    assert records and {r["category"] for r in records} == {"Emergency escalation"}
    at.button(key="run_all_btn").click().run()
    assert len(at.session_state["result"].records) >= 24


def test_failure_analysis_case_selector():
    at = fresh_app()
    at.sidebar.radio(key="page").set_value("Failure Analysis").run()
    at.selectbox(key="fa_case").set_value("BEN-03").run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("False positive" in e.value for e in at.error)
