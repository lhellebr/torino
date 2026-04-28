from torino.models import TriageIssue
from torino.triage.validators import validate_issue, Check


FULL_DESCRIPTION = (
    "*Description of problem:*\n"
    "Something is broken\n\n"
    "*How reproducible:*\n"
    "Always\n\n"
    "*Is this issue a regression from an earlier version:*\n"
    " Yes\n\n"
    "*Steps to Reproduce:*\n"
    "# Do this\n"
    "# Do that\n\n"
    "*Actual behavior:*\n"
    "It explodes\n\n"
    "*Expected behavior:*\n"
    "It should not explode\n"
)


def _make_issue(**overrides):
    defaults = dict(
        key="SAT-99999",
        summary="Test issue",
        description=FULL_DESCRIPTION,
        issue_type="Bug",
        status="New",
        priority="Major",
        severity="Important",
        components=["Authentication"],
        labels=[],
        fix_versions=[],
        affects_versions=[],
        regression="Yes",
        regression_from_description="Yes",
        reporter="testuser",
        assignee=None,
        url="https://example.atlassian.net/browse/SAT-99999",
    )
    defaults.update(overrides)
    return TriageIssue(**defaults)


def _find_check(checks: list[Check], field: str) -> Check | None:
    return next((c for c in checks if c.field == field), None)


def _find_checks(checks: list[Check], field: str) -> list[Check]:
    return [c for c in checks if c.field == field]


class TestSummary:
    def test_ok(self):
        checks = validate_issue(_make_issue())
        assert _find_check(checks, "Summary").status == "ok"

    def test_empty(self):
        checks = validate_issue(_make_issue(summary=""))
        assert _find_check(checks, "Summary").status == "missing"

    def test_whitespace(self):
        checks = validate_issue(_make_issue(summary="   "))
        assert _find_check(checks, "Summary").status == "missing"


class TestPriority:
    def test_ok(self):
        checks = validate_issue(_make_issue(priority="Major"))
        assert _find_check(checks, "Priority").status == "ok"

    def test_undefined(self):
        checks = validate_issue(_make_issue(priority="Undefined"))
        assert _find_check(checks, "Priority").status == "missing"

    def test_none(self):
        checks = validate_issue(_make_issue(priority=None))
        assert _find_check(checks, "Priority").status == "missing"


class TestSeverity:
    def test_ok(self):
        checks = validate_issue(_make_issue(severity="Critical"))
        assert _find_check(checks, "Severity").status == "ok"

    def test_missing(self):
        checks = validate_issue(_make_issue(severity=None))
        assert _find_check(checks, "Severity").status == "missing"


class TestComponents:
    def test_ok(self):
        checks = validate_issue(_make_issue(components=["Authentication"]))
        assert _find_check(checks, "Component").status == "ok"

    def test_missing(self):
        checks = validate_issue(_make_issue(components=[]))
        assert _find_check(checks, "Component").status == "missing"


class TestRegression:
    def test_field_set(self):
        checks = validate_issue(_make_issue(regression="Yes"))
        assert _find_check(checks, "Regression").status == "ok"

    def test_field_unset_description_has_it(self):
        checks = validate_issue(_make_issue(
            regression=None, regression_from_description="Yes",
        ))
        c = _find_check(checks, "Regression")
        assert c.status == "warning"
        assert "description says" in c.message

    def test_both_unset(self):
        checks = validate_issue(_make_issue(
            regression=None, regression_from_description=None,
        ))
        assert _find_check(checks, "Regression").status == "missing"


class TestDescription:
    def test_full_template(self):
        checks = validate_issue(_make_issue(description=FULL_DESCRIPTION))
        desc_checks = _find_checks(checks, "Description")
        assert len(desc_checks) == 1
        assert desc_checks[0].status == "ok"

    def test_empty(self):
        checks = validate_issue(_make_issue(description=""))
        desc_checks = _find_checks(checks, "Description")
        assert any(c.status == "missing" for c in desc_checks)

    def test_none(self):
        checks = validate_issue(_make_issue(description=None))
        desc_checks = _find_checks(checks, "Description")
        assert any(c.status == "missing" for c in desc_checks)

    def test_missing_section(self):
        partial = (
            "*Description of problem:*\n"
            "Something is broken\n"
        )
        checks = validate_issue(_make_issue(description=partial))
        desc_checks = _find_checks(checks, "Description")
        warnings = [c for c in desc_checks if c.status == "warning"]
        assert len(warnings) > 0
        missing_names = [c.message for c in warnings]
        assert any("Steps to Reproduce" in m for m in missing_names)


class TestLabels:
    def test_no_special_labels(self):
        checks = validate_issue(_make_issue(labels=[]))
        assert _find_checks(checks, "Labels") == []

    def test_triaged(self):
        checks = validate_issue(_make_issue(labels=["triaged"]))
        label_checks = _find_checks(checks, "Labels")
        assert any("triaged" in c.message for c in label_checks)

    def test_needinfo(self):
        checks = validate_issue(_make_issue(labels=["NEEDINFO"]))
        label_checks = _find_checks(checks, "Labels")
        assert any("NEEDINFO" in c.message for c in label_checks)
