# Contributing

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

## Types of Contributions

### Report Bugs

Report bugs at https://github.com/sdague/arwn/issues.

Please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug"
is open to whoever wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with "feature"
is open to whoever wants to implement it.

### Write Documentation

ARWN could always use more documentation, whether in docstrings or
in the project files.

### Submit Feedback

The best way to send feedback is to file an issue at https://github.com/sdague/arwn/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions are welcome.

## Get Started

1. Fork the `arwn` repo on GitHub.

2. Clone your fork locally:

   ```bash
   git clone git@github.com:your_name_here/arwn.git
   cd arwn
   ```

3. Create a virtualenv and install in editable mode:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```

4. Create a branch for local development:

   ```bash
   git checkout -b name-of-your-bugfix-or-feature
   ```

5. When you're done making changes, run the linter and tests:

   ```bash
   tox -e lint
   tox -e py314
   ```

6. Commit your changes and push your branch to GitHub:

   ```bash
   git add .
   git commit -m "Description of your changes."
   git push origin name-of-your-bugfix-or-feature
   ```

7. Submit a pull request through the GitHub website.

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, update the documentation.
3. The pull request should pass CI for all supported Python versions (3.10–3.14).

## Releasing

Releases are automated. To cut a release:

1. Update the version in `pyproject.toml`.
2. Move the `[Unreleased]` entries in `CHANGELOG.md` to a new versioned section.
3. Commit and push to `main` — the release workflow handles PyPI publish, git tag, and GitHub release automatically.
