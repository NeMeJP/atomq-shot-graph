# Makefile for atomq-shot-graph. Thin wrapper over run.sh for Make users.

.PHONY: all install demo test viz lint typecheck clean help

help:
	@echo "atomq-shot-graph — available targets:"
	@echo "  make install    — create venv + install deps"
	@echo "  make demo       — install + run the demo script"
	@echo "  make test       — install + run pytest suite"
	@echo "  make viz        — install + regenerate docs/images/*.png"
	@echo "  make lint       — ruff check"
	@echo "  make typecheck  — mypy --strict"
	@echo "  make clean      — remove .venv and caches"
	@echo "  make all        — install + test + demo + viz  (one-click)"

install:
	@./run.sh demo >/dev/null 2>&1 || true
	@./run.sh test >/dev/null 2>&1 || true

demo:
	@./run.sh demo

test:
	@./run.sh test

viz:
	@./run.sh viz

lint:
	@.venv/bin/ruff check src/ tests/ examples/

typecheck:
	@.venv/bin/mypy src/yaqumo_shot_graph/

clean:
	@./run.sh clean

all:
	@./run.sh all
