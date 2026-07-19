import json
import xml.etree.ElementTree as ET

from agentproof.formats import render_junit, render_sarif
from agentproof.models import AuditReport, Claim, Finding, FindingStatus


def _report():
    claim = Claim("C1", "all_tests_passed", "All tests passed.")
    finding = Finding(claim, FindingStatus.VERIFIED, "2 tests passed", (0,))
    return AuditReport("demo", [finding], event_count=1, integrity_ok=True)


def test_sarif_renderer_is_valid_json():
    payload = json.loads(render_sarif(_report()))
    assert payload["version"] == "2.1.0"
    assert payload["runs"][0]["results"][0]["ruleId"] == "agentproof/all_tests_passed"


def test_junit_renderer_is_valid_xml():
    root = ET.fromstring(render_junit(_report()))
    assert root.tag == "testsuite"
    assert root.attrib["tests"] == "1"
    assert root.attrib["failures"] == "0"
