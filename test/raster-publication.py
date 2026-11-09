"""A failed raster job must not publish the worker's candidate cache index."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('animation_builder', 'tools/build_animation.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
Path('build').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='raster-publication-', dir='build') as temporary:
    root = Path(temporary).resolve()
    source = root / 'fixture.tex'
    source.write_text('unused')
    engine = root / 'engine'
    (engine / 'flora').mkdir(parents=True)
    (engine / 'flora/progression.lua').touch()
    cache = root / 'fixture.floral-animation'
    cache.mkdir()
    index = cache / 'index.floral'
    index.write_bytes(b'previous valid index')

    def run(command, **kwargs):
        if command[0] == 'latexmk':
            (root / 'fixture.floral-animation-manifest').touch()
        elif command[0] == 'texlua':
            scratch = Path(command[5])
            pdf = scratch / 'sample.pdf'
            pdf.touch()
            (scratch / 'jobs.tsv').write_text(f'{pdf}\t{cache / "sample"}\n')
            (scratch / 'index.floral').write_bytes(b'candidate index')
        else:
            raise subprocess.CalledProcessError(1, command)

    args = SimpleNamespace(source=source, outdir=root, engine=None, dpi=144, jobs=2)
    with patch.object(builder, 'engine_paths', return_value=(engine, engine)), \
            patch.object(builder.shutil, 'which', return_value='/unused'), \
            patch.object(builder.subprocess, 'run', side_effect=run):
        try:
            builder.build(args)
        except subprocess.CalledProcessError:
            pass
        else:
            raise AssertionError('raster failure must propagate')
    assert index.read_bytes() == b'previous valid index'
    assert not (cache / 'sample.png').exists()
print('raster publication failure test passed')
