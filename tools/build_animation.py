"""Build a floral PDF with cached raster animation; requires Python and Poppler."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def engine_paths(explicit):
    root = explicit or os.environ.get('TIKZFLORA')
    local_env = Path('.env')
    if not root and local_env.exists():
        for line in local_env.read_text().splitlines():
            match = re.fullmatch(r'\s*TIKZFLORA\s*=\s*(.*?)\s*', line)
            if match:
                root = match[1].strip('"\'')
    if root:
        root = Path(root).expanduser().resolve()
        return root / 'lua', root / 'tex'
    if Path('lua/flora/init.lua').is_file():
        return Path('lua').resolve(), Path('.').resolve()
    style = subprocess.check_output(['kpsewhich', 'tikzflora.sty'], text=True).strip()
    if not style:
        raise RuntimeError('Cannot find tikz-flora; pass --engine /path/to/tikz-flora')
    parent = Path(style).resolve().parent
    for candidate in (parent / 'lua', parent.parent / 'lua'):
        if (candidate / 'flora/init.lua').is_file():
            return candidate, parent
    raise RuntimeError('Cannot locate the engine Lua modules; pass --engine')


def build(args):
    for tool in ('latexmk', 'texlua', 'pdftocairo'):
        if not shutil.which(tool):
            raise RuntimeError(f'{tool} is required. Raster animation needs Python, Poppler (pdftocairo), and LuaLaTeX/latexmk.')
    source = args.source.resolve()
    if not source.is_file():
        raise RuntimeError(f'Document not found: {source}')
    project = Path.cwd().resolve()
    output = args.outdir.resolve()
    if not output.is_relative_to(project):
        raise RuntimeError('--outdir must be inside the current project (LuaLaTeX output safety rules)')
    if any(ch in str(output) for ch in '\t\r\n%{}'):
        raise RuntimeError('Unsupported characters in animation output path')
    output.mkdir(parents=True, exist_ok=True)
    lua, styles = engine_paths(args.engine)
    if not (lua / 'flora/progression.lua').is_file():
        raise RuntimeError('This tikz-flora installation lacks the growth API; update the pinned engine')
    env = dict(os.environ)
    env['TIKZFLORA'] = str(lua.parent)
    env['FLORA_LUA'] = str(lua)
    env['TEXINPUTS'] = str(styles) + '//:' + env.get('TEXINPUTS', '')
    relative_output = str(output.relative_to(project)) or '.'
    command = ['latexmk', '-g', '-lualatex', '-interaction=nonstopmode', '-halt-on-error',
               '-outdir=' + relative_output, str(source)]
    prepare_env = dict(env, FLORAL_ANIMATION_PREPARE='1')
    subprocess.run(command, env=prepare_env, check=True)
    stem = source.stem
    manifest = output / (stem + '.floral-animation-manifest')
    cache = output / (stem + '.floral-animation')
    if not manifest.is_file():
        raise RuntimeError('No animation manifest was produced; load beamer-floral-animation in the document')
    cache.mkdir(exist_ok=True)
    worker = Path(__file__).with_name('render_animation.lua')
    with tempfile.TemporaryDirectory(prefix='render-', dir=cache) as temporary:
        scratch = Path(temporary)
        subprocess.run(['texlua', str(worker), str(lua), str(manifest), str(cache),
                        str(scratch), str(args.dpi)], env=env, check=True)
        jobs = [line.split('\t') for line in (scratch / 'jobs.tsv').read_text().splitlines()]

        def raster(job):
            pdf, prefix = job
            # A partial render is never published as a valid cache sample.
            temporary_prefix = prefix + '.tmp'
            subprocess.run(['pdftocairo', '-png', '-singlefile', '-transp', '-r', str(args.dpi),
                            pdf, temporary_prefix], check=True)
            os.replace(temporary_prefix + '.png', prefix + '.png')
            Path(pdf).unlink()

        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            list(pool.map(raster, jobs))
        candidate = (scratch / 'index.floral').read_bytes()
        index = cache / 'index.floral'
        changed = not index.is_file() or index.read_bytes() != candidate
        if changed:
            os.replace(scratch / 'index.floral', index)
    if jobs or changed:
        subprocess.run(command, env=env, check=True)
    print(f'Built {output / (stem + ".pdf")} ({len(jobs)} new raster samples, {args.dpi} dpi).')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--outdir', type=Path, default=Path('.'))
    parser.add_argument('--engine', type=Path, help='development checkout of tikz-flora')
    parser.add_argument('--dpi', type=int, choices=range(36, 601), default=144, metavar='36..600')
    parser.add_argument('--jobs', type=int, choices=range(1, 9), default=2, metavar='1..8')
    args = parser.parse_args()
    try:
        build(args)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Animation build failed: {error}\n')
