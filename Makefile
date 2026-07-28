.PHONY: venv install-deps install-hooks setup lint format check clean

# Create virtual environment if it does not exist
venv:
	@if [ ! -d ".venv" ]; then uv venv; fi

# Install project and dev dependencies into project-level .venv
install-deps: venv
	uv pip install --python .venv -e ".[dev]"

# Install git pre-commit hooks
install-hooks: install-deps
	.venv/bin/pre-commit install

# One-command project setup for developers
setup: install-hooks
	@echo "Project environment and pre-commit hooks successfully set up!"

# Run linting across project
lint:
	.venv/bin/ruff check .

# Run formatting across project
format:
	.venv/bin/ruff format .

# Run pre-commit checks on all files
check:
	.venv/bin/pre-commit run --all-files

# Clean up bytecode cache directories and temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.py[co]" -delete
	@echo "Cleaned up all __pycache__ directories and bytecode files."
