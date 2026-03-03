# START HERE: Starbelly Web Crawler

## What is this repository?

Starbelly is a **user-friendly web crawler** with a graphical user interface designed for ease of deployment and configuration. Unlike other crawling systems like Nutch or Scrapy that require complex configuration files and custom code, Starbelly provides a GUI-based approach to web crawling that makes it accessible to users who need powerful crawling capabilities without diving deep into code.

This is the **server component** - a Python-based backend that does the actual crawling, manages jobs, handles scheduling, and provides a WebSocket API for clients to interact with the crawler.

## Why is this being built? Why is it useful?

### The Problem It Solves

Traditional web crawlers are powerful but difficult to use:
- They require extensive programming knowledge
- Configuration is complex and error-prone  
- Managing and monitoring crawls is cumbersome
- Deploying them requires significant DevOps expertise

### Starbelly's Solution

Starbelly trades off some scalability for **massive improvements in usability**:
- **No code required**: Configure everything through a GUI
- **Real-time monitoring**: See crawl progress live
- **Easy deployment**: Docker-based deployment with minimal setup
- **Flexible**: Comprehensive policy system for fine-grained control
- **Extensible**: Clean API allows building custom systems on top

### Real-World Use Cases

- **Custom search engines**: Plug in Elasticsearch backend to index crawled content
- **Data collection pipelines**: Extract structured data from websites at scale
- **Website monitoring**: Track changes to competitor sites or your own content
- **Research**: Academic or business intelligence gathering from the web
- **Archive building**: Create snapshots of website content over time

## Who is this for?

### Primary Users

1. **Data Scientists & Researchers**: Need to collect web data without becoming crawling experts
2. **Small Teams**: Don't have resources for complex crawling infrastructure
3. **Developers Building on Top**: Want a reliable crawling backend to integrate with their systems
4. **Digital Agencies**: Need to monitor or analyze web content for clients

### Skill Level

- **End Users**: No programming required - use the GUI
- **Integrators**: Basic API knowledge to connect to the WebSocket API  
- **Contributors**: Python developers familiar with async programming

## Repository Deep Dive

### Core Architecture

Starbelly is built on a **streaming, concurrent architecture** using modern Python async frameworks.

#### Technology Stack

- **Language**: Python 3.7+
- **Async Framework**: Trio (with trio-asyncio bridge for some components)
- **Database**: RethinkDB (for configuration, metadata, and crawl data)
- **API**: WebSocket-based with Protocol Buffers (protobuf) serialization
- **HTTP Client**: aiohttp (for actual web crawling)
- **Dependency Management**: Poetry

#### Key Components

The system is organized as a **pipeline architecture** where each crawl job has its own set of components working concurrently:

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│  Frontier   │────▶│ Rate Limiter │────▶│ Downloader │
│             │     │   (Shared)   │     │            │
└─────────────┘     └──────────────┘     └────────────┘
       ▲                                        │
       │                                        ▼
       │                                 ┌────────────┐
       │                                 │  Storage   │
       │                                 └────────────┘
       │                                        │
       │                                        ▼
       │                                 ┌────────────┐
       └─────────────────────────────────│ Extractor  │
                                         └────────────┘
