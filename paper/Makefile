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

.PHONY: all clean check

all: $(PAPER).pdf

$(PAPER).pdf: $(PAPER).tex references.bib IEEEtran.cls IEEEtran.bst
	latexmk -pdf -halt-on-error -interaction=nonstopmode $(PAPER).tex

# Fails loudly on the two things that pass silently and matter: an undefined
# reference, and a font the publisher will refuse. IEEE rejects Type 3 fonts,
# and matplotlib writes them into a PDF unless told otherwise.
check: $(PAPER).pdf
	@echo '--- undefined references and citations:'
	@! grep -n 'undefined' $(PAPER).log || (echo 'UNDEFINED REFERENCES'; exit 1)
	@echo '  none'
	@echo '--- fonts:'
	@pdffonts $(PAPER).pdf
	@! pdffonts $(PAPER).pdf | grep -q 'Type 3' || (echo 'TYPE 3 FONT PRESENT'; exit 1)
	@echo '--- pages:'
	@pdfinfo $(PAPER).pdf | grep Pages

clean:
	latexmk -C $(PAPER).tex
	rm -f $(PAPER).bbl
