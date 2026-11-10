"""GIF jobs of the animation builder, with synthetic samples (needs Pillow).

  .venv/bin/python test/gif-job.py
"""
import importlib.util
from pathlib import Path
import tempfile

from PIL import Image, ImageSequence

spec = importlib.util.spec_from_file_location('animation_builder', 'tools/build_animation.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

STEPS, RATE_MILLI = 10, 20000
Path('build').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='gif-job-', dir='build') as temporary:
    root = Path(temporary).resolve()
    folder = root / 'samples'
    folder.mkdir()
    for n in range(2 * STEPS + 1):
        # Sample 3 repeats sample 2 exactly; frames must not be merged.
        grown = max(n - 1, 2) if n == 3 else n
        image = Image.new('RGBA', (48, 32), (0, 0, 0, 0))
        for x in range(grown * 2):
            for y in range(12, 20):
                image.putpixel((x, y), (200, 20 * (grown % 10), 90, 255 if x < grown else 5))
        image.putpixel((40, 4), (10, 200, 10, 7))   # alpha 7: transparent
        image.putpixel((41, 4), (10, 200, 10, 8))   # alpha 8: kept, matted
        image.save(folder / f'sample-{n}.png')
    out = root / 'interval-2-r20000-mFFFFFF.gif'
    job = (str(folder), STEPS, STEPS, RATE_MILLI, 'FFFFFF', str(out))
    builder.build_gif(job)

    data = out.read_bytes()
    assert data[:6] == b'GIF89a' and data.endswith(b';')
    assert b'NETSCAPE' not in data, 'the GIF must play once, without a loop extension'
    assert not list(root.glob('*.tmp'))
    with Image.open(out) as gif:
        frames = [frame.copy() for frame in ImageSequence.Iterator(gif)]
        assert gif.n_frames == STEPS + 1 == len(frames)
        assert 'loop' not in gif.info
    delays = []
    with Image.open(out) as gif:
        for index in range(gif.n_frames):
            gif.seek(index)
            delays.append(gif.info['duration'])
            assert gif.disposal_method == 2
    assert all(delay % 10 == 0 for delay in delays), delays
    # Graphic control blocks: disposal 2, transparency flag, transparent index 255.
    controls = [data[i:i + 8] for i in range(len(data)) if data[i:i + 3] == b'\x21\xf9\x04']
    assert len(controls) == STEPS + 1, len(controls)
    assert all(c[3] == 0x09 and c[6] == 255 for c in controls)
    total_ms = sum(delays[:STEPS])
    assert abs(total_ms - 1000 * STEPS * 1000 / RATE_MILLI) <= 10, total_ms
    # Alpha at or below 7 is transparent, a little more is matted opaque.
    first = frames[STEPS].convert('RGBA')
    assert first.getpixel((40, 4))[3] == 0 and first.getpixel((41, 4))[3] == 255
    assert first.getpixel((0, 0))[3] == 0
    assert builder.valid_gif(out) and not builder.valid_gif(root / 'absent.gif')

    # A rate that is not a whole number of centiseconds carries the error.
    for rate in (20000, 15000, 59940, 60000, 7000):
        cs = [builder.centiseconds(i, rate) for i in range(161)]
        assert min(cs) >= 1
        assert abs(sum(cs[:160]) * 10 - 160 * 1e6 / rate) <= 10, rate

    # A sample that cannot be read publishes nothing, not even a partial file.
    broken = root / 'broken'
    broken.mkdir()
    for n in range(STEPS + 1):
        (folder / f'sample-{n}.png').replace(broken / f'sample-{n}.png')
    (broken / 'sample-6.png').write_bytes(b'not a png')
    target = root / 'interval-1-r20000-mFFFFFF.gif'
    try:
        builder.build_gif((str(broken), 0, STEPS, RATE_MILLI, 'FFFFFF', str(target)))
    except Exception:
        pass
    else:
        raise AssertionError('a broken sample must fail the job')
    assert not target.exists() and not list(root.glob('*.tmp'))

    # Without Pillow the job explains what to install.
    import builtins
    real = builtins.__import__

    def refuse(name, *args, **kwargs):
        if name == 'PIL':
            raise ImportError(name)
        return real(name, *args, **kwargs)
    builtins.__import__ = refuse
    try:
        builder.build_gif(job)
    except RuntimeError as error:
        assert str(error) == 'GIF playback needs Pillow (python3 -m pip install pillow)'
    else:
        raise AssertionError('missing Pillow must be reported')
    finally:
        builtins.__import__ = real

    # The worker's listing: only missing GIFs, only inside the cache.
    listing = root / 'gifs.tsv'
    listing.write_text('\t'.join([str(folder), '0', '10', '20000', 'FFFFFF', str(root / 'a.gif')]) + '\n'
                       + '\t'.join([str(folder), '10', '10', '20000', 'FFFFFF', str(out)]) + '\n')
    assert [Path(j[5]).name for j in builder.gif_jobs(listing, root)] == ['a.gif']
    listing.write_text('\t'.join([str(folder), '0', '10', '20000', 'FFFFFF', '/elsewhere/a.gif']) + '\n')
    try:
        builder.gif_jobs(listing, root)
    except RuntimeError:
        pass
    else:
        raise AssertionError('GIF output outside the cache must be refused')
print('gif job tests passed')
