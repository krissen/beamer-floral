"""Check a PDF built with GIF playback: one full-page Movie annotation per timed
page, a complete GIF for each that decodes to its samples, and no JavaScript
anywhere. Needs qpdf and Pillow."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import struct


def gif_facts(path):
    """Frames, delays (centiseconds), disposal and transparency of each frame, loop extension."""
    data = path.read_bytes()
    if data[:4] != b'GIF8' or data[-1:] != b';':
        raise RuntimeError(f'{path}: not a complete GIF')
    position = 13
    if data[10] & 0x80:
        position += 3 * (2 << (data[10] & 7))
    frames, looped, control = [], False, None

    def skip(at):
        while data[at]:
            at += data[at] + 1
        return at + 1

    while data[position] != 0x3B:
        if data[position] == 0x21:
            label = data[position + 1]
            if label == 0xF9:
                packed, delay, index = struct.unpack('<BHB', data[position + 3:position + 7])
                control = (delay, packed >> 2 & 7, bool(packed & 1) and index)
            elif label == 0xFF and data[position + 3:position + 14].startswith(b'NETSCAPE'):
                looped = True
            position = skip(position + 2)
        elif data[position] == 0x2C:
            flags = data[position + 9]
            position += 10
            if flags & 0x80:
                position += 3 * (2 << (flags & 7))
            position = skip(position + 1)
            frames.append(control)
            control = None
        else:
            raise RuntimeError(f'{path}: unexpected block')
    return frames, looped


# Per-channel RMS (0-255) between a decoded frame and its matted sample. A
# correct encoding stays at quantisation error; scrambled rows are far above.
RMS_LIMIT = 8.0


def rms_against_source(frame, sample, matte):
    """Per-channel RMS of a decoded GIF frame against its sample matted on `matte`.

    Also returns whether every fully transparent sample pixel decoded transparent."""
    from PIL import Image, ImageChops
    with Image.open(sample) as source:
        source = source.convert('RGBA')
    colour = tuple(int(matte[i:i + 2], 16) for i in (0, 2, 4))
    background = Image.new('RGBA', source.size, (*colour, 255))
    expected = Image.alpha_composite(background, source).convert('RGB')
    frame = frame.convert('RGBA')
    if frame.size != source.size:
        raise RuntimeError(f'frame {frame.size} differs from sample {source.size}')
    actual = Image.alpha_composite(background, frame).convert('RGB')
    difference = ImageChops.difference(expected, actual)
    pixels = source.size[0] * source.size[1]
    squared = [sum(count * value * value for value, count in enumerate(histogram)) / pixels
               for histogram in (difference.getchannel(band).histogram() for band in 'RGB')]
    empty = source.getchannel('A').point([255] + [0] * 255)
    transparent = ImageChops.multiply(empty, frame.getchannel('A')).getbbox() is None
    return [v ** 0.5 for v in squared], transparent


def check_decoded(path, steps, folder, first_sample):
    """First and last frame of an interval GIF against their sample PNGs."""
    from PIL import Image
    matte = re.fullmatch(r'interval-\d+-r\d+-m([0-9A-Fa-f]{6})\.gif', path.name)[1]
    with Image.open(path) as gif:
        for index in (0, steps):
            gif.seek(index)
            rms, transparent = rms_against_source(
                gif.copy(), folder / f'sample-{first_sample + index}.png', matte)
            if max(rms) > RMS_LIMIT or not transparent:
                raise RuntimeError(f'{path}: frame {index} does not match its sample '
                                   f'(RMS {max(rms):.1f}, limit {RMS_LIMIT}, transparent {transparent})')


def check(pdf, expected_pages=None):
    result = subprocess.run(['qpdf', '--json', '--json-key=qpdf', str(pdf)],
                            capture_output=True, text=True)
    if result.returncode not in (0, 3):
        raise RuntimeError(result.stderr)
    for line in result.stderr.splitlines():
        if line.startswith('WARNING:'):
            raise RuntimeError(line)
    objects = json.loads(result.stdout)['qpdf'][1]

    def value(item):
        if isinstance(item, str) and re.fullmatch(r'\d+ \d+ R', item):
            return objects['obj:' + item]['value']
        return item

    def visit(item, path=''):
        if isinstance(item, dict):
            for key, child in item.items():
                if key in ('/JS', '/JavaScript') or child == '/JavaScript':
                    raise RuntimeError(f'JavaScript in the PDF ({key} at {path or "root"})')
                visit(child, path + key)
        elif isinstance(item, list):
            for child in item:
                visit(child, path)

    for name, item in objects.items():
        if name.startswith('obj:'):
            visit(item.get('value'), name)
    timed = 0
    intervals = {}
    for name, item in objects.items():
        page = item.get('value') if name.startswith('obj:') else None
        if not isinstance(page, dict) or page.get('/Type') != '/Page':
            continue
        box = [float(x) for x in value(page.get('/MediaBox') or [0, 0, 0, 0])]
        movies = [annotation for annotation in (value(page.get('/Annots')) or [])
                  if value(annotation).get('/Subtype') == '/Movie']
        if not movies:
            continue
        if len(movies) != 1:
            raise RuntimeError(f'{name}: a timed page needs exactly one Movie annotation, found {len(movies)}')
        movie = value(movies[0])
        rect = [float(x) for x in movie['/Rect']]
        if any(abs(a - b) > 0.01 for a, b in zip(rect, [0, 0, box[2] - box[0], box[3] - box[1]])):
            raise RuntimeError(f'{name}: the Movie annotation must cover the page, Rect {rect} in {box}')
        if movie.get('/A', {}).get('/Mode') != '/Once':
            raise RuntimeError(f'{name}: the GIF must play once')
        timed += 1
        relative = movie['/Movie']['/F'].removeprefix('u:')
        path = pdf.parent / relative
        if not path.is_file():
            raise RuntimeError(f'{name}: missing GIF {relative}')
        label = re.fullmatch(r'floral-(\d+)-(\d+)', movie['/T'].removeprefix('u:'))
        if not label:
            raise RuntimeError(f'{name}: unexpected annotation name {movie["/T"]}')
        intervals.setdefault(path.parent, {})[int(label[2])] = path
    if not timed:
        raise RuntimeError('No timed pages found')
    if expected_pages is not None and timed != expected_pages:
        raise RuntimeError(f'{timed} timed pages, expected {expected_pages}')
    for folder, stages in intervals.items():
        count = max(stages)
        if sorted(stages) != list(range(1, count + 1)):
            raise RuntimeError(f'{folder}: not every interval has a page')
        samples = len(list(folder.glob('sample-*.png')))
        if samples < 2 or (samples - 1) % count:
            raise RuntimeError(f'{folder}: {samples} samples do not divide into {count} intervals')
        steps = (samples - 1) // count
        for stage, path in stages.items():
            frames, looped = gif_facts(path)
            if len(frames) != steps + 1:
                raise RuntimeError(f'{path}: {len(frames)} frames, expected {steps + 1}')
            if looped:
                raise RuntimeError(f'{path}: loop extension; the GIF must play once')
            check_decoded(path, steps, folder, (stage - 1) * steps)
            if any(f is None or f[1] != 2 or f[2] != 255 or f[0] < 1 for f in frames):
                raise RuntimeError(f'{path}: frames need disposal 2, transparent index 255 and a delay')
    print(f'GIF PDF checks passed ({timed} timed pages, no JavaScript)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('--pages', type=int, help='expected number of timed pages')
    arguments = parser.parse_args()
    check(arguments.pdf.resolve(), arguments.pages)
