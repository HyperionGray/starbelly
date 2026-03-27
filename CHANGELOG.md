# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Added comprehensive documentation files (CONTRIBUTING.md, CHANGELOG.md, CODE_OF_CONDUCT.md, SECURITY.md)
- Added explicit API error handling for unsubscribe requests that reference
  unknown subscription IDs.

### Changed
- Enhanced README.md with additional sections
- Cleaned up integration subscription tests by removing the TODO marker and
  fixing fixture teardown to use valid database connections.
- Removed stale repository artifacts (`bfg-1.15.0.jar`,
  `.github/copilot-instructions.md~`, obsolete streaming implementation notes,
  and placeholder streaming examples).

## [2.0.0-dev]

### Changed
- Massive rewrite of Starbelly's I/O to use Trio instead of asyncio
- Upgraded web client to Dart 2 and Angular 5

### Added
- New asynchronous I/O model using Trio
- Modern web client framework

## [1.0.0] - 2017-11-03

### Added
- Initial release of Starbelly
- Web crawler with graphical user interface
- Policy-based crawling system
- RethinkDB integration
- WebSocket API
- Docker deployment support

[Unreleased]: https://github.com/HyperionGray/starbelly/compare/v1.0.0...HEAD
[2.0.0-dev]: https://github.com/HyperionGray/starbelly/compare/v1.0.0...v2.0.0-dev
[1.0.0]: https://github.com/HyperionGray/starbelly/releases/tag/v1.0.0
