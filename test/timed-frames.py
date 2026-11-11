"""The intermediate frames of a timed vector animation are well formed.

Run: python3 test/timed-frames.py growth-timed.pdf [--self-test] [-v]

A timed vector animation stores each frame as a Form XObject tied to its own
optional content group (OCG), named "<anim>.<k>". The default configuration
turns on only the last frame of each interval, so the plain render shows the
endpoint and nothing else. Four checks, on invariants alone (no stored
reference images):

  qq    q/Q balance. In every Form XObject reachable from every frame the
        graphics-state depth never goes below 0 and ends at 0. A pixel test
        cannot see most imbalances (a form boundary restores the state), so
        this reads the content streams with a real tokenizer: strings,
        comments and inline images are skipped, never counted.
  last  Rendering the last frame through the OCG switch is byte-identical to
        the plain render of the page.
  ink   Frame 0 has no flora ink, and ink grows from frame to frame over
        sampled frames 0, n/3, 2n/3 and n-1. Ink is the summed grey-level
        difference from the same page with every frame off. Tolerance:
        INK_FLOOR for "none" and a growth of at least INK_STEP between
        sampled frames, both in grey-level units at 72 dpi. The interval of
        a later overlay of a frame continues the flora of the one before: its
        frame 0 must instead equal the last frame of the previous interval
        (within INK_FLOOR). Which is which comes from the page labels: the
        pages of one beamer frame share a label prefix, so an animation on a
        page whose predecessor has the same prefix and carries an animation
        continues that one; every other animation starts from nothing.
  group Transparency groups. No frame form itself carries /Group (what the
        engine pinned in engine-ref.txt emits: the groups are on nested
        forms); every nested /Group dictionary is the same dictionary.

The OCG switch rewrites the catalog with `qpdf --update-from-json`; pages
are rendered with `pdftoppm -gray -r 72` and read back as PGM. Only
python3, qpdf and poppler-utils are needed.

--self-test also runs every check on mutated copies of the PDF and demands
that the check meant to catch the mutation fails: a check that never failed
proves nothing.
"""

import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

DPI = 72
# Antialiasing and compositing are deterministic for one poppler build, so a
# frame with no flora renders exactly as the blank page: the floor only keeps
# a rounding change in a future poppler from failing the test.
INK_FLOOR = 50
# Sampled frames differ by whole petals; the smallest step seen on
# growth-timed is about 50000 grey levels. A frame that did not grow gives a
# step near 0.
INK_STEP = 500

NAME = re.compile(r"^[ub]:(\d+)\.(\d+)$")
WORD = re.compile(rb"[^\s()<>\[\]{}/%]+")
INLINE_END = re.compile(rb"\sEI(?=[\s]|$)")


def operators(data):
    """Yield (operator, start, end) for each q and Q in a content stream."""
    i, n = 0, len(data)
    while i < n:
        c = data[i:i + 1]
        if c in (b" ", b"\t", b"\r", b"\n", b"\f", b"\0"):
            i += 1
        elif c == b"%":
            while i < n and data[i:i + 1] not in (b"\r", b"\n"):
                i += 1
        elif c == b"(":
            depth, i = 1, i + 1
            while i < n and depth:
                ch = data[i:i + 1]
                if ch == b"\\":
                    i += 1
                elif ch == b"(":
                    depth += 1
                elif ch == b")":
                    depth -= 1
                i += 1
        elif data[i:i + 2] in (b"<<", b">>"):
            i += 2
        elif c == b"<":
            i = data.find(b">", i) + 1 or n
        elif c == b"/":
            m = WORD.match(data, i + 1)
            i = m.end() if m else i + 1
        elif c in b"[]{})>":
            i += 1
        else:
            m = WORD.match(data, i)
            if not m:
                i += 1
                continue
            word = m.group()
            if word == b"BI":
                # Inline image: dictionary, ID, binary data, EI. The data is
                # opaque and may contain anything, q and Q included.
                end = INLINE_END.search(data, m.end())
                i = end.end() if end else n
                continue
            if word in (b"q", b"Q"):
                yield word.decode(), m.start(), m.end()
            i = m.end()


