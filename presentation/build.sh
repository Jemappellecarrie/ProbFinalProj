#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

ENGINE="${LATEX_ENGINE:-pdflatex}"

"${ENGINE}" -interaction=nonstopmode -halt-on-error connections_generator_presentation.tex >/tmp/connections_presentation_build.log
"${ENGINE}" -interaction=nonstopmode -halt-on-error connections_generator_presentation.tex >>/tmp/connections_presentation_build.log

rm -f *.aux *.log *.nav *.out *.snm *.toc *.vrb *.xdv *.fls *.fdb_latexmk

echo "Built presentation/connections_generator_presentation.pdf"
