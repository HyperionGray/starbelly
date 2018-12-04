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
        app            [label="Crawler"];
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
        downloader;
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

.. _rate-limiter:

Rate Limiter
------------

.. currentmodule:: starbelly.rate_limiter

The rate limiting logic is implemented in the following class.

.. autoclass:: RateLimiter
    :members:

The rate limiter uses the following class to store expiry information.

.. autoclass:: Expiry
    :members:

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

.. _scheduler:

Scheduler
---------


Crawls may be scheduled to run automatically at specified periods. The Scheduler
is the main class for implementing this logic.

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
