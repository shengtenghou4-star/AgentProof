from agentproof.security_controls import run_security_controls


def _documents(root):
    (root / "docs").mkdir(exist_ok=True)
    (root / "SECURITY.md").write_text("security", encoding="utf-8")
    (root / "docs" / "threat-model.md").write_text("threats", encoding="utf-8")
    (root / "docs" / "EVIDENCE_CLAIMS.md").write_text("claims", encoding="utf-8")


def test_security_controls_pass_safe_source(tmp_path):
    _documents(tmp_path)
    source = tmp_path / "src"
    source.mkdir()
    (source / "safe.py").write_text(
        "import subprocess\nsubprocess.run(['python', '--version'], check=False)\n",
        encoding="utf-8",
    )
    report = run_security_controls(tmp_path)
    assert report.passed is True
    assert report.scanned_files == 1
    assert report.findings == ()


def test_security_controls_block_shell_and_eval(tmp_path):
    _documents(tmp_path)
    source = tmp_path / "src"
    source.mkdir()
    (source / "unsafe.py").write_text(
        "import subprocess\nsubprocess.run('echo bad', shell=True)\neval('1 + 1')\n",
        encoding="utf-8",
    )
    report = run_security_controls(tmp_path)
    controls = {finding.control for finding in report.findings}
    assert report.passed is False
    assert {"SHELL-001", "CODE-001"} <= controls


def test_security_controls_require_boundary_documents(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "safe.py").write_text("value = 1\n", encoding="utf-8")
    report = run_security_controls(tmp_path)
    assert report.passed is False
    assert any(finding.control == "DOC-001" for finding in report.findings)
