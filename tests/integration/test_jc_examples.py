# tests/integration/test_jc_examples.py
"""Guard examples/jc_parsers.py against rot.

Requires the optional jc extra; skipped when it is not installed
(``pip install clinch[jc]``). Real-tool tests are also skipped when the
underlying tool is unavailable.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

jc = pytest.importorskip("jc")

import jc_parsers  # noqa: E402


def test_csv_example_through_wrapper() -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
        fh.write("name,age\nfoo,42\nbar,7\n")
        path = Path(fh.name)
    try:
        result = jc_parsers.CsvWrapper().read(path)
    finally:
        path.unlink()

    assert [row.name for row in result.successes] == ["foo", "bar"]
    assert all(isinstance(row.age, int) for row in result.successes)  # jc str -> int
    assert not result.has_failures


@pytest.mark.skipif(shutil.which("ps") is None, reason="ps not available")
def test_ps_example_through_wrapper() -> None:
    result = jc_parsers.PsWrapper().processes()

    assert result.success_count >= 1
    assert result.failure_count == 0
    assert all(isinstance(p.pid, int) and isinstance(p.rss, int) for p in result.successes)
    assert any(p.pid == 1 for p in result.successes)  # init is always present


@pytest.mark.skipif(shutil.which("df") is None, reason="df not available")
def test_df_example_through_wrapper() -> None:
    result = jc_parsers.DfWrapper().usage()

    assert result.success_count >= 1
    assert result.failure_count == 0
    assert any(fs.mounted_on == "/" for fs in result.successes)  # root fs always present
    assert all(fs.use_percent >= 0 for fs in result.successes)


def test_example_main_runs_to_completion() -> None:
    """The example's entry point (csv + ps + df) completes without error."""
    if shutil.which("ps") is None or shutil.which("df") is None:
        pytest.skip("ps/df required")
    jc_parsers.main()
