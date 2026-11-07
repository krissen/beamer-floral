"""Check the PDF resource structure and execute its emitted animation clock."""
import argparse
import json
import re
from pathlib import Path
import subprocess
import tempfile


def check(pdf):
    result = subprocess.run(['qpdf', '--json', '--json-key=qpdf', str(pdf)],
                            capture_output=True, text=True)
    if result.returncode not in (0, 3):
        raise RuntimeError(result.stderr)
    # pdfbase intentionally adds an unregistered, inert widget per page as
    # an Acrobat OCG workaround. Reject other malformed PDF structures.
    for line in result.stderr.splitlines():
        if line.startswith('WARNING:') and 'this widget annotation is not reachable' not in line:
            raise RuntimeError(line)
    objects = json.loads(result.stdout)['qpdf'][1]
    scripts = set()

    def visit(value):
        if isinstance(value, dict):
            if value.get('/S') == '/JavaScript' and isinstance(value.get('/JS'), str):
                scripts.add(value['/JS'])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(objects)
    code_blocks = []
    for reference in sorted(scripts):
        if reference.endswith(' R'):
            code_blocks.append(subprocess.check_output(
                ['qpdf', '--show-object='+reference.split()[0], '--filtered-stream-data', str(pdf)]))
    startup = next((item for item in code_blocks if b'function floralPrepare' in item), None)
    if startup is None:
        raise RuntimeError('Missing document-level view preparation')
    checked = set()
    intervals = {}
    with tempfile.TemporaryDirectory(prefix='floral-clock-') as directory:
        for code in code_blocks:
            if b'floralEpoch' not in code or code in checked:
                continue
            checked.add(code)
            identity = re.search(rb'var a(\d+)_floralEpoch', code)[1]
            intervals[identity.decode()] = int(re.search(rb'if\(target>=(\d+)\)', code)[1])
            closing = next((item for item in code_blocks if b'floralEpoch' not in item and
                            b'if(a'+identity+b'_floralEntered)' in item), None)
            if closing is None:
                raise RuntimeError('Missing floral page-close guard')
            invisible = next((item for item in code_blocks if b'floralEpoch' not in item and
                              b"typeof a"+identity+b"_seekFrame==='function'" in item), None)
            if invisible is None:
                raise RuntimeError('Missing PageInvisible rearm action')
            source = Path(directory) / 'clock.js'
            source.write_bytes(code)
            close_source = Path(directory) / 'close.js'
            close_source.write_bytes(closing)
            invisible_source = Path(directory) / 'invisible.js'
            invisible_source.write_bytes(invisible)
            startup_source = Path(directory) / 'startup.js'
            startup_source.write_bytes(startup)
            subprocess.run(['node', str(Path(__file__).resolve().parents[1] /
                                       'test/animation-clock.cjs'), str(source), str(close_source), str(invisible_source), str(startup_source)], check=True)
    if not checked:
        raise RuntimeError('No floral animation clock found in PDF')
    counts = {identity: 0 for identity in intervals}
    for item in objects.values():
        value = item.get('value')
        if not isinstance(value, dict) or value.get('/Type') != '/OCG':
            continue
        name = value.get('/Name', '').removeprefix('u:').split('.')
        if len(name) != 2 or name[0] not in intervals or not name[1].isdigit():
            continue
        usage = value.get('/Usage', {})
        if isinstance(usage, str):
            usage = objects['obj:'+usage]['value']
        expected = '/ON' if int(name[1]) == intervals[name[0]] else '/OFF'
        for kind in ('Print', 'Export'):
            if usage.get('/'+kind, {}).get('/'+kind+'State') != expected:
                raise RuntimeError(f'{kind} must show only the interval endpoint: {name}')
        counts[name[0]] += 1
    for identity, last in intervals.items():
        if counts[identity] != last + 1:
            raise RuntimeError('Incomplete animation OCG family')
    print(f'PDF resource and playback clock checks passed ({len(checked)} intervals)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    check(parser.parse_args().pdf)
