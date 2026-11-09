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
Other local verification overlapped part of the baseline title run.

## Results

| Fixture / cache | Before (s) | After (s) |
| --- | ---: | ---: |
| Dense title, cold | 539.4 | 391.9 |
| Dense title, warm | 28.6 | 5.4 |

| Dense title, cold | Before | After |
| --- | ---: | ---: |
| Measurement LaTeX (s) | 74.6 | 4.9 |
| Lua/PDF export (s) | 260.4 | 246.6 |
| Rasterization and builder overhead (s) | 146.2 | 129.7 |
| Final LaTeX (s) | 58.2 | 10.7 |
| Largest subprocess RSS (MiB) | 901.5 | 871.6 |
| Peak output plus scratch disk (MiB) | 1347.7 | 1346.8 |

The adapter removes most LaTeX planning cost. PDF export is now the largest
remaining step; it is separate motor work and is not changed in this PR.
The engine pin, cache format, builder CLI and defaults are unchanged.

## Correctness checks

- The small raster fixture and dense title have identical geometry manifests
  and byte-identical PNG samples before and after (10 and 161 samples).
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
