"""Unit checks for tools/measure_raster_build.py that need no TeX installation."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("measure", ROOT / "tools/measure_raster_build.py")
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)

with tempfile.TemporaryDirectory() as name:
    tmp = Path(name)

    # A step whose time report is missing records null and warns, never 0.
    steps = []
    run = measure.timed_run(lambda command, **kwargs: None, steps, tmp)
    warning = io.StringIO()
    with contextlib.redirect_stderr(warning):
        run(["latexmk", "x.tex"])
    assert steps == [{"stage": "latex", "seconds": steps[0]["seconds"], "rss": None}], steps
    assert "RSS recorded as null" in warning.getvalue()
    summary = measure.summarize({"total_seconds": 1.0, "peak_disk_bytes": 0, "steps": steps})
    assert summary["rss_mib"] is None and measure.mib(None) == "n/a"
    mixed = steps + [{"stage": "export", "seconds": 0.1, "rss": 2**20}]
    assert measure.summarize({"total_seconds": 1.0, "peak_disk_bytes": 0, "steps": mixed})["rss_mib"] == 1.0

    # Engine identity names its source in every case.
    frozen = tmp / "frozen"; frozen.mkdir()
    assert measure.engine_identity(frozen) == ("unknown (frozen)", "directory name")
    (frozen / "engine-commit.txt").write_text("abc123\n")
    assert measure.engine_identity(frozen) == ("abc123", "engine-commit.txt")
    checkout = tmp / "checkout"; checkout.mkdir()
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    subprocess.run(["git", "-C", str(checkout), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
                    "--allow-empty", "--no-verify", "-m", "chore(test): empty"], check=True)
    revision, source = measure.engine_identity(checkout)
    assert source == "git" and len(revision) == 40

    # A tracked change marks the checkout dirty; untracked files do not.
    (checkout / "file.txt").write_text("a\n")
    assert not measure.git_dirty(checkout)
    subprocess.run(["git", "-C", str(checkout), "add", "file.txt"], check=True)
    assert measure.git_dirty(checkout)

    # The report is replaced whole, so a reader never sees a partial file.
    out = tmp / "out"
    measure.write_report(out, {"complete": False, "builds": {"a": 1}})
    measure.write_report(out, {"complete": True, "builds": {"a": 1, "b": 2}})
    assert json.loads((out / "results.json").read_text())["complete"] is True
    assert not (out / "results.json.tmp").exists()

print("measure_raster_build checks passed")
