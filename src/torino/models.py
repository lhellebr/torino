from dataclasses import dataclass, field


@dataclass
class TriageIssue:
    key: str
    summary: str
    description: str | None
    issue_type: str
    status: str
    priority: str | None
    severity: str | None
    components: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    fix_versions: list[str] = field(default_factory=list)
    affects_versions: list[str] = field(default_factory=list)
    regression: str | None = None
    regression_from_description: str | None = None
    reporter: str | None = None
    assignee: str | None = None
    url: str | None = None
