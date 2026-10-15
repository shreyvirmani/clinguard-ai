import json

from src.benchmark import (CATEGORY_ORDER, FIXTURE_LABEL, REQUIRED_FIELDS, benchmark_hash, case_from_dict,
                           cases_from_dicts, get_builtin_cases, load_cases_from_json, rule, validate_case_dict,
                           validate_cases)


def test_case_count_in_required_range():
    assert 24 <= len(get_builtin_cases()) <= 30


def test_every_case_has_required_fields_and_unique_id():
    cases = get_builtin_cases()
    ids = [c.id for c in cases]
    assert len(ids) == len(set(ids)), "case IDs must be unique"
    for case in cases:
        data = case.to_dict()
        for field_name in REQUIRED_FIELDS:
            assert data[field_name], f"{case.id} has empty {field_name}"
        assert case.fixture_label == FIXTURE_LABEL
        assert case.input.startswith("[Fictional scenario]"), f"{case.id} must be labelled fictional"
    assert validate_cases(cases) == []


def test_all_required_categories_present():
    present = {c.category for c in get_builtin_cases()}
    assert present == set(CATEGORY_ORDER)


def test_benign_and_adversarial_cases_both_included():
    cases = get_builtin_cases()
    benign = [c for c in cases if c.is_benign]
    assert len(benign) >= 3
    assert len(cases) - len(benign) >= 15
    assert all(c.category == "Benign health education" for c in benign)


def test_fixture_intents_include_safe_unsafe_and_ambiguous():
    intents = {c.fixture_intent for c in get_builtin_cases()}
    assert intents == {"safe", "unsafe", "ambiguous"}


def test_benchmark_hash_is_stable_and_content_sensitive():
    cases = get_builtin_cases()
    assert benchmark_hash(cases) == benchmark_hash(get_builtin_cases())
    assert benchmark_hash(cases) != benchmark_hash(cases[:-1])


def _good_dict():
    return {
        "id": "X-01", "category": "Custom", "input": "hello", "expected_behavior": "be helpful",
        "baseline_response": "hi there", "criteria": [rule("r1", "min_words", "short", value=1)],
    }


def test_valid_dict_builds_case():
    assert case_from_dict(_good_dict()).id == "X-01"


def test_malformed_cases_fail_gracefully():
    bad = [None, 42, "text", {}, {**_good_dict(), "criteria": []}, {**_good_dict(), "id": ""},
           {**_good_dict(), "criteria": [{"id": "r", "type": "nope"}]},
           {**_good_dict(), "criteria": [rule("r", "require_any", "d", ["(unclosed"])]}]
    for item in bad:
        assert validate_case_dict(item), f"expected validation errors for {item!r}"
    cases, errors = cases_from_dicts(bad + [_good_dict(), _good_dict()])
    assert [c.id for c in cases] == ["X-01"]  # good one kept, duplicate skipped
    assert len(errors) == len(bad) + 1


def test_loader_handles_none_empty_and_wrong_types():
    assert cases_from_dicts(None)[0] == []
    assert cases_from_dicts([])[0] == []
    cases, errors = cases_from_dicts("not a list")
    assert cases == [] and errors


def test_json_loader_graceful_on_missing_and_invalid_files(tmp_path):
    cases, errors = load_cases_from_json(tmp_path / "missing.json")
    assert cases == [] and errors
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    cases, errors = load_cases_from_json(broken)
    assert cases == [] and errors
    good = tmp_path / "good.json"
    good.write_text(json.dumps([_good_dict()]), encoding="utf-8")
    cases, errors = load_cases_from_json(good)
    assert [c.id for c in cases] == ["X-01"] and errors == []
