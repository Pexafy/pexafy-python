# Contributing

Bug reports and pull requests are welcome.

## Reporting a bug

Open an issue with what you ran, what you expected, and what happened instead.
A minimal reproduction saves a lot of back and forth.

## Pull requests

- Keep the change focused — one concern per PR.
- Add a test if you are fixing a bug or adding behaviour.
- `ruff check .` and `pytest` should pass before you push.

## Development

```bash
git clone https://github.com/Pexafy/pexafy-python.git
cd pexafy-python
pip install -e ".[dev]"
pytest
```
