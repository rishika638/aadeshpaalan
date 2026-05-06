from app.utils.org_mapping import map_responsibility_to_designation


def test_org_mapping_case_insensitive_substring_match() -> None:
    res = map_responsibility_to_designation("The Revenue Department shall file a report.")
    assert res.designation == "Deputy Secretary, Revenue"
    assert res.requires_human_review is False


def test_org_mapping_fallback_requires_review() -> None:
    res = map_responsibility_to_designation("The competent authority shall ensure compliance.")
    assert res.designation == "Concerned Authority"
    assert res.requires_human_review is True