def balance(data):
    """Return (final depth, lowest depth) of a content stream."""
    depth = low = 0
    for op, _, _ in operators(data):
        depth += 1 if op == "q" else -1
        low = min(low, depth)
    return depth, low


class Doc:
    """A PDF read through qpdf's JSON: objects, pages, frames, stream data."""

    def __init__(self, path):
        self.path = str(path)
        out = subprocess.run(
            ["qpdf", "--json=2", "--json-key=qpdf", "--json-key=pages",
             "--json-stream-data=inline", "--decode-level=generalized", self.path],
            capture_output=True, check=True)
        full = json.loads(out.stdout)
        self.objects = full["qpdf"][1]
        self.pages = [p["object"] for p in full["pages"]]
        self.prefixes = [(p.get("label") or {}).get("/P") for p in full["pages"]]
        self.root_ref = self.objects["trailer"]["value"]["/Root"]
        self.root = self.val(self.root_ref)
        props = self.root["/OCProperties"]
        self.ocg_refs = self.val(props["/OCGs"])
        self.default = props["/D"]
        self.off = self.val(self.default["/OFF"])
        self.names = {r: self.val(r)["/Name"] for r in self.ocg_refs}
        self.frames = self.find_frames()

    def val(self, x):
        if isinstance(x, str) and x.endswith(" R"):
            return self.objects["obj:" + x]["value"]
        return x

    def stream(self, ref):
        return self.objects["obj:" + ref].get("stream")

    def stream_dict(self, ref):
        s = self.stream(ref)
        return s["dict"] if s else None

    def xobjects(self, dic):
        res = self.val(dic.get("/Resources"))
        return self.val(res.get("/XObject")) if res and "/XObject" in res else {}

    def page_xobjects(self, page_ref):
        page = self.val(page_ref)
        while "/Resources" not in page and "/Parent" in page:
            page = self.val(page["/Parent"])
        return self.xobjects(page)

    def find_frames(self):
        """anim -> page number -> {k: form ref}, from the OC of page forms."""
        frames = {}
        for number, page_ref in enumerate(self.pages, 1):
            for ref in self.page_xobjects(page_ref).values():
                d = self.stream_dict(ref)
                if d is None or "/OC" not in d:
                    continue
                m = NAME.match(self.names.get(d["/OC"], ""))
                if m:
                    anim, k = int(m.group(1)), int(m.group(2))
                    frames.setdefault(anim, {}).setdefault(number, {})[k] = ref
        return frames

    def previous_interval(self, anim):
        """The animation this one continues, or None for a fresh start."""
        number = min(self.frames[anim])
        before = number - 1
        prefix = self.prefixes[number - 1]
        if before < 1 or prefix is None or self.prefixes[before - 1] != prefix:
            return None
        return next((a for a, pages in self.frames.items()
                     if a != anim and before in pages), None)

    def data(self, ref):
        return base64.b64decode(self.stream(ref)["data"])

    def reachable(self, ref):
        """Every Form XObject below a frame form, the form itself first."""
        seen, todo, order = set(), [ref], []
        while todo:
            cur = todo.pop()
            if cur in seen:
                continue
            seen.add(cur)
            d = self.stream_dict(cur)
            if d is None or d.get("/Subtype") != "/Form":
                continue
            order.append(cur)
            todo.extend(self.xobjects(d).values())
        return order

    def ocg_for(self, anim, k):
        want = "%d.%d" % (anim, k)
        return next(r for r, name in self.names.items() if name[2:] == want)


def amount(frames):
    """Frame count of an animation, or None when the pages disagree."""
    ns = {len(f) for f in frames.values()}
    return ns.pop() if len(ns) == 1 else None


def pgm(path):
    with open(path, "rb") as f:
        raw = f.read()
    m = re.match(rb"P5\s+(\d+)\s+(\d+)\s+255\s", raw)
    w, h = int(m.group(1)), int(m.group(2))
    body = raw[m.end():]
    assert len(body) == w * h
    return body


