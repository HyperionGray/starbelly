# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Updated deprecated `trio.hazmat` references to `trio.lowlevel` across server, subscription, and test modules
- Replaced deprecated `trio.run_sync_in_worker_thread` with `trio.to_thread.run_sync` in extractor, storage, and login modules
- Replaced removed `trio.MultiError.catch` with `strict_exception_groups=False` nursery parameter in job runner
- Fixed `DownloadResponse.is_success` to accept all 2xx status codes instead of only 200
- Added missing `read_sitemaps` and `obey_crawl_delay` fields to `PolicyRobotsTxt` protobuf schema
- Regenerated `starbelly_pb2.py` from updated proto definition

### Added
- Added comprehensive documentation files (CONTRIBUTING.md, CHANGELOG.md, CODE_OF_CONDUCT.md, SECURITY.md)

### Changed
- Enhanced README.md with additional sections

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
