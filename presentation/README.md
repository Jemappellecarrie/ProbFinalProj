# Presentation

This folder contains the final-project presentation source and output for the
Connections Puzzle Generator.

## Files

- `connections_generator_presentation.tex`
  Main Beamer source for the presentation deck.
- `connections_generator_presentation.pdf`
  Compiled presentation output.
- `assets/showcase.png`
  Product showcase image used in the product/demo slides.
- `build.sh`
  Local build script. Defaults to `pdflatex` and can be overridden with
  `LATEX_ENGINE=...`.

## Build

```bash
cd presentation
./build.sh
```

If you want to use another engine:

```bash
cd presentation
LATEX_ENGINE=xelatex ./build.sh
```

The script compiles the PDF in-place and removes common LaTeX auxiliary files
so artifacts stay contained inside this folder.