def render(pdf, page, work, tag):
    base = os.path.join(work, tag)
    subprocess.run(["pdftoppm", "-gray", "-r", str(DPI), "-f", str(page),
                    "-l", str(page), "-singlefile", str(pdf), base], check=True)
    return pgm(base + ".pgm")


def rewrite(src, dst, objects):
    """qpdf --update-from-json with the given objects: ref -> JSON object."""
    body = {"obj:" + ref: value for ref, value in objects.items()}
    update = {"version": 2, "parameters": {"decodelevel": "generalized"},
              "qpdf": [{"jsonversion": 2, "pushedinheritedpageresources": False,
                        "calledgetallpages": False}, body]}
    tmp = str(dst) + ".json"
    with open(tmp, "w") as f:
        json.dump(update, f)
    subprocess.run(["qpdf", str(src), "--update-from-json=" + tmp, str(dst)],
                   check=True, capture_output=True)


def only_on(doc, work, tag, keep):
    """A copy of the PDF with exactly the OCGs in keep switched on."""
    root = json.loads(json.dumps(doc.root))
    root["/OCProperties"]["/D"]["/OFF"] = [r for r in doc.ocg_refs if r not in keep]
    dst = os.path.join(work, tag + ".pdf")
    rewrite(doc.path, dst, {doc.root_ref: {"value": root}})
    return dst


def check_qq(doc, work, log):
    fails, forms = [], set()
    for anim, pages in sorted(doc.frames.items()):
        for k, ref in sorted(next(iter(pages.values())).items()):
            for form in doc.reachable(ref):
                if form in forms:
                    continue
                forms.add(form)
                depth, low = balance(doc.data(form))
                if depth or low < 0:
                    fails.append("form %s (below frame %d.%d): final depth %d, lowest %d"
                                 % (form, anim, k, depth, low))
    if not forms:
        fails.append("no frame forms found")
    log("qq: %d forms checked over %d animations" % (len(forms), len(doc.frames)))
    return fails


def check_last(doc, work, log):
    fails = []
    for anim, pages in sorted(doc.frames.items()):
        n = amount(pages)
        if n is None or sorted(next(iter(pages.values()))) != list(range(n)):
            fails.append("animation %d: frames are not 0..n-1 on every page" % anim)
            continue
        switched = only_on(doc, work, "last%d" % anim, {doc.ocg_for(anim, n - 1)})
        for number in sorted(pages):
            plain = render(doc.path, number, work, "plain%d_%d" % (anim, number))
            last = render(switched, number, work, "lastr%d_%d" % (anim, number))
            differ = sum(a != b for a, b in zip(plain, last))
            log("last: animation %d page %d, frame %d: %d pixels differ"
                % (anim, number, n - 1, differ))
            if plain != last:
                fails.append("animation %d page %d: last frame differs from the plain "
                             "render in %d pixels" % (anim, number, differ))
    if not doc.frames:
        fails.append("no animations found")
    return fails


