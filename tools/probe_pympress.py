"""Run pympress on a deck and record what its media overlays do.

Visits the pages given on the command line inside the pympress process and
logs, per visit: overlay events, every on-screen GIF repaint with its cost,
peak memory, and the content window's own drawing (never the screen). The
drawing is sampled densely right after each page change, as an "ink" count of
pixels that are neither white nor black, so that a flash of stale or missing
content shows up as a jump in the series.

Usage: <pympress python> tools/probe_pympress.py <outdir> <deck.pdf> <seconds-per-page> <page>...
"""
import resource
import sys
import time
from pathlib import Path

import cairo
from gi.repository import GLib

from pympress.__main__ import main  # first: installs gettext for the other modules
from pympress import ui  # noqa: I001
from pympress.media_overlays import base, gif_backend

out = Path(sys.argv[1])
dwell = float(sys.argv[3])
visits = [int(page) for page in sys.argv[4:]]
log = open(out / "events.log", "w", buffering=1)
state = {"probing": False, "visit": 0}


def note(*fields):
    log.write(" ".join(str(f) for f in (f"{time.time():.4f}", *fields)) + "\n")


def logged(cls, name, describe):
    original = getattr(cls, name)

    def wrapper(self, *args, **kwargs):
        started = time.time()
        result = original(self, *args, **kwargs)
        if not state["probing"]:
            note(name, id(self), describe(self, *args), f"{(time.time() - started) * 1000:.1f}ms")
        return result
    setattr(cls, name, wrapper)


logged(gif_backend.GifOverlay, "draw", lambda self, widget, ctx: widget.get_allocated_width())
logged(gif_backend.GifOverlay, "_set_file", lambda self, path: path.name)
logged(base.VideoOverlay, "show", lambda self: type(self).__name__)
logged(base.VideoOverlay, "do_hide", lambda self, *a: type(self).__name__)
logged(base.VideoOverlay, "handle_end", lambda self: type(self).__name__)
try:
    from pympress.media_overlays import gst_backend
    logged(gst_backend.GstOverlay, "_set_file", lambda self, path: path.name)
    logged(gst_backend.GstOverlay, "do_play", lambda self: "play")
except Exception as error:  # the backend is optional
    note("gst-unavailable", 0, error)

original_init = ui.UI.__init__


def init(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    state["ui"] = self


ui.UI.__init__ = init


def render(scale):
    window = state["ui"].c_win
    width, height = window.get_allocated_width(), window.get_allocated_height()
    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, int(width * scale), int(height * scale))
    context = cairo.Context(surface)
    context.scale(scale, scale)
    state["probing"] = True
    try:
        window.draw(context)
    finally:
        state["probing"] = False
    return surface


def snapshot(label):
    render(1).write_to_png(str(out / f"shot-{label}.png"))
    note("snapshot", 0, label)
    return False


def ink(visit, until, pause):
    if visit != state["visit"]:
        return False
    surface = render(0.25)
    blue = bytes(surface.get_data())[0::4]
    note("ink", 0, visit, len(blue) - blue.count(b"\xff") - blue.count(b"\x00"))
    if time.time() < until:
        return True
    if pause < 250:  # the dense burst is over: keep a slow series for the rest of the visit
        GLib.timeout_add(250, ink, visit, time.time() + dwell, 250)
    return False


def memory():
    note("rss", 0, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 2**20)
    return True


def step():
    app = state["ui"]
    if state["visit"] >= len(visits):
        app.app.quit()
        return False
    page = visits[state["visit"]]
    state["visit"] += 1
    visit = state["visit"]
    note("page", 0, visit, page)
    app.goto_page(page - 1)
    ink(visit, time.time() + 1.5, 25)
    GLib.timeout_add(25, ink, visit, time.time() + 1.5, 25)
    GLib.timeout_add(int(dwell * 350), snapshot, f"{visit}-p{page}-mid")
    GLib.timeout_add(int(dwell * 920), snapshot, f"{visit}-p{page}-end")
    return True


def start():
    window = state["ui"].c_win
    note("window", 0, window.get_allocated_width(), window.get_allocated_height(),
         "scale", window.get_scale_factor())
    GLib.timeout_add(500, memory)
    GLib.timeout_add(int(dwell * 1000), step)
    step()
    return False


GLib.timeout_add(6000, start)

main([sys.argv[0], sys.argv[2]])
