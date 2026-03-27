# Starbelly

Starbelly is a user-friendly web crawler that is easy to deploy and configure.

For local development setup, see [QUICKSTART.md](QUICKSTART.md).

[![Build Status](https://img.shields.io/travis/com/HyperionGray/starbelly.svg?style=flat-square)](https://travis-ci.org/HyperionGray/starbelly)
[![Coverage](https://img.shields.io/coveralls/github/HyperionGray/starbelly.svg?style=flat-square)](https://coveralls.io/github/HyperionGray/starbelly)
[![Read the Docs](https://img.shields.io/readthedocs/starbelly.svg)](https://starbelly.readthedocs.io)

## Features

- **User-Friendly Interface**: Intuitive web-based dashboard for managing crawls
- **Policy-Based Crawling**: Configure crawling behavior with flexible policies
- **Real-Time Monitoring**: Track crawl progress and results in real-time
- **Scalable Architecture**: Built with modern async Python (Trio) for high performance
- **WebSocket API**: Stream crawl data to your applications
- **RethinkDB Integration**: Efficient storage and querying of crawl data
- **Docker Support**: Easy deployment with Docker Compose

## Installation

Starbelly is deployed using Docker and Docker Compose. 

### Prerequisites

- Docker
- Docker Compose

### Quick Start

1. Download and extract the [Starbelly Docker configuration](https://github.com/HyperionGray/starbelly-docker/archive/master.zip)
2. Navigate to the `starbelly-docker/starbelly` directory
3. Run: `docker-compose up -d`
4. Open your browser to `https://localhost`
5. Login with username `admin` and password `admin`

For detailed installation instructions, security configuration, and TLS certificate setup, see the [Installation Guide](http://starbelly.readthedocs.io/en/latest/installation.html).

## Usage

### Starting Your First Crawl

1. Log into the Starbelly dashboard
2. Create a new crawl policy defining your crawling rules
3. Start a new crawl with a seed URL
4. Monitor progress in real-time through the dashboard

For a detailed walkthrough, see the [First Crawl Guide](http://starbelly.readthedocs.io/en/latest/first_crawl.html).

### API Usage

Starbelly provides a WebSocket API for programmatic access. See the [WebSocket API Documentation](http://starbelly.readthedocs.io/en/latest/websocket_api.html) for details.

Python client library: [starbelly-python-client](https://github.com/hyperiongray/starbelly-python-client)

## Documentation

Complete documentation is available at [starbelly.readthedocs.io](http://starbelly.readthedocs.io/en/latest/).

Key documentation sections:
- [Installation Guide](http://starbelly.readthedocs.io/en/latest/installation.html)
- [Configuration](http://starbelly.readthedocs.io/en/latest/configuration.html)
- [WebSocket API](http://starbelly.readthedocs.io/en/latest/websocket_api.html)
- [Developer Guide](http://starbelly.readthedocs.io/en/latest/development.html)
- [Policy System](http://starbelly.readthedocs.io/en/latest/policy.html)

## Examples

Example code and Jupyter notebooks are available in the [examples](examples/) and [notebooks](notebooks/) directories.

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on how to get started.

### Development Setup

See the [Developer Guide](http://starbelly.readthedocs.io/en/latest/development.html) for instructions on setting up a development environment.

## License

Starbelly is under a proprietary license. Please contact Hyperion Gray at acaceres@hyperiongray.com for licensing information.

## Support

For questions or support, please contact Hyperion Gray at acaceres@hyperiongray.com.

---

<a href="https://www.hyperiongray.com/?pk_campaign=github&pk_kwd=starbelly"><img alt="define hyperion gray" width="500px" src="https://hyperiongray.s3.amazonaws.com/define-hg.svg"></a>
