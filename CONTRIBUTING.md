# Contributing to Starbelly

Thank you for your interest in contributing to Starbelly! This document provides guidelines for contributing to the project.

## Developer Guide

For detailed information about setting up your development environment, please see the [Developer Guide](http://starbelly.readthedocs.io/en/latest/development.html) in our documentation.

## Getting Started

### Prerequisites

* Docker
* Poetry
* Python 3.7+
* Chromium or Chrome (for web client development)
* Dart SDK 2.7.1 (for web client development)

### Setting Up Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/hyperiongray/starbelly
   cd starbelly
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Create a self-signed certificate:
   ```bash
   cd dev/
   poetry run python gencert.py localhost
   ```

4. Run Docker containers:
   ```bash
   docker-compose up
   ```

5. Initialize the database:
   ```bash
   python tools/container_init.py
   ```

6. Start the application server:
   ```bash
   python -m starbelly --log-level debug --reload
   ```

## Development Workflow

### Running Tests

```bash
poetry run make test
```

### Building Documentation

```bash
poetry run make docs
```

Documentation is built using Sphinx and stored in the `docs/` directory.

## Coding Standards

* Follow PEP 8 style guidelines for Python code
* Write clear, descriptive commit messages
* Add tests for new features
* Update documentation when making changes

## Technologies Used

* **Backend**: Python 3, Trio, WebSockets, RethinkDB
* **Frontend**: Dart, Angular
* **Containerization**: Docker, Docker Compose
* **Documentation**: Sphinx, RestructuredText

## Pull Request Process

1. Create a feature branch from `master`
2. Make your changes
3. Ensure tests pass
4. Update documentation as needed
5. Submit a pull request with a clear description of changes

## Questions?

For more information, visit [starbelly.readthedocs.io](http://starbelly.readthedocs.io/en/latest/).

## License

Starbelly is under a proprietary license. By contributing to Starbelly, you agree that your contributions will be subject to the same proprietary license. Please contact Hyperion Gray at acaceres@hyperiongray.com for licensing information.