def check_ink(doc, work, log):
    fails = []
    blank_pdf = only_on(doc, work, "blank", set())
    ended = {}
    for anim, pages in sorted(doc.frames.items()):
        number = min(pages)
        n = amount(pages)
        if n is None or n < 4:
            fails.append("animation %d: too few frames (%s) to sample" % (anim, n))
            continue
        blank = render(blank_pdf, number, work, "blank%d" % anim)
        samples = sorted({0, n // 3, 2 * n // 3, n - 1})
        ink = []
        for k in samples:
            pdf = only_on(doc, work, "ink%d_%d" % (anim, k), {doc.ocg_for(anim, k)})
            shot = render(pdf, number, work, "inkr%d_%d" % (anim, k))
            ink.append(sum(abs(a - b) for a, b in zip(blank, shot)))
        log("ink: animation %d page %d, frames %s: %s" % (anim, number, samples, ink))
        ended[anim] = ink[-1]
        before = doc.previous_interval(anim)
        start = 0 if before is None else ended.get(before)
        log("ink: animation %d %s" % (anim, "starts fresh" if before is None
                                          else "continues animation %d" % before))
        if start is None:
            fails.append("animation %d: continues animation %d, which was not measured"
                         % (anim, before))
        elif abs(ink[0] - start) > INK_FLOOR:
            fails.append("animation %d: frame 0 has ink %d, expected %d (%s; "
                         "tolerance %d)" % (anim, ink[0], start,
                         "a fresh start" if before is None else
                         "the end of animation %d" % before, INK_FLOOR))
        for (k0, i0), (k1, i1) in zip(zip(samples, ink), zip(samples[1:], ink[1:])):
            if i1 < i0 + INK_STEP:
                fails.append("animation %d: ink from frame %d to %d is %d to %d, "
                             "growth under %d" % (anim, k0, k1, i0, i1, INK_STEP))
    return fails


def check_group(doc, work, log):
    fails, nested, kinds = [], 0, set()
    for anim, pages in sorted(doc.frames.items()):
        shapes = set()
        for k, ref in next(iter(pages.values())).items():
            shapes.add(json.dumps(doc.stream_dict(ref).get("/Group"), sort_keys=True))
            for form in doc.reachable(ref)[1:]:
                group = doc.stream_dict(form).get("/Group")
                if group is not None:
                    nested += 1
                    kinds.add(json.dumps(group, sort_keys=True))
        if shapes != {"null"}:
            fails.append("animation %d: frame forms carry /Group: %s"
                         % (anim, sorted(shapes - {"null"})))
    if len(kinds) > 1:
        fails.append("nested /Group dictionaries differ: %s" % sorted(kinds))
    log("group: frame forms carry none; %d nested /Group, %d distinct"
        % (nested, len(kinds)))
    return fails


CHECKS = {"qq": check_qq, "last": check_last, "ink": check_ink, "group": check_group}


def run(pdf, work, only=None, log=lambda s: None):
    doc = Doc(pdf)
    return {name: fn(doc, work, log) for name, fn in CHECKS.items()
            if not only or name in only}


# --- mutations ---------------------------------------------------------

def stream_update(doc, ref, data=None, dict_changes=None):
    s = doc.stream(ref)
    d = json.loads(json.dumps(s["dict"]))
    for key, value in (dict_changes or {}).items():
        d[key] = value
    payload = s["data"] if data is None else base64.b64encode(data).decode()
    return {"stream": {"dict": d, "data": payload}}


def frames_of(doc, anim):
    pages = doc.frames[anim]
    return pages[min(pages)]


def mut_drop_q(doc, work):
    """Drop the first Q of one nested form deep in a middle frame."""
    frames = frames_of(doc, 1 if 1 in doc.frames else min(doc.frames))
    ref = frames[len(frames) // 2]
    for form in doc.reachable(ref)[2:]:
        data = doc.data(form)
        ops = [o for o in operators(data) if o[0] == "Q"]
        if ops:
            _, start, end = ops[0]
            dst = os.path.join(work, "mut-qq.pdf")
            rewrite(doc.path, dst, {form: stream_update(doc, form, data[:start] + data[end:])})
            return dst, "dropped the first Q of nested form %s" % form
    raise RuntimeError("no nested form with a Q")


def mut_wrong_default(doc, work):
    """The default view shows frame n-2 instead of the last frame."""
    anim = min(doc.frames)
    n = amount(doc.frames[anim])
    off = [r for r in doc.off if r != doc.ocg_for(anim, n - 2)]
    off.append(doc.ocg_for(anim, n - 1))
    obj = doc.default["/OFF"]
    dst = os.path.join(work, "mut-last.pdf")
    if isinstance(obj, str):
        rewrite(doc.path, dst, {obj: {"value": off}})
    else:
        root = json.loads(json.dumps(doc.root))
        root["/OCProperties"]["/D"]["/OFF"] = off
        rewrite(doc.path, dst, {doc.root_ref: {"value": root}})
    return dst, "default view of animation %d shows frame %d, not %d" % (anim, n - 2, n - 1)


def mut_blank_frame(doc, work):
    """A sampled middle frame's form content is emptied."""
    anim = min(doc.frames)
    frames = frames_of(doc, anim)
    k = len(frames) // 3
    dst = os.path.join(work, "mut-ink.pdf")
    rewrite(doc.path, dst, {frames[k]: stream_update(doc, frames[k], b" ")})
    return dst, "content of frame %d.%d emptied" % (anim, k)


def mut_swap_oc(doc, work):
    """Frames 0 and n-1 of an animation trade their /OC."""
    anim = min(doc.frames)
    frames = frames_of(doc, anim)
    first, last = frames[0], frames[len(frames) - 1]
    oc0 = doc.stream_dict(first)["/OC"]
    oc1 = doc.stream_dict(last)["/OC"]
    dst = os.path.join(work, "mut-swap.pdf")
    rewrite(doc.path, dst, {
        first: stream_update(doc, first, dict_changes={"/OC": oc1}),
        last: stream_update(doc, last, dict_changes={"/OC": oc0})})
    return dst, "frames %d.0 and %d.%d swapped /OC" % (anim, anim, len(frames) - 1)


def mut_frame_group(doc, work):
    """One frame form gains a transparency group."""
    anim = min(doc.frames)
    frames = frames_of(doc, anim)
    k = len(frames) // 2
    group = {"/S": "/Transparency", "/I": True, "/K": False}
    dst = os.path.join(work, "mut-group.pdf")
    rewrite(doc.path, dst, {frames[k]: stream_update(doc, frames[k], dict_changes={"/Group": group})})
    return dst, "frame form %d.%d gained /Group" % (anim, k)


def mut_nested_group(doc, work):
    """One nested /Group dictionary differs from the rest."""
    for anim, pages in sorted(doc.frames.items()):
        for ref in next(iter(pages.values())).values():
            for form in doc.reachable(ref)[1:]:
                if "/Group" in doc.stream_dict(form):
                    group = dict(doc.stream_dict(form)["/Group"], **{"/K": True})
                    dst = os.path.join(work, "mut-nested.pdf")
                    rewrite(doc.path, dst, {form: stream_update(doc, form, dict_changes={"/Group": group})})
                    return dst, "nested form %s has /K true" % form
    raise RuntimeError("no nested /Group to mutate")


def mut_empty_continuation(doc, work):
    """Frame 0 of an animation that continues another is emptied."""
    anim = next(a for a in sorted(doc.frames) if doc.previous_interval(a) is not None)
    first = frames_of(doc, anim)[0]
    dst = os.path.join(work, "mut-cont.pdf")
    rewrite(doc.path, dst, {first: stream_update(doc, first, b" ")})
    return dst, "content of frame %d.0, which continues animation %d, emptied" % (
        anim, doc.previous_interval(anim))


# (check that must fail, mutation)
MUTATIONS = [
    ("qq", mut_drop_q),
    ("last", mut_wrong_default),
    ("ink", mut_blank_frame),
    ("ink", mut_swap_oc),
    ("ink", mut_empty_continuation),
    ("group", mut_frame_group),
    ("group", mut_nested_group),
]


def self_test(pdf, work, log):
    base = Doc(pdf)
    ok = True
    for name, make in MUTATIONS:
        mutated, what = make(base, work)
        fails = run(mutated, work, only={name}, log=log)[name]
        print("MUTATION %-5s %s" % (name, what))
        if fails:
            for f in fails:
                print("    FAILS as it should: %s" % f)
        else:
            print("    NOT CAUGHT: check %s passed on the mutated PDF" % name)
            ok = False
    return ok


def main(argv):
    args = [a for a in argv if not a.startswith("-")]
    if len(args) != 1:
        sys.exit(__doc__)
    log = print if "-v" in argv else (lambda s: None)
    pdf = Path(args[0]).resolve()
    with tempfile.TemporaryDirectory() as work:
        results = run(pdf, work, log=log)
        status = 0
        for name, fails in results.items():
            print("%s %s" % ("FAIL" if fails else "PASS", name))
            for f in fails:
                print("    " + f)
            status |= bool(fails)
        if "--self-test" in argv:
            if status:
                sys.exit("the real PDF fails; not running the mutations")
            if not self_test(pdf, work, log):
                status = 1
        sys.exit(status)


if __name__ == "__main__":
    main(sys.argv[1:])
