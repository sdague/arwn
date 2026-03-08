# Python Packaging Modernization

This project has been updated to use modern Python packaging standards (PEP 517, PEP 518, PEP 621).

## What Changed

### New Files
- **pyproject.toml**: Main configuration file containing all project metadata, dependencies, and tool configurations
- **PACKAGING.md**: This documentation file

### Updated Files
- **setup.py**: Reduced to a minimal shim for backward compatibility
- **setup.cfg**: Simplified to contain only tool-specific configurations (flake8, pytest, bdist_wheel)
- **requirements_dev.txt**: Updated with modern versions and references to pyproject.toml
- **test-requirements.txt**: Updated with modern versions and references to pyproject.toml

## Key Improvements

1. **PEP 621 Metadata**: All project metadata is now in `pyproject.toml` using the standard format
2. **Modern Build System**: Uses `setuptools>=61.0` with declarative configuration
3. **SPDX License**: Uses modern SPDX license identifier (Apache-2.0)
4. **Updated Python Versions**: Supports Python 3.8 through 3.12
5. **Optional Dependencies**: Dev and docs dependencies are now optional extras
6. **Entry Points**: Console scripts defined in pyproject.toml
7. **Tool Configuration**: Black, isort, mypy, pytest, and coverage configured in pyproject.toml

## Installation

### For Users
```bash
pip install arwn
```

### For Development
```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Or install with all optional dependencies
pip install -e ".[dev,docs]"
```

### For Testing
```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Building

```bash
# Install build tool
pip install build

# Build source distribution and wheel
python -m build
```

## Publishing

```bash
# Install twine
pip install twine

# Upload to PyPI
twine upload dist/*
```

## Backward Compatibility

- `setup.py` is retained as a minimal shim for tools that still require it
- `setup.cfg` contains legacy tool configurations
- `requirements_dev.txt` and `test-requirements.txt` are kept for backward compatibility
- All functionality is preserved

## Migration Notes

If you're maintaining this project:

1. Version bumps should be done in `pyproject.toml` (the `version` field)
2. Dependencies should be added to `pyproject.toml` under `dependencies` or `optional-dependencies`
3. Tool configurations should be added to `pyproject.toml` under the appropriate `[tool.*]` section
4. The old `setup.py` and `setup.cfg` files can eventually be removed once all tools support pyproject.toml

## References

- [PEP 517 - A build-system independent format for source trees](https://peps.python.org/pep-0517/)
- [PEP 518 - Specifying Minimum Build System Requirements](https://peps.python.org/pep-0518/)
- [PEP 621 - Storing project metadata in pyproject.toml](https://peps.python.org/pep-0621/)
- [Setuptools Quickstart](https://setuptools.pypa.io/en/latest/userguide/quickstart.html)
- [Python Packaging User Guide](https://packaging.python.org/)