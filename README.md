# Pykara Templater

**Pykara** is a karaoke templating framework written in Python, inspired by
the legacy Karaoke Templater from Aegisub.

## Requirements

- Python 3.14 or higher

## Installation

```sh
pip install pykara
```

## Usage

```sh
pykara input.ass output.ass
pykara input.ass output.ass --json output.json   # Export intermediate data
pykara input.ass output.ass --warn-only          # Downgrade errors to warnings
pykara input.ass output.ass --seed 42            # Initial deterministic RNG seed
pykara input.ass output.ass --font-dir ./fonts   # Prefer fonts from a directory
pykara input.ass output.ass --generated-only     # Write only generated fx lines
```

See the [documentation](docs/index.md) for the full reference.

## Development

Create and activate a virtual environment:

```sh
python -m venv .venv
source .venv/bin/activate
```

Install development dependencies:

```sh
pip install -e ".[dev]"
```

### Code Quality & Testing

```sh
mdformat --check .                 # Validate Markdown formatting
ruff check pykara tests            # Run lint rules
ruff format --check pykara tests   # Verify Python formatting
pyright                            # Run static type checking
pytest --cov                       # Run test suite with coverage
```

## License

Distributed under the MIT License.
