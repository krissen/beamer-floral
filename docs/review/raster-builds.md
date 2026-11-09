# Raster adapter build measurements

The raster adapter checks the image cache before constructing growth plans.
On measurement-pass misses it collects the manifest and returns without
painting flora. The measurement PDF is an intermediate, not a deliverable.
The export worker retains plan-dependent stage validation.

## Setup

Measured on the same local machine with engine
`ff218774e205828f2d26026110797d4230a46126`, exported to a separate directory
so concurrent engine development could not invalidate a running build.
Both versions use 144 dpi and two raster jobs. The baseline is the parent of
`48bfe4f`; the optimized adapter is `c665197`.

The dense title is `test/growth-benchmark.tex` with `[vector]` replaced by
`[raster]`: density 1.2, eight seconds, 20 fps, 161 PNG samples. The slideshow
is `test/size-benchmark.tex` with `\def\floralvariant{raster}`: eleven
logical frames, 21 PDF pages, eight seconds and 20 fps per frame.
Each cold run uses a new output directory; its warm run reuses that directory.
Commands use `python3 tools/build_animation.py --engine <frozen-engine>
--outdir <output> <source>` with the default dpi and jobs.

Wall times cover the complete builder, including both LaTeX invocations,
Lua/PDF export and rasterization. Each subprocess was wrapped with macOS
`/usr/bin/time -l`; RSS is the largest individual subprocess maximum, not the
sum of concurrent raster processes. Disk is the maximum sampled output-tree
size (500 ms intervals), including scratch PDFs, cache PNGs and final output.
These are single local observations, not repeated statistical estimates.
Other local verification overlapped the first baseline title run (539.4 s
cold, 28.6 s warm), so the title baseline below is a repeat without that load.
The optimized slideshow run overlapped other local work at its end.

## Results

| Fixture / cache | Before (s) | After (s) | Change |
| --- | ---: | ---: | ---: |
| Dense title, cold | 514.3 | 391.9 | -23.8% |
| Dense title, warm | 27.5 | 5.4 | -80.5% |
| Slideshow, cold | 1388.9 | 1228.3 | -11.6% |
| Slideshow, warm | 95.8 | 51.9 | -45.8% |

| Cold build | Title before | Title after | Slides before | Slides after |
| --- | ---: | ---: | ---: | ---: |
| Measurement LaTeX (s) | 81.3 | 4.9 | 167.2 | 5.9 |
| Lua/PDF export (s) | 248.6 | 246.6 | 720.7 | 772.2 |
| Rasterization and builder overhead (s) | 129.7 | 129.7 | 319.9 | 355.6 |
| Final LaTeX (s) | 54.7 | 10.7 | 181.1 | 94.6 |
| Largest subprocess RSS (MiB) | 877.4 | 871.6 | 1273.8 | 1168.2 |
| Peak output plus scratch disk (MiB) | 1369.6 | 1346.8 | 4038.1 | 4000.2 |

The adapter does not change export or rasterization code, so the slideshow's
higher values in those two rows are not attributed to it; those runs were not
isolated from other local work.

The adapter removes most LaTeX planning cost. PDF export is now the largest
remaining step, about 63% of the cold build for both fixtures; it is separate
motor work and is not changed in this PR.
The engine pin, cache format, builder CLI and defaults are unchanged.

## Correctness checks

- The small raster fixture, dense title and slideshow have identical geometry
  manifests and byte-identical PNG samples before and after (10, 161 and 1771
  samples).
- Cache hit and measurement miss adapter tests forbid `plan`, `stages` and
  `render`; ordinary builds still reject missing or stale caches.
- Worker tests cover cold, warm and partial caches, level mismatch and a
  rendering exception. A separate builder test proves a failed raster job
  cannot replace the previous index.
- `test/raster-geometry.tex` forbids growth planning in every LaTeX pass and
  covers a title page, changing overlay titles, three overlays, reservations
  and cleared reservations. The warm builder exports zero new samples and
  asserts unchanged geometry after convergence; the PDF has five pages.
- PDF checks exercise playback catch-up, endpoints, replay, startup resources,
  final posters, print and export OCG states.
- Standalone extracted static, vector and raster examples compile without
  local development paths. Full GitHub CI passes on `c665197`.
