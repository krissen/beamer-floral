"""Unit checks for tools/measure_raster_build.py that need no TeX installation.

Each fix for issue #25 has a case here that fails without it.
"""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location("measure", ROOT / "tools/measure_raster_build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_main(module, argv):
    """Run main() and return (stdout, stderr, exception or None)."""
    saved = sys.argv
    out, err = io.StringIO(), io.StringIO()
    sys.argv = ["measure", *argv]
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            module.main()
        return out.getvalue(), err.getvalue(), None
    except Exception as error:  # noqa: BLE001 - the test inspects any failure
        return out.getvalue(), err.getvalue(), error
    finally:
        sys.argv = saved


def read(out):
    return json.loads((out / "results.json").read_text())


def fake_result(rss):
    steps = [{"stage": "latex", "seconds": 1.0, "rss": rss}, {"stage": "export", "seconds": 0.5, "rss": rss},
             {"stage": "latex", "seconds": 0.5, "rss": rss}]
    return {"total_seconds": 2.5, "peak_disk_bytes": 2**20, "steps": steps}


with tempfile.TemporaryDirectory() as name:
    tmp = Path(name)
    source = ROOT / "test/growth-raster.tex"
    frozen = tmp / "frozen"
    frozen.mkdir()

    # 1. Missing and unreadable time reports record null RSS and warn.
    measure = load()
    for label, setup in (("missing", lambda path: None),
                         ("unreadable", lambda path: path.write_bytes(b"\xff\xfe\x00bad"))):
        steps = []
        scratch = tmp / f"scratch-{label}"
        scratch.mkdir()

        def original(command, **kwargs):
            setup(Path(command[command.index("-o") + 1]))

        warning = io.StringIO()
        with contextlib.redirect_stderr(warning):
            measure.timed_run(original, steps, scratch)(["latexmk", "x.tex"])
        assert steps[0]["rss"] is None, (label, steps)
        assert "RSS recorded as null" in warning.getvalue(), label
    summary = measure.summarize(fake_result(None))
    assert summary["rss_mib"] is None and measure.mib(None) == "n/a"
    mixed = fake_result(None)
    mixed["steps"].append({"stage": "export", "seconds": 0.1, "rss": 2**20})
    assert measure.summarize(mixed)["rss_mib"] == 1.0

    # 2. Engine identity names its source; dirty means tracked changes only.
    assert measure.engine_identity(frozen) == ("unknown (frozen)", "directory name")
    (frozen / "engine-commit.txt").write_text("abc123\n")
    assert measure.engine_identity(frozen) == ("abc123", "engine-commit.txt")
    checkout = tmp / "checkout"
    checkout.mkdir()
    git = ["git", "-C", str(checkout), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    subprocess.run([*git, "commit", "-q", "--allow-empty", "--no-verify", "-m", "chore(test): empty"], check=True)
    assert measure.engine_identity(checkout)[1] == "git"
    (checkout / "file.txt").write_text("a\n")
    assert not measure.git_dirty(checkout)
    subprocess.run([*git, "add", "file.txt"], check=True)
    assert measure.git_dirty(checkout)

    # 3. A full run writes after each build, atomically, and marks completion last.
    out = tmp / "run"
    seen = []
    replaced = []
    original_replace = Path.replace

    def recording_replace(self, target):
        replaced.append(Path(target).name)
        return original_replace(self, target)

    def fake_measure(builder, src, build_dir, args):
        if (out / "results.json").exists():
            seen.append(read(out))
        return fake_result(None)

    measure = load()
    measure.load_builder = lambda: None
    measure.measure = fake_measure
    Path.replace = recording_replace
    try:
        stdout, stderr, error = run_main(measure, ["--engine", str(frozen), "--outdir", str(out),
                                                   "--source", str(source)])
    finally:
        Path.replace = original_replace
    assert error is None, error
    report = read(out)
    assert report["complete"] is True
    assert report["engine"] == "abc123" and report["engine_source"] == "engine-commit.txt"
    assert isinstance(report["commit_dirty"], bool)
    assert list(report["builds"]) == ["growth-raster-cold", "growth-raster-warm"]
    # The warm build saw the cold result already written and the run incomplete.
    assert seen[-1]["complete"] is False and "growth-raster-cold" in seen[-1]["builds"], seen
    assert replaced and set(replaced) == {"results.json"}, replaced
    assert not (out / "results.json.tmp").exists()
    assert "n/a" in stdout, stdout

    # 4. A rerun that fails anywhere before or during its builds leaves no
    #    complete report behind.
    for stage in ("load_builder", "engine_identity", "measure"):
        measure = load()
        measure.load_builder = lambda: None

        def boom(*args, **kwargs):
            raise RuntimeError(f"{stage} failed")

        if stage == "measure":
            measure.measure = boom
        else:
            setattr(measure, stage, boom)
        (out / "results.json").write_text(json.dumps({"complete": True, "builds": {"old": 1}}))
        _, _, error = run_main(measure, ["--engine", str(frozen), "--outdir", str(out), "--source", str(source)])
        assert isinstance(error, RuntimeError), (stage, error)
        assert read(out)["complete"] is False, stage

print("measure_raster_build checks passed")
