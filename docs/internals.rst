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
        apiserver;
        manager;
        rate_limiter [label="RateLimiter",href="#rate-limiter"];
        downloader;
        extractor [label="Extractor",href="#extractor"];
        resource_monitor;
        scheduler;

        // Edges
        apiserver -> manager [dir=both];
        apiserver -> resource_monitor [dir=both];
        apiserver -> scheduler;
        manager -> rate_limiter [label="FrontierItem"];
        rate_limiter -> downloader [label="FrontierItem"];
        downloader -> extractor [label="ExtractItem"];
        extractor -> manager [label="list[URL]"];
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
