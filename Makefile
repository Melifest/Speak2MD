SHELL := /bin/bash
.PHONY: up down logs fmt test lint

up:
\tdocker compose up --build

down:
\tdocker compose down -v

logs:
\tdocker compose logs -f --tail=200

fmt:
\tpython -m pip install black ruff >/dev/null 2>&1 || true
\truff check backend --fix
\tblack backend

test:
\tpython -m pip install -r backend/requirements.txt >/dev/null 2>&1 || true
\tpytest -q
