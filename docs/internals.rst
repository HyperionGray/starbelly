Internals
=========

This document describes the crawler's architecture and internal structures.

Service Architecture
--------------------

This diagram shows the components used to deploy Starbelly.

.. graphviz::

    graph system_diagram {
        graph [bgcolor=transparent];
        node [shape=box];
        edge [fontsize=10];

        // Nodes
        app            [label="Starbelly"];
        web            [label="Web server"];
        database       [label="RethinkDB"];
        webclient      [label="Web client"];
        othclient      [label="Other client"];

        // Edges
        web -- app [label="Proxy WebSocket"];
        app -- database;
        webclient -- web [label="Static Assets\n& WebSocket"];
        othclient -- web [label="WebSocket"];
    }

The web server serves static assets (such as the web client's HTML, CSS, and
images) and also proxies the WebSocket API to the crawler. The official
deployment uses Nginx as its web server, but other servers like Apache could
be used instead.

The web client is the standard client for end users to interact with the
crawler. Other clients (e.g. a client you write in Python) connect over the same
WebSocket API as the web client and have access to all of the same
functionality. (See :ref:`api-documentation`.)

The crawler itself is a single Python process that runs crawls jobs and services
WebSocket API requests.

All configuration, metadata, and crawl data `are stored in RethinkDB.
<https://www.rethinkdb.com/>`__.

Asynchronous Framework
----------------------

Starbelly is written in `Python 3 <https://www.python.org/>`__ using the `Trio
framework <https://trio.readthedocs.io/>`__ for most of the asynchronous I/O.
Some parts of the implementation depend on `asyncio libraries
<https://docs.python.org/3/library/asyncio.html>`__, which are invoked using
the `trio-asyncio bridge <https://trio-asyncio.readthedocs.io/>`__:

- The downloader uses ``aiohttp`` and ``aiosocks``, because there is not a
  mature Trio library for HTTP that supports SOCKS proxies.

Crawler Architecture
--------------------

Within the Starbelly server, the implementation is divided into multiple classes
that handle separate concerns. This diagram shows the relationships between
these classes.

.. note::

    Click on a component to jump to that section of the documentation.

.. graphviz::

    digraph system_diagram {
        graph [bgcolor=transparent];
        node [shape=box];
        edge [fontsize=10];

        // Nodes
        api_server;
        crawl_manager [label="CrawlManager"];
        policy_manager [label="PolicyManager",href="#policy"];
        rate_limiter [label="RateLimiter",href="#rate-limiter"];
        downloader [label="Downloader",href="#downloader"];
        extractor [label="Extractor",href="#extractor"];
        resource_monitor;
        scheduler [label="Scheduler",href="#scheduler"];

        // Edges
        api_server -> crawl_manager [label="Manage Crawls"];
        api_server -> scheduler [label="Configure"];
        resource_monitor -> api_server [label="Usage Stats"];
        scheduler -> crawl_manager [label="Start Crawls"];
        crawl_manager -> rate_limiter [label="DownloadRequest"];
        crawl_manager -> policy_manager;
        rate_limiter -> downloader [label="DownloadRequest"];
        downloader -> extractor [label="ExtractItem"];
        downloader -> policy_manager;
        extractor -> crawl_manager [label="URLs"];
    }

Each of these classes is documented below.

.. _downloader:

Downloader
----------

The downloader is responsible for fetching resources over the network and
sending them back to the crawl manager.

.. currentmodule:: starbelly.downloader



.. _extractor:

Extractor
---------

.. currentmodule:: starbelly.url_extractor

After a resource is downloaded, the following function is called to extract
URLs from the resource that the crawler can follow.

.. autofunction:: extract_urls


.. _policy:

Policy
------

Policy objects guide the crawler's decision making, i.e. which links to follow,
which resources to download, when to use a proxy, etc. The policy manager is
responsible for saving and loading policies from the database.

A policy object is a container that includes many various subpolicies.

.. currentmodule:: starbelly.policy

.. autoclass:: Policy
    :members:

.. autoclass:: PolicyAuthentication
    :members:

.. autoclass:: PolicyLimits
    :members:

.. autoclass:: PolicyMimeTypeRules
    :members:

.. autoclass:: PolicyProxyRules
    :members:

.. autoclass:: PolicyRobotsTxt
    :members:

.. autoclass:: PolicyValidationError

.. autoclass:: PolicyUrlNormalization
    :members:

.. autoclass:: PolicyUrlRules
    :members:

.. autoclass:: PolicyUserAgents
    :members:

.. _rate-limiter:

Rate Limiter
------------

The rate limiter ensures that multiple requests to the same domain are not sent
too quickly. The rate limiter acts a bottle neck between the crawl manager and
the downloader. The crawl manager sends items to the rate limiter, and the
rate limiter forwards those items to the downloader when the appropriate amount
of time has passed.

.. currentmodule:: starbelly.rate_limiter


.. autoclass:: RateLimiter
    :members:

The rate limiter uses the following class to store expiry information.

.. autoclass:: Expiry
    :members:

.. _scheduler:

Scheduler
---------

The scheduler is responsible for ensuring that scheduled jobs run at appropriate
times.

.. currentmodule:: starbelly.schedule

.. autoclass:: Scheduler
    :members:

The following model classes are used by the Scheduler.

.. autoclass:: Schedule
    :members:

.. autoclass:: ScheduleEvent
    :members:

.. autoclass:: ScheduleNotification
    :members:

.. autoclass:: ScheduleValidationError
