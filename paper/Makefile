# Builds the paper from the TeX distribution inside WSL.
#
#     cd paper && make
#
# IEEEtran is vendored beside this file rather than installed. The
# distribution here does not ship it, and vendoring means a fresh clone builds
# with no setup, which is the same reason the sibling project vendors the ACM
# class. Both files came from CTAN and their checksums are recorded in
# STATUS.md.

PAPER = paper
GENERATED = generated/suite.tex generated/safety.tex generated/facts.tex
RESULTS = ../results/suite_bounds.json ../results/safety_price.json
# The tool runs on the project's Windows interpreter. WSL executes Windows
# binaries directly, so the build does not need a second environment.
PYTHON = ../.venv/Scripts/python.exe

.PHONY: all clean check tables

all: $(PAPER).pdf

# Regenerated whenever a results file is newer, so a paper cannot be built
# from a table that is older than the numbers it claims to report.
tables: $(GENERATED)

$(GENERATED): ../tools/build_paper_tables.py $(RESULTS)
	$(PYTHON) ../tools/build_paper_tables.py

$(PAPER).pdf: $(PAPER).tex references.bib IEEEtran.cls IEEEtran.bst $(GENERATED)
	latexmk -pdf -halt-on-error -interaction=nonstopmode $(PAPER).tex

# Fails loudly on the two things that pass silently and matter: an undefined
# reference, and a font the publisher will refuse. IEEE rejects Type 3 fonts,
# and matplotlib writes them into a PDF unless told otherwise.
check: $(PAPER).pdf
	@echo '--- undefined references and citations:'
# Matched narrowly. A bare search for "undefined" also catches
# "Font shape ... undefined", which is a benign substitution, and a check that
# fails on something harmless gets ignored and then misses the real thing.
	@! grep -nE "Warning: (Reference|Citation) .*undefined" $(PAPER).log \
	  || (echo 'UNDEFINED REFERENCES OR CITATIONS'; exit 1)
	@! grep -n 'There were undefined references' $(PAPER).log \
	  || (echo 'UNDEFINED REFERENCES OR CITATIONS'; exit 1)
	@echo '  none'
# Warnings only. The log also carries "LaTeX Font Info" lines for the routine
# bold-extended to bold substitution in Times, which are not worth counting
# and which swamp the handful that are.
	@echo '--- font warnings (not errors, but worth reading):'
	@grep -c 'LaTeX Font Warning' $(PAPER).log || true
# A table wider than its column runs into the margin and the build still
# succeeds. In a two-column layout that is easy to miss on screen and
# impossible to miss in print.
	@echo '--- overfull boxes:'
	@grep -c 'Overfull' $(PAPER).log || true
	@grep -n 'Overfull \\hbox' $(PAPER).log | head -5 || true
	@echo '--- fonts:'
	@pdffonts $(PAPER).pdf
	@! pdffonts $(PAPER).pdf | grep -q 'Type 3' || (echo 'TYPE 3 FONT PRESENT'; exit 1)
	@echo '--- pages:'
	@pdfinfo $(PAPER).pdf | grep Pages

clean:
	latexmk -C $(PAPER).tex
	rm -f $(PAPER).bbl
