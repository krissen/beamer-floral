"""Build a floral PDF with cached raster animation; requires Python and Poppler.

GIF playback (\\usepackage[gif]{beamer-floral-animation}) also needs Pillow."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import io
import math
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


# GdkPixbuf (the decoder pympress uses) plays a frame delay below 2 cs as 20 ms and
# a zero delay as 100 ms, so no frame is written with less than 2 cs and a rate
# above 50 fps is thinned to every k-th sample.
MIN_DELAY = 2
MAX_RATE_MILLI = 50000


def frame_plan(steps, rate_milli):
    """Samples (0..steps) shown by an interval's GIF and the delay of each, in centiseconds.

    Stride k = max(1, ceil(rate / 50 fps)); samples 0, k, 2k, ... below steps, and steps.
    A final gap shorter than 2 cs after rounding drops the sample before it. A delay is
    the time to the next kept sample in whole centiseconds, the rounding error carried
    forward; the last frame gets one nominal sample time, at least 2 cs. An interval
    shorter than 20 ms becomes two frames with 2 cs, the only case that is not to scale."""
    def edge(n):
        return (n * 200000 + rate_milli) // (2 * rate_milli)

    stride = max(1, -(-rate_milli // MAX_RATE_MILLI))
    kept = list(range(0, steps, stride)) + [steps]
    if len(kept) > 2 and edge(steps) - edge(kept[-2]) < MIN_DELAY:
        del kept[-2]
    delays = [max(MIN_DELAY, edge(b) - edge(a)) for a, b in zip(kept, kept[1:])]
    delays.append(max(MIN_DELAY, edge(steps + 1) - edge(steps)))
    return kept, delays


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


def reserved_mask(image_module, size, geometry):
    """255 inside every reserved rectangle. geometry is (width pt, height pt, rectangles);
    rectangles are x0, y0, x1, y1 in pt from the lower-left corner and are rounded
    outward, so a reserved area is always fully covered."""
    from PIL import ImageDraw
    width, height, rectangles = geometry
    scale_x, scale_y = size[0] / width, size[1] / height
    mask = image_module.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    for x0, y0, x1, y1 in rectangles:
        left = max(0, math.floor(min(x0, x1) * scale_x))
        right = min(size[0], math.ceil(max(x0, x1) * scale_x))
        top = max(0, math.floor((height - max(y0, y1)) * scale_y))
        bottom = min(size[1], math.ceil((height - min(y0, y1)) * scale_y))
        if right > left and bottom > top:
            draw.rectangle([left, top, right - 1, bottom - 1], fill=255)
    return mask


def gif_frame(image_module, path, matte, geometry=None):
    """One sample as a 256 colour frame: matted, index 255 transparent.

    The GIF is an annotation above the page, so the page's reservation clips do not
    reach it; the reserved rectangles are made transparent here."""
    with image_module.open(path) as source:
        rgba = source.convert('RGBA')
    if geometry and geometry[2]:
        rgba.paste((0, 0, 0, 0), mask=reserved_mask(image_module, rgba.size, geometry))
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
    frame.save(buffer, 'GIF', transparency=255, optimize=False, interlace=False)
    return rgba.size, bytes(palette), _image_data(buffer.getvalue(), rgba.size)


def build_gif(job):
    """Write one interval's GIF (frame_plan), played once, never half written.

    Frames are assembled here rather than by Pillow's multi-frame writer, which
    merges identical neighbours and would change the frame count."""
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError('GIF playback needs Pillow (python3 -m pip install pillow)') from None
    folder, first, steps, rate_milli, matte, out, geometry = job
    colour = tuple(int(matte[i:i + 2], 16) for i in (0, 2, 4))
    out = Path(out)
    temporary = out.with_name(out.name + '.tmp')
    try:
        chunks = []
        size = None
        kept, delays = frame_plan(steps, rate_milli)
        for n, delay in zip(kept, delays):
            size, palette, data = gif_frame(Image, Path(folder) / f'sample-{first + n}.png', colour, geometry)
            # Graphic control: disposal 2 (restore to background), transparent index 255.
            chunks.append(bytes([0x21, 0xF9, 4])
                          + struct.pack('<BHBB', 0x09, delay, 255, 0)
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
        folder, first, steps, rate_milli, matte, out, page, reserved = line.split('\t')
        width, height = (float(v) for v in page.split(','))
        rectangles = [tuple(float(v) for v in item.split(',')) for item in reserved.split(';') if item]
        if width <= 0 or height <= 0 or any(len(r) != 4 for r in rectangles):
            raise RuntimeError(f'Invalid GIF job: {line}')
        job = (folder, int(first), int(steps), int(rate_milli), matte, out, (width, height, rectangles))
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
