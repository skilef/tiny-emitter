# Tiny emitter
![example workflow](https://github.com/skilef/tiny-emitter/actions/workflows/python-package.yml/badge.svg)

A lightweight event emitter for Python.

## Setup
```shell
pip install tiny_emitter
```

## Build and deploy
```shell
python -m pip install --upgrade build twine
python -m build
python -m twine upload --repository testpypi dist/*
```

## Running tests
```shell
pytest
```

## TODO

- [ ] Write unit tests