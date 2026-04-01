# Starbelly

Starbelly is a user-friendly web crawler that is easy to deploy and configure.

[![Build Status](https://img.shields.io/travis/com/HyperionGray/starbelly.svg?style=flat-square)](https://travis-ci.com/HyperionGray/starbelly)
[![Coverage](https://img.shields.io/coveralls/github/HyperionGray/starbelly.svg?style=flat-square)](https://coveralls.io/github/HyperionGray/starbelly)
[![Read the Docs](https://img.shields.io/readthedocs/starbelly.svg)](https://starbelly.readthedocs.io)

## Features

- **Policy-Based Crawling**: Define custom crawl policies to control crawler behavior
- **Graphical User Interface**: Easy-to-use web interface for managing crawls
- **WebSocket API**: Real-time communication and streaming results
- **Docker Deployment**: Simple deployment using Docker containers
- **RethinkDB Backend**: Scalable database for storing crawl data
- **Asynchronous I/O**: Built on Trio for high-performance concurrent crawling

## Installation

Starbelly is deployed using Docker and Docker Compose. See the [Installation Guide](https://starbelly.readthedocs.io/en/latest/installation.html) for detailed instructions.

Quick start:
```bash
git clone https://github.com/hyperiongray/starbelly-docker.git
cd starbelly-docker/starbelly
docker-compose up -d
```

## Usage

After installation, navigate to your server's address in a web browser. The default credentials are:
- **Username**: admin
- **Password**: admin

For detailed usage instructions, see the [documentation](https://starbelly.readthedocs.io/en/latest/first_crawl.html).

## Documentation

Complete documentation is available at [starbelly.readthedocs.io](https://starbelly.readthedocs.io/en/latest/).

## Examples

Example notebooks and scripts are available in the `notebooks` and `examples` directories.

## API

Starbelly provides a WebSocket API for programmatic access. See the [WebSocket API documentation](https://starbelly.readthedocs.io/en/latest/websocket_api.html) for details.

Python client library: [starbelly-python-client](https://github.com/hyperiongray/starbelly-python-client)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Starbelly is under the MIT License. See [LICENSE](LICENSE) for details.

For commercial support or inquiries, please contact Hyperion Gray at acaceres@hyperiongray.com

---

<a href="https://www.hyperiongray.com/?pk_campaign=github&pk_kwd=starbelly"><img alt="define hyperion gray" width="500px" src="https://hyperiongray.s3.amazonaws.com/define-hg.svg"></a>
