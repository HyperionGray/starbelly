# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2019-XX-XX

### Added
- Runtime configuration file overrides via `--config-dir`, `--config-files`,
  `STARBELLY_CONFIG_DIR`, and `STARBELLY_CONFIG_FILES`

### Changed
- Massive rewrite of Starbelly's I/O to use Trio instead of asyncio
- Upgrade web client to Dart 2 and Angular 5

## [1.0.0] - 2017-11-03

### Added
- Initial release of Starbelly web crawler
- User-friendly interface for web crawling
- RethinkDB integration for data storage
- WebSocket API for real-time communication
- Policy-based crawling configuration
- Docker support for easy deployment
