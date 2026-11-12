# Reusing one drawing

Flora normally adapts to each frame: it grows into the room the text leaves
and around the frame title, so every frame gets its own drawing. For a long
deck, `reuse` draws one picture per page class instead and puts it on every
page of that class:

```tex
\florasetup{reuse=content}            % ordinary frames share one drawing
\florasetup{reuse=all}                % title, section and content pages
\florasetup{reuse={title, section}}   % any combination
\florathisframe{reuse=none}           % this frame adapts as usual
```

Title pages are those that call `\titlepage`, and section pages those that
call `\sectionpage`, in any theme. A reused drawing keeps the whole text
block clear and does not measure the content. Frames with a title share one
drawing per title height (one line, two lines), and frames without one share
another. A different reservation, `\florathisframe` setting or page geometry
gives that frame its own drawing, which later frames with the same settings
reuse. Growing frames keep their own drawings, and so does a frame that an
integration draws with its own `render_page` callback. Pattern frames keep
their own drawings too (see [Patterns](patterns.md)). The drawing is cached with the
other flora, so later compiles do not draw it again.

Each reused page still carries its own running-head mark, sized and placed
by that page's title as on an adaptive page. Its kind comes with the class
drawing, so the pages of a class show one kind, and its rule stops where
the shared drawing's stems run, so it can be longer than on an adaptive
page. In body mode the mark lies over the hero bloom, not under it. Between runs a reused frame keeps only its
marks, so an edit asks for another run only when it changes a mark (adds
one, removes it, or changes its size or place) or the frame's overlay
count; a title or body line that only grows wider asks for none.

What you give up:

- Flora no longer fills the empty space inside short frames; it stays in the
  margins.
- Every page of a class looks the same.
- On titled frames the top edge carries no flora, since the title's width is
  not measured.
- With `title` in the list, the title page is much plainer than its usual
  full composition. `reuse=content` leaves title pages as they are.

Measured build times and PDF sizes, adaptive against `reuse`, the method and
how to repeat the measurements are in
[performance](../dev/performance.md#build-times-adaptive-and-reuse).
