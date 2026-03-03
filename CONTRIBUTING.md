# Contributing to Starbelly

Thank you for your interest in contributing to Starbelly! This document provides guidelines and information for contributors.

## Getting Started

Before you begin:

1. Read the [Developer Guide](http://starbelly.readthedocs.io/en/latest/development.html) in our documentation
2. Familiarize yourself with the codebase and architecture
3. Check existing issues and pull requests to avoid duplication

## Development Environment

### Prerequisites

- **Docker** - For running RethinkDB and Nginx containers
- **Poetry** - For Python dependency management
- **Python 3.7+** - Required for the server
- **Chromium or Chrome** - Optional, for web client development
- **Dart SDK 2.7.1** - For web client development

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/HyperionGray/starbelly
   cd starbelly
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Set up the development environment:
   ```bash
   cd dev/
   poetry run python gencert.py localhost
   docker-compose up
   ```

4. Run the server:
   ```bash
   poetry shell
   python tools/container_init.py
   python -m starbelly --log-level debug --reload
   ```

For detailed setup instructions, see the [Developer Guide](http://starbelly.readthedocs.io/en/latest/development.html).

## How to Contribute

### Reporting Bugs

When reporting bugs, please include:

- Starbelly version
- Operating system and version
- Python version
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Any relevant logs or error messages

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:

- Check if the enhancement has already been suggested
- Provide a clear description of the proposed feature
- Explain why this enhancement would be useful
- Include any relevant examples or mockups

### Pull Requests

1. **Fork the repository** and create your branch from `master`
2. **Make your changes**, following the code style guidelines
3. **Add tests** if applicable
4. **Update documentation** if you're changing functionality
5. **Run the test suite**:
   ```bash
   poetry run make test
   ```
6. **Submit a pull request** with a clear description of your changes

### Code Style

- Follow PEP 8 guidelines for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and concise
- Add comments for complex logic

### Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in the present tense (e.g., "Add", "Fix", "Update")
- Reference issue numbers when applicable

## Testing

Run the test suite with:

```bash
poetry run make test
```

For coverage reports:

```bash
poetry run pytest tests/ --cov=starbelly --cov-report=term-missing
```

## Documentation

Documentation is built using Sphinx. To build the documentation:

```bash
poetry run make docs
```

View the built documentation at `docs/_build/html/index.html`.

## Code of Conduct

This project adheres to a code of conduct that promotes a welcoming and inclusive environment. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Questions?

If you have questions about contributing, feel free to:

- Open an issue for discussion
- Contact the maintainers at Hyperion Gray

## License

By contributing to Starbelly, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Starbelly!
