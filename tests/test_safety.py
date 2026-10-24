"""Every red-team scenario is a regression test."""
import pytest

from tests.safety_scenarios import SCENARIOS


@pytest.mark.parametrize("sid,title,entry,expected,fn,mitigation", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_safety_scenario(sid, title, entry, expected, fn, mitigation):
    result = fn()
    assert result["passed"], f"{sid} {title}: {result['actual']}"