```

**Frontier** (`starbelly/frontier.py`):
- Manages the queue of URLs to be crawled
- Prioritizes URLs based on "cost" (lower cost = higher priority)
- Handles domain authentication if required
- Stores pending URLs in RethinkDB

**Rate Limiter** (`starbelly/rate_limiter.py`):
- **Shared across all jobs** - critical for preventing site overload
- Enforces delays between requests to same domain
- Uses token-based system to track domain access
- Prevents multiple concurrent jobs from overwhelming sites

**Downloader** (`starbelly/downloader.py`):
- Fetches resources over HTTP/HTTPS
- Supports SOCKS and HTTP proxies
- Enforces MIME type policies
- Handles authentication, redirects, errors
- Uses aiohttp with asyncio bridge

**Storage** (`starbelly/storage.py`):
- Saves downloaded content to RethinkDB
- Stores metadata (headers, timestamps, status codes)
- Handles compression and deduplication

**Extractor** (`starbelly/extractor.py`):
- Parses HTML/XML to find new URLs
- Applies URL rules from policy
- Normalizes URLs according to policy
- Detects forms and handles form submission
- Integrates with sitemap parsing

#### Policy System

The **Policy** (`starbelly/policy.py`) is the brain of the crawler - it makes all decisions:

- **URL Rules**: Regex patterns to include/exclude URLs
- **MIME Type Rules**: Which content types to download
- **Robots.txt**: How to handle robots.txt (obey, ignore, etc.)
- **Proxy Rules**: When to use proxies and which ones
- **Rate Limits**: Max requests per domain, per second
- **Authentication**: Login credentials for protected sites
- **CAPTCHA**: Integration with third-party CAPTCHA solvers
- **Limits**: Max items, max duration, max cost

Policies are **stored as protobuf messages** and converted to/from database documents. This makes them portable and versionable.

#### Job Management

**CrawlManager** (`starbelly/job.py`):
- Supervises all running crawl jobs
- Starts/stops/pauses/resumes jobs
- Tracks statistics and resource usage
- Enforces job limits

**CrawlJob** (`starbelly/job.py`):
- One instance per active crawl
- Spawns and supervises all pipeline components
- Manages job lifecycle
- Reports status to manager

**Scheduler** (`starbelly/schedule.py`):
- Automatically starts jobs based on schedules
- Supports cron-like scheduling
- Can run jobs periodically or one-time

#### WebSocket API

**Server** (`starbelly/server/`):
- WebSocket-based API (not REST)
- Uses Protocol Buffers for serialization (efficient binary format)
- Request/Response model for commands
- Subscription/Event model for streaming updates

API Handlers are decorated with `@api_handler`:
```python
@api_handler
async def start_crawl(request, crawl_manager, db):
    # Handle start crawl command
    pass
```

Subscriptions allow clients to receive **real-time updates**:
- `JobStatusSubscription`: Live crawl statistics
- `JobSyncSubscription`: Stream crawl results
- `ResourceMonitorSubscription`: System resource usage

#### Database Layer

**RethinkDB Integration** (`starbelly/db.py`):
- NoSQL database optimized for real-time applications
- **Changefeeds**: Database-level streaming of data changes
- Tables: `policy`, `schedule`, `job`, `response`, `frontier`, etc.
- Connection pooling for performance

Why RethinkDB?
- Native support for changefeeds (perfect for real-time updates)
- Flexible schema (crawl data is heterogeneous)
- Good query language
- Built-in clustering (though Starbelly is single-instance currently)

### Unique Aspects of This Codebase

1. **Trio-based**: Uses Trio instead of asyncio for most async code. Trio has better structured concurrency and cancellation semantics. However, some libraries (aiohttp) require asyncio, so there's a bridge (`trio_asyncio`).

2. **Protobuf everywhere**: API messages are protobuf, not JSON. This is more efficient but requires schema management and code generation. The schema is in a separate repo: `starbelly-protobuf`.

3. **Pipeline architecture**: Each job has completely isolated components. They communicate via Trio channels (in-memory queues). The rate limiter is the only shared component.

4. **Policy-driven**: Almost every decision is controlled by policy, making the crawler extremely flexible without code changes.

5. **Streaming API**: Uses WebSocket subscriptions instead of polling. Clients get real-time updates via database changefeeds.

6. **Auto-login**: Uses Formasaurus (ML-based form detection) to automatically log into sites. This is quite sophisticated and unique.

7. **Watchdog mode**: Development mode with auto-reload when code changes (see `__main__.py`).

### How It Works Technically

#### Starting a Crawl

1. Client sends `RequestStartJob` protobuf message via WebSocket
2. API handler (`starbelly/server/job.py`) receives it
3. CrawlManager creates a new CrawlJob instance
4. CrawlJob:
   - Loads policy from database
   - Creates frontier, downloader, extractor, storage components
   - Spawns Trio nursery (task group) for all components
   - Inserts seed URLs into frontier
5. Components start running concurrently:
   - Frontier sends URLs to rate limiter
   - Rate limiter delays and forwards to downloader
   - Downloader fetches and sends to storage
   - Storage saves and sends to extractor
   - Extractor finds new URLs and adds to frontier
   - Loop continues until frontier is exhausted or limits reached

#### Trio Structured Concurrency

Trio uses "nurseries" (task groups with guaranteed cleanup):
```python
async with trio.open_nursery() as nursery:
    nursery.start_soon(frontier.run)
    nursery.start_soon(downloader.run)
    nursery.start_soon(extractor.run)
    nursery.start_soon(storage.run)
