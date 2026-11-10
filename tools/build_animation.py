"""Build a floral PDF with cached raster animation; requires Python and Poppler.

GIF playback (\\usepackage[gif]{beamer-floral-animation}) also needs Pillow."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import io
import os
from pathlib import Path
import re
import shutil
import struct
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


def centiseconds(index, rate_milli):
    """Whole-centisecond delay of frame `index`; the rounding error is carried forward."""
    def edge(n):
        return (n * 200000 + rate_milli) // (2 * rate_milli)
    return edge(index + 1) - edge(index)


def _sub_blocks_end(data, position):
    while data[position]:
        position += data[position] + 1
    return position + 1


def _image_data(data, size):
    """The LZW part of a single-frame GIF written by Pillow."""
    position = 13
    if data[10] & 0x80:
        position += 3 * (2 << (data[10] & 7))
    while True:
        marker = data[position]
        if marker == 0x21:
            position = _sub_blocks_end(data, position + 2)
        elif marker == 0x2C:
            left, top, width, height, flags = struct.unpack('<HHHHB', data[position + 1:position + 10])
            if (left, top, width, height) != (0, 0, *size):
                raise RuntimeError('unexpected GIF frame geometry')
            position += 10
            if flags & 0x80:
                position += 3 * (2 << (flags & 7))
            return data[position:_sub_blocks_end(data, position + 1)]
        else:
            raise RuntimeError('unexpected GIF block')


def gif_frame(image_module, path, matte):
    """One sample as a 256 colour frame: matted, index 255 transparent."""
    with image_module.open(path) as source:
        rgba = source.convert('RGBA')
    background = image_module.new('RGBA', rgba.size, (*matte, 255))
    flat = image_module.alpha_composite(background, rgba).convert('RGB')
    frame = flat.quantize(colors=255, method=image_module.Quantize.MEDIANCUT,
                          dither=image_module.Dither.NONE)
    clear = rgba.getchannel('A').point([255] * 8 + [0] * 248)
    frame.paste(255, mask=clear)
    palette = list(frame.getpalette() or [])[:765]
    palette += [0] * (768 - len(palette))
    frame.putpalette(palette)
    buffer = io.BytesIO()
    frame.save(buffer, 'GIF', transparency=255, optimize=False)
    return rgba.size, bytes(palette), _image_data(buffer.getvalue(), rgba.size)


def build_gif(job):
    """Write one interval's GIF: steps + 1 frames, played once, never half written.

    Frames are assembled here rather than by Pillow's multi-frame writer, which
    merges identical neighbours and would change the frame count."""
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError('GIF playback needs Pillow (python3 -m pip install pillow)') from None
    folder, first, steps, rate_milli, matte, out = job
    colour = tuple(int(matte[i:i + 2], 16) for i in (0, 2, 4))
    out = Path(out)
    temporary = out.with_name(out.name + '.tmp')
    try:
        chunks = []
        size = None
        for n in range(steps + 1):
            size, palette, data = gif_frame(Image, Path(folder) / f'sample-{first + n}.png', colour)
            # Graphic control: disposal 2 (restore to background), transparent index 255.
            chunks.append(bytes([0x21, 0xF9, 4])
                          + struct.pack('<BHBB', 0x09, centiseconds(n, rate_milli), 255, 0)
                          + struct.pack('<BHHHHB', 0x2C, 0, 0, *size, 0x87) + palette + data)
        with open(temporary, 'wb') as stream:
            stream.write(b'GIF89a' + struct.pack('<HHBBB', *size, 0x70, 0, 0))
            stream.write(b''.join(chunks))
            stream.write(b';')
        os.replace(temporary, out)
    finally:
        temporary.unlink(missing_ok=True)


def valid_gif(path):
    try:
        with open(path, 'rb') as stream:
            return stream.read(4) == b'GIF8'
    except OSError:
        return False


def gif_jobs(listing, cache):
    """Missing GIFs from the worker's gifs.tsv; anything outside the cache is refused."""
    jobs = []
    if not listing.is_file():
        return jobs
    root = cache.resolve()
    for line in listing.read_text().splitlines():
        folder, first, steps, rate_milli, matte, out = line.split('\t')
        job = (folder, int(first), int(steps), int(rate_milli), matte, out)
        if job[2] < 1 or job[3] < 1 or not re.fullmatch(r'[0-9A-Fa-f]{6}', matte):
            raise RuntimeError(f'Invalid GIF job: {line}')
        if not Path(out).resolve().is_relative_to(root):
            raise RuntimeError(f'GIF output outside the animation cache: {out}')
        if not valid_gif(out):
            jobs.append(job)
    return jobs


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
        # GIFs are built from the finished samples, before anything is published.
        gifs = gif_jobs(scratch / 'gifs.tsv', cache)
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            list(pool.map(build_gif, gifs))
        candidate = (scratch / 'index.floral').read_bytes()
        index = cache / 'index.floral'
        changed = not index.is_file() or index.read_bytes() != candidate
        if changed:
            os.replace(scratch / 'index.floral', index)
    if jobs or changed or gifs:
        subprocess.run(command, env=env, check=True)
    extra = f', {len(gifs)} new GIFs' if gifs else ''
    print(f'Built {output / (stem + ".pdf")} ({len(jobs)} new raster samples{extra}, {args.dpi} dpi).')


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
