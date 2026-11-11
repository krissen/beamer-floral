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
spec = importlib.util.spec_from_file_location('gif_checker', 'tools/check_gif_pdf.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

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
    job = (str(folder), STEPS, STEPS, RATE_MILLI, 'FFFFFF', str(out), (24, 16, []))
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

    # The invariant: every decoded frame equals its matted source within
    # quantisation error, on a source whose rows all differ and whose edge is soft.
    pixels = root / 'pixels'
    pixels.mkdir()
    for n in range(STEPS + 1):
        image = Image.new('RGBA', (160, 90), (0, 0, 0, 0))
        right = 20 + n * 13
        for y in range(5, 85):
            for x in range(10, right):
                soft = max(0, min(255, 32 * (right - x)))   # soft right edge
                image.putpixel((x, y), ((y % 16) * 16, (y % 16) * 83 % 256, (y % 16) * 41 % 256, soft))
        image.save(pixels / f'sample-{n}.png')
    for matte in ('FFFFFF', '203040'):
        built = root / f'interval-5-r20000-m{matte}-e3.gif'
        builder.build_gif((str(pixels), 0, STEPS, RATE_MILLI, matte, str(built), (80, 45, [])))
        with Image.open(built) as gif:
            for index in range(gif.n_frames):
                gif.seek(index)
                rms, transparent = checker.rms_against_source(
                    gif.copy(), pixels / f'sample-{index}.png', matte)
                print('frame', index, matte, 'RMS', ' '.join(f'{v:.2f}' for v in rms))
                assert max(rms) < checker.RMS_LIMIT, (index, matte, rms)
                assert transparent, f'frame {index}: transparent source pixels must decode transparent'
        checker.check_decoded(built, list(range(STEPS + 1)), pixels, 0)

    # Reservations: the page's clip does not reach an annotation, so the GIF must
    # carry it. The page is 80 x 45 pt, the samples 160 x 90 px (2 px per pt). One
    # rectangle inside the page, one touching the left and bottom edge, one partly outside.
    reserved = [(20, 10, 40, 25), (0, 0, 15.3, 8.2), (70, 35, 95, 60)]
    # Pixel boxes, rounded outward, y from the top: left, top, right, bottom (exclusive).
    boxes = [(40, 40, 80, 70), (0, 73, 31, 90), (140, 0, 160, 20)]
    masked = root / 'interval-6-r20000-mFFFFFF-e3.gif'
    builder.build_gif((str(pixels), 0, STEPS, RATE_MILLI, 'FFFFFF', str(masked), (80, 45, reserved)))
    unmasked = root / 'interval-7-r20000-mFFFFFF-e3.gif'
    builder.build_gif((str(pixels), 0, STEPS, RATE_MILLI, 'FFFFFF', str(unmasked), (80, 45, [])))
    recorded = {'width': 80, 'height': 45, 'reserve': [list(r) for r in reserved]}
    assert checker.reserved_areas(recorded, (160, 90)) == boxes, checker.reserved_areas(recorded, (160, 90))
    with Image.open(masked) as gif:
        for index in range(gif.n_frames):
            gif.seek(index)
            frame = gif.convert('RGBA')
            for left, top, right, bottom in boxes:
                alpha = frame.crop((left, top, right, bottom)).getchannel('A')
                assert alpha.getextrema() == (0, 0), (index, (left, top, right, bottom))
            rms, transparent = checker.rms_against_source(frame, pixels / f'sample-{index}.png', 'FFFFFF', recorded)
            assert max(rms) < checker.RMS_LIMIT and transparent, (index, rms)
        # Pixels just outside a reservation are untouched (the last frame is opaque there).
        assert gif.convert('RGBA').getpixel((39, 55))[3] == 255 and gif.convert('RGBA').getpixel((80, 55))[3] == 255
        assert gif.convert('RGBA').getpixel((60, 39))[3] == 255 and gif.convert('RGBA').getpixel((60, 70))[3] == 255
    checker.check_decoded(masked, list(range(STEPS + 1)), pixels, 0, recorded)
    # The checker rejects a GIF built without the masking.
    try:
        checker.check_decoded(unmasked, list(range(STEPS + 1)), pixels, 0, recorded)
    except RuntimeError as error:
        print('unmasked GIF rejected:', error)
    else:
        raise AssertionError('the checker must reject a GIF that ignores reservations')
    # The worker's geometry reaches the job.
    listing = root / 'masked.tsv'
    listing.write_text('\t'.join([str(pixels), '0', '10', '20000', 'FFFFFF', str(root / 'b.gif'), '80,45',
                                  '20,10,40,25;0,0,15.3,8.2;70,35,95,60']) + '\n')
    assert builder.gif_jobs(listing, root)[0][6] == (80.0, 45.0, [(20.0, 10.0, 40.0, 25.0), (0.0, 0.0, 15.3, 8.2), (70.0, 35.0, 95.0, 60.0)])

    # Timing matrix. GdkPixbuf plays a delay below 2 cs as 20 ms (0 cs as 100 ms), so:
    # every delay is at least 2 cs, the first and last sample are shown, and the delays
    # of all frames but the last sum to the interval's duration within 10 ms whenever
    # that is at least 20 ms (shorter intervals become two frames of 2 cs). Rates up to
    # 50 fps are written exactly as before the rule existed.
    rates = [7, 15, 20, 25, 50, 59.94, 60, 100, 120, 333, 1000, 6400]
    cells = [(round(fps * 1000), steps) for fps in rates for steps in (1, 2, 3, 7, 40)]
    # The finding's own case: duration 0.05 s over 16 overlays at 20 fps.
    seconds = 0.05 / 16
    cells.append((round(max(1, round(seconds * 20)) / seconds * 1000), max(1, round(seconds * 20))))
    tiny = root / 'tiny'
    tiny.mkdir()
    for n in range(41):
        image = Image.new('RGBA', (16, 12), (0, 0, 0, 0))
        for x in range(n % 16 + 1):
            image.putpixel((x, n % 12), (n * 6 % 256, 90, 200, 255))
        image.save(tiny / f'sample-{n}.png')

    def legacy(steps, rate_milli):
        def edge(n):
            return (n * 200000 + rate_milli) // (2 * rate_milli)
        return list(range(steps + 1)), [edge(n + 1) - edge(n) for n in range(steps + 1)]

    for rate_milli, steps in cells:
        shown, delays = builder.frame_plan(steps, rate_milli)
        cell = (rate_milli, steps)
        assert (shown, delays) == checker.expected_plan(steps, rate_milli), cell
        assert min(delays) >= 2, cell
        assert shown[0] == 0 and shown[-1] == steps and shown == sorted(set(shown)), cell
        duration_ms = steps * 1e6 / rate_milli
        if duration_ms >= 20:
            assert abs(sum(delays[:-1]) * 10 - duration_ms) <= 10, (cell, delays, duration_ms)
        else:
            assert shown == [0, steps] and delays[0] == 2, cell
        if rate_milli <= 50000:
            assert (shown, delays) == legacy(steps, rate_milli), cell
        # The written file follows the plan, frame for frame.
        target = root / 'matrix.gif'
        builder.build_gif((str(tiny), 0, steps, rate_milli, 'FFFFFF', str(target), (16, 12, [])))
        facts, looped = checker.gif_facts(target)
        assert [f[0] for f in facts] == delays and not looped, cell
        if rate_milli <= 50000:
            reference = root / 'reference.gif'
            current = builder.frame_plan
            builder.frame_plan = legacy
            try:
                builder.build_gif((str(tiny), 0, steps, rate_milli, 'FFFFFF', str(reference), (16, 12, [])))
            finally:
                builder.frame_plan = current
            assert target.read_bytes() == reference.read_bytes(), ('byte identity', cell)
    print('timing matrix:', len(cells), 'cells passed')

    # A sample that cannot be read publishes nothing, not even a partial file.
    broken = root / 'broken'
    broken.mkdir()
    for n in range(STEPS + 1):
        (folder / f'sample-{n}.png').replace(broken / f'sample-{n}.png')
    (broken / 'sample-6.png').write_bytes(b'not a png')
    target = root / 'interval-1-r20000-mFFFFFF.gif'
    try:
        builder.build_gif((str(broken), 0, STEPS, RATE_MILLI, 'FFFFFF', str(target), (24, 16, [])))
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
    listing.write_text('\t'.join([str(folder), '0', '10', '20000', 'FFFFFF', str(root / 'a.gif'), '24,16', '']) + '\n'
                       + '\t'.join([str(folder), '10', '10', '20000', 'FFFFFF', str(out), '24,16', '']) + '\n')
    assert [Path(j[5]).name for j in builder.gif_jobs(listing, root)] == ['a.gif']
    listing.write_text('\t'.join([str(folder), '0', '10', '20000', 'FFFFFF', '/elsewhere/a.gif', '24,16', '']) + '\n')
    try:
        builder.gif_jobs(listing, root)
    except RuntimeError:
        pass
    else:
        raise AssertionError('GIF output outside the cache must be refused')
print('gif job tests passed')