# When nursery exits, all tasks are guaranteed to be done
```

If any component raises an exception, Trio **automatically cancels all other tasks** in the nursery and propagates the exception. This prevents resource leaks.

#### Channels for Communication

Components communicate via Trio memory channels:
```python
send_channel, receive_channel = trio.open_memory_channel(100)

# Producer
await send_channel.send(item)

# Consumer  
item = await receive_channel.receive()
```

Channels provide **backpressure** - if consumer is slow, producer blocks. This prevents memory exhaustion.

#### Protobuf Workflow

1. Define messages in `.proto` file (in separate repo)
2. Compile: `protoc --python_out=. starbelly.proto`
3. Generated code: `starbelly_pb2.py` (checked into this repo)
4. Use in code:
   ```python
   from starbelly_pb2 import Request
   request = Request()
   request.request_id = 1
   request.start_job.CopyFrom(...)
   data = request.SerializeToString()
   ```

### Important Files and Directories

#### Core Crawler Components
- `starbelly/job.py` - Job management, crawl lifecycle (600+ lines)
- `starbelly/frontier.py` - URL queue management (400+ lines)
- `starbelly/downloader.py` - HTTP fetching (500+ lines)
- `starbelly/extractor.py` - URL extraction and parsing (500+ lines)
- `starbelly/storage.py` - Database persistence (300+ lines)
- `starbelly/rate_limiter.py` - Request throttling (300+ lines)

#### Policy and Configuration
- `starbelly/policy.py` - Policy logic (1000+ lines - this is complex!)
- `starbelly/robots.py` - Robots.txt handling (300+ lines)
- `starbelly/config.py` - Configuration management
- `starbelly/login.py` - Auto-login with Formasaurus (400+ lines)
- `starbelly/captcha.py` - CAPTCHA solver integration

#### API and Server
- `starbelly/server/` - WebSocket API handlers
  - `job.py` - Job API (start, stop, pause, resume)
  - `policy.py` - Policy CRUD
  - `schedule.py` - Schedule CRUD
  - `subscription.py` - Subscription management
  - `system.py` - System commands (clear DB, etc.)

#### Database
- `starbelly/db.py` - Database layer with RethinkDB (800+ lines)
- `starbelly/subscription.py` - Subscription implementations (600+ lines)

#### Entry Points and Bootstrap
- `starbelly/__main__.py` - Entry point, argument parsing, watchdog
- `starbelly/bootstrap.py` - Application initialization
- `starbelly/version.py` - Version info

#### Generated and Schemas
- `starbelly/starbelly_pb2.py` - Generated protobuf code (huge, don't edit)

#### Development and Tools
- `tools/container_init.py` - Initialize database tables
- `tools/shell.py` - Interactive IPython shell with DB access
- `dev/` - Docker compose setup for development
- `tests/` - Unit and integration tests

#### Documentation
- `docs/` - Sphinx documentation
  - `internals.rst` - Architecture details
  - `development.rst` - Dev environment setup
  - `websocket_api.rst` - API reference

#### Configuration
- `pyproject.toml` - Poetry dependencies and project metadata
- `.pylintrc` - Linting configuration
- `pytest.ini` - Test configuration

## How to Build On This Project

### Prerequisites for Development

1. **Install dependencies**:
   ```bash
   poetry install
   ```

2. **Start RethinkDB** (in Docker):
   ```bash
   cd dev/
   docker-compose up  # or 'docker compose up' for Docker Compose v2+
   ```

3. **Initialize database**:
   ```bash
   poetry run python tools/container_init.py
   ```

4. **Run the server**:
   ```bash
   poetry run python -m starbelly --log-level debug --reload
   ```

5. **(Optional) Use the shell**:
   ```bash
   poetry run python tools/shell.py
   ```

**Note**: RethinkDB admin interface will be available at http://localhost:8080 once the Docker container is running.

### Easy Tasks (Good First Issues)

These require minimal knowledge of the codebase:

1. **Improve documentation**:
   - Location: `docs/*.rst`
   - Add examples, clarify confusing sections
   - Update screenshots if they're outdated

2. **Add more unit tests**:
   - Location: `tests/`
   - Many components could use more test coverage
   - Look for functions without tests

3. **Add configuration validation**:
   - Location: `starbelly/config.py`
   - Better error messages when config is invalid
   - Document all config options

4. **Improve logging**:
   - Throughout codebase
   - Add more debug-level logs for troubleshooting
   - Make info-level logs more actionable

5. **Add CLI commands**:
   - Location: `starbelly/__main__.py`
   - Add commands like `--version`, `--check-config`
   - Make it easier to operate without API

### Moderate Tasks

These require understanding specific components:

1. **Add URL filtering by content type**:
   - Location: `starbelly/extractor.py`
   - Currently extracts all links; could filter by MIME type
   - Modify `_extract_urls()` method

2. **Improve rate limiter**:
   - Location: `starbelly/rate_limiter.py`
   - Add adaptive rate limiting based on server response
   - Implement "politeness" delays per-site
   - Add burst allowances

3. **Better robots.txt caching**:
   - Location: `starbelly/robots.py`
   - Add expiration based on cache-control headers
   - Implement LRU eviction for memory efficiency

4. **Implement retry logic**:
   - Location: `starbelly/downloader.py`
   - Add exponential backoff for failed requests
   - Make retry policy configurable
   - See `backoff.py` for existing backoff implementation

5. **Add more extraction patterns**:
   - Location: `starbelly/extractor.py`
   - Extract URLs from CSS files
   - Extract from JavaScript (basic pattern matching)
   - Handle meta refresh redirects

6. **Add streaming API for more data types**:
   - Location: `starbelly/subscription.py`, `starbelly/db.py`
   - See `STREAMING_API.md` and `IMPLEMENTATION_SUMMARY.md`
   - Protobuf schema updates needed (separate repo)
   - Currently has policies, schedules, domain_logins
   - Could add: captcha solvers, rate limits, user accounts

### Difficult Tasks

These require deep understanding of the architecture:

1. **Distributed crawling**:
   - **Why difficult**: Requires redesigning single-instance architecture
   - Split components across multiple machines
   - Coordinate via RethinkDB or message queue
   - Handle partial failures gracefully
   - Key files: `starbelly/job.py`, all component files

2. **Incremental crawling**:
   - **Why difficult**: Requires change detection and efficient storage
   - Compare current vs. previous crawl
   - Only download changed pages (use ETags, Last-Modified)
   - Store diffs instead of full copies
   - Key files: `starbelly/downloader.py`, `starbelly/storage.py`

3. **JavaScript rendering**:
   - **Why difficult**: Requires integrating a headless browser
   - Add Playwright or Puppeteer
   - Bridge with trio-asyncio
   - Manage browser lifecycle (memory leaks!)
   - Handle dynamic content, AJAX
   - Key files: `starbelly/downloader.py`, `starbelly/extractor.py`

4. **Better scheduling**:
   - **Why difficult**: Complex state management and timing
   - Add dependency-based scheduling (crawl A before B)
   - Implement job chains and workflows
   - Add SLA tracking and alerts
   - Key files: `starbelly/schedule.py`, `starbelly/job.py`

5. **Deduplication at scale**:
   - **Why difficult**: Performance and memory challenges
   - Current deduplication is basic
   - Implement simhashing or minhashing for near-duplicates
   - Use bloom filters for URL seen checks
   - Optimize database queries
   - Key files: `starbelly/frontier.py`, `starbelly/storage.py`

6. **Plugin system**:
   - **Why difficult**: Requires API design and stability guarantees
   - Allow custom extractors, downloaders, storage backends
   - Define stable plugin API
   - Handle plugin errors without crashing main system
   - Document plugin development
   - Key files: All component files need plugin hooks

7. **GraphQL API**:
   - **Why difficult**: Major API addition alongside WebSocket
   - Add GraphQL server (graphene-python or strawberry)
   - Support subscriptions (for real-time updates)
   - Maintain compatibility with protobuf API
   - Key files: New `starbelly/graphql/` directory

### Known Issues and TODOs

Check these locations for improvement opportunities:

- **TODO comments in code**: `grep -r "TODO" starbelly/`
- **FIXME comments**: `grep -r "FIXME" starbelly/`
- **GitHub Issues**: Check the issue tracker
- **IMPLEMENTATION_SUMMARY.md**: Lists incomplete features

### Testing Your Changes

1. **Run unit tests**:
   ```bash
   poetry run pytest tests/
   ```

2. **Run specific test**:
   ```bash
   poetry run pytest tests/test_downloader.py::test_download_success
   ```

3. **Check coverage**:
   ```bash
   poetry run pytest --cov=starbelly --cov-report=html
   ```

4. **Lint code**:
   ```bash
   poetry run pylint starbelly/
   ```

5. **Manual testing**:
   - Start server with `--reload`
   - Use web client or Python client to test
   - Check RethinkDB GUI (http://localhost:8080)

### Code Style Guidelines

- Follow PEP 8
- Use type hints where reasonable
- Write docstrings for public functions
- Keep functions focused and small
- Prefer async/await over callbacks
- Use Trio patterns (nurseries, channels)
- Add logging at appropriate levels

### Architecture Principles

1. **Structured concurrency**: Use Trio nurseries, never spawn untracked tasks
2. **Fail fast**: Let exceptions propagate, handle them at boundaries
3. **Policy-driven**: Put configuration in Policy, not hardcoded
4. **Database as source of truth**: RethinkDB holds all state
5. **Streaming over polling**: Use changefeeds for real-time updates

### Getting Help

- **Read the docs**: `docs/` directory, especially `internals.rst`
- **Use the shell**: `tools/shell.py` for exploring the database
- **Check examples**: `examples/` and `notebooks/`
- **Read tests**: Tests show how components are used
- **Ask questions**: Open a GitHub discussion or issue

---

## Quick Navigation Reference

**Want to understand how crawling works?**
→ Start with `starbelly/job.py` (CrawlJob class)

**Want to add a new policy rule?**
→ Look at `starbelly/policy.py` (Policy* classes)

**Want to change how URLs are extracted?**
→ Check `starbelly/extractor.py` (CrawlExtractor class)

**Want to add a new API command?**
→ See `starbelly/server/` (any file with @api_handler)

**Want to understand the database schema?**
→ Run `tools/shell.py` and explore: `r.table_list().run(conn)`

**Want to debug a crawl?**
→ Run server with `--log-level debug` and watch the logs

**Want to understand async patterns?**
→ Read Trio docs first: https://trio.readthedocs.io

This project is well-structured but complex. Take time to understand the async patterns (Trio), the protobuf workflow, and the pipeline architecture. Once those click, the rest makes sense. Happy coding!
