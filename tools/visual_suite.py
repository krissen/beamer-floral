"""Compile the reusable visual template across themes and aspect ratios."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import json
import html
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
THEMES = ['floral', 'default', 'Madrid', 'Berlin', 'Copenhagen', 'Singapore',
          'Warsaw', 'Boadilla']


def export_screenshots(output, destination, env):
    """Use the same acceptance PDFs for documentation screenshots."""
    pages = {
        'title': ('169-floral', 1), 'title-long': ('169-floral', 5),
        'palette-warm': ('169-floral', 10), 'palette-blue': ('169-floral', 15),
        'palette-green': ('169-floral', 16), 'stock-default': ('169-default', 10),
        'stock-madrid': ('169-Madrid', 10), 'stock-berlin': ('169-Berlin', 10),
    }
    missing = sorted({document for document, _ in pages.values()
                      if not (output / (document + '.pdf')).exists()})
    if missing:
        raise SystemExit('Screenshot export needs these comparison PDFs: ' + ', '.join(missing))
    # Layout/density scenes are also an executable documentation fixture in CI.
    build = output / 'build/documentation-showcase'
    build.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(['latexmk', '-norc', '-lualatex', '-interaction=nonstopmode',
                             '-halt-on-error', f'-outdir={build}', str(ROOT / 'docs/src/showcase.tex')],
                            cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (output / 'diagnostics/documentation-showcase-build.txt').write_text(result.stdout)
    if result.returncode:
        raise SystemExit('Documentation showcase failed; see diagnostics/documentation-showcase-build.txt')
    log = (build / 'showcase.log').read_text(errors='replace')
    if re.search(r'Overfull|Underfull|Warning:|^!', log, re.MULTILINE):
        raise SystemExit('Documentation showcase has diagnostics; inspect its log before exporting')
    pages.update({'layout-left': ('documentation-showcase', 5),
                  'layout-surround': ('documentation-showcase', 6),
                  'density-light': ('documentation-showcase', 7),
                  'density-dense': ('documentation-showcase', 8)})
    destination.mkdir(parents=True, exist_ok=True)
    for name, (document, page) in pages.items():
        source = build / 'showcase.pdf' if document == 'documentation-showcase' else output / (document + '.pdf')
        subprocess.run(['pdftoppm', '-f', str(page), '-singlefile', '-scale-to', '1800',
                        '-png', str(source), str(destination / name)], check=True)


def write_index(output, results):
    rows = []
    for row in results:
        name = html.escape(row['name'])
        status = 'Unsupported sidebar layout' if row.get('compatibility') else ('Compiled' if row['success'] else 'FAILED')
        rows.append(f'<tr><td><a href="{name}.pdf">{name}</a></td>'
                    f'<td><a href="previews/{name}-overview.jpg">Contact sheet</a></td>'
                    f'<td>{status}; {len(row["warnings"])} diagnostics, '
                    f'{len(row.get("introduced", []))} introduced</td></tr>')
    (output / '00-START-HERE.html').write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Floral visual review</title>'
        '<style>body{font:17px system-ui;max-width:1000px;margin:3em auto;background:#faf8f4;color:#29232a}'
        'td,th{padding:.5em 1em;text-align:left;border-bottom:1px solid #ddd}a{color:#8e174a}'
        'li{margin:.4em 0}table{border-collapse:collapse}</style>'
        '<h1>Floral visual review</h1><p>The same English content and seed in every PDF. '
        '169 = 16:9, 43 = 4:3. Follow a PDF or contact-sheet link.</p>'
        '<p>All examples use the package defaults: 2.5 cm left and 1 cm right. '
        'Narrow inherited Beamer margins are unsuitable for floral borders.</p>'
        '<h2>Page guide</h2><ul><li>1–5: title pages, from short to very long titles and subtitles.</li>'
        '<li>6–8: frame headings of increasing length. 9: an untitled frame after a long heading.</li>'
        '<li>10: blocks. 11: columns, nested lists and a table. 12–13: overlays.</li>'
        '<li>14: a plain frame. 15–16: blue and green palettes.</li></ul>'
        '<table><tr><th>PDF</th><th>Overview</th><th>Build result</th></tr>' + ''.join(rows) + '</table>'
        '<p>Compilation does not imply visual approval. Sidebar themes can cover the flora '
        'and are not part of the recommended set.</p>'
        '<p>Details: <a href="00-READ-ME.md">read me</a> and '
        '<a href="diagnostics/results.json">build diagnostics</a>.</p></html>')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/visual-review')
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=3)
    parser.add_argument('--themes', nargs='+', default=THEMES)
    parser.add_argument('--aspects', nargs='+', choices=['169', '43'], default=['169', '43'])
    parser.add_argument('--force', action='store_true', help='force recompilation of the selected cases')
    parser.add_argument('--screenshots', type=Path, help='export selected acceptance pages as documentation PNGs')
    args = parser.parse_args()
    output = args.output.resolve()
    for folder in ('sources', 'build', 'previews', 'diagnostics'):
        (output / folder).mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env['TEXINPUTS'] = f'{ROOT}:{args.engine.resolve()}/tex//:'
    env['FLORA_LUA'] = str(args.engine.resolve() / 'lua')
    manifest = {
        'engine_commit': subprocess.check_output(['git', '-C', str(args.engine), 'rev-parse', 'HEAD'], text=True).strip(),
        'package_commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
        'package_dirty': bool(subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], text=True).strip()),
        'seed': 3, 'density': 1.2, 'requested_themes': args.themes,
        'template': str(ROOT / 'test/visual/template.tex'),
    }
    (output / 'diagnostics/manifest.json').write_text(json.dumps(manifest, indent=2))
    cases = [(theme, aspect, 'wide') for aspect in args.aspects for theme in args.themes]

    def compile_case(case, baseline=False):
        theme, aspect, margins = case
        name = f'{aspect}-{theme}'
        if baseline:
            name += '-without-flora'
        source = output / 'sources' / (name + '.tex')
        source.write_text(f'\\def\\VisualTheme{{{theme}}}\n\\def\\VisualAspect{{{aspect}}}\n'
                          + ('\\def\\VisualBaseline{1}\n' if baseline else '')
                          + '\\input{' + str(ROOT / 'test/visual/template.tex') + '}\n')
        build = output / 'build' / name
        build.mkdir(exist_ok=True)
        result = subprocess.run(['latexmk', *(['-g'] if args.force else []), '-norc', '-lualatex', '-interaction=nonstopmode',
                                 '-halt-on-error', f'-outdir={build}', str(source)],
                                cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (output / 'diagnostics' / (name + '-build.txt')).write_text(result.stdout)
        log = (build / (name + '.log')).read_text(errors='replace') if (build / (name + '.log')).exists() else result.stdout
        warnings = []
        compatibility = []
        current = 'preamble'
        for line in log.splitlines():
            if 'VISUAL-CASE:' in line:
                current = line.split('VISUAL-CASE:', 1)[1].strip()
            if 'Package beamer-floral Warning: Sidebar theme detected.' in line:
                compatibility.append('Sidebar occupies the floral margin; not visually supported')
            elif re.search(r'Overfull|Underfull|Warning:|^!', line):
                warnings.append({'case': current, 'message': line})
        if result.returncode == 0:
            target = output / (name + '.pdf') if not baseline else output / 'diagnostics' / (name + '.pdf')
            shutil.copyfile(build / (name + '.pdf'), target)
            if not baseline:
                prefix = output / 'previews' / name
                subprocess.run(['pdftoppm', '-scale-to', '600', '-png', str(target), str(prefix)], check=True)
                from PIL import Image, ImageDraw
                pages = sorted(p for p in (output / 'previews').glob(name + '-*.png')
                               if re.fullmatch(re.escape(name) + r'-\d+\.png', p.name))
                sheet = Image.new('RGB', (1800, ((len(pages)+2)//3)*480), '#dddddd')
                draw = ImageDraw.Draw(sheet)
                for i, page in enumerate(pages):
                    x, y = i%3*600, i//3*480
                    draw.text((x+8, y+5), page.stem, fill='black')
                    sheet.paste(Image.open(page), (x, y+24))
                sheet.save(output / 'previews' / (name + '-overview.jpg'))
        return {'name': name, 'theme': theme, 'aspect': aspect, 'margins': margins,
                'success': result.returncode == 0, 'warnings': warnings, 'compatibility': compatibility}

    results = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(compile_case, case): case for case in cases}
        for future in as_completed(futures):
            row = future.result()
            results.append(row)
            status = 'UNSUPPORTED (sidebar)' if row['compatibility'] else ('compiled' if row['success'] else 'FAILED')
            print(f"{row['name']}: {status}, {len(row['warnings'])} diagnostics", flush=True)
    # Diagnose suspect stock-theme results against exactly the same document
    # without the floral package. Never dismiss newly introduced box warnings.
    for row in results:
        if row['warnings'] and row['theme'] != 'floral':
            row['baseline'] = compile_case((row['theme'], row['aspect'], row['margins']), baseline=True)
    previous_path = output / 'diagnostics/results.json'
    if previous_path.exists():
        previous = {row['name']: row for row in json.loads(previous_path.read_text())
                    if row['theme'] in THEMES and row.get('margins') == 'wide'}
        previous.update({row['name']: row for row in results})
        results = list(previous.values())
    results.sort(key=lambda r: r['name'])
    for row in results:
        baseline = Counter((w['case'], w['message']) for w in row.get('baseline', {}).get('warnings', []))
        row['introduced'] = []
        for warning in row['warnings']:
            key = warning['case'], warning['message']
            if baseline[key]:
                baseline[key] -= 1
            else:
                row['introduced'].append(warning)
    (output / 'diagnostics/results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
    lines = ['# Visual review suite', '', 'The same 16 pages in every PDF. 169 = 16:9; 43 = 4:3.',
             'All examples use the package defaults: 2.5 cm left and 1 cm right.',
             '', 'Page guide:', '',
             '1–5: title pages, from short to very long titles and subtitles.',
             '6–8: frame headings of increasing length.',
             '9: an untitled frame after a long heading. 10: blocks.',
             '11: columns, nested lists and a table. 12–13: overlays with changing headings and content.',
             '14: a plain frame. 15–16: blue and green palettes.', '',
             'Contact sheets and screenshot-ready page images are in previews/.',
             'Build logs and stock-theme baselines are in diagnostics/.', '',
             '## Build results', '']
    for row in results:
        lines.append(f"- {row['name']}: {'compiled' if row['success'] else 'FAILED'}, {len(row['warnings'])} diagnostics, {len(row['introduced'])} introduced")
        for note in row.get('compatibility', []):
            lines.append(f'  - NOT VISUALLY SUPPORTED: {note}')
        for warning in row['warnings']:
            lines.append(f"  - {warning['case']}: {warning['message']}")
    (output / '00-READ-ME.md').write_text('\n'.join(lines)+'\n')
    write_index(output, results)
    if any(not r['success'] or not r.get('baseline', {'success': True})['success'] for r in results):
        raise SystemExit('Some documents failed; see diagnostics/results.json')
    if any(r['introduced'] for r in results):
        raise SystemExit('New diagnostics require investigation; see diagnostics/results.json')
    if args.screenshots:
        export_screenshots(output, args.screenshots, env)
    print(f'Results: {output}', flush=True)


if __name__ == '__main__':
    main()
