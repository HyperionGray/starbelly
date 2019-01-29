Internals
=========

This document describes the crawler's architecture and internal structures.

Service Architecture
--------------------

This diagram shows the components used to deploy Starbelly.

.. graphviz::

    graph service_diagram {
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
- The downloader users ``aiohttp``. It could be ported to ``asks`` but I didn't
  want to mix two different HTTP clients into the same project. When the
  downloader is updated, this can be updated as well.

Crawling Pipeline
-----------------

Starbelly's crawling operations consist of a pipeline of various components. The
*frontier* is a component that keeps track of which URLs remain to be crawled.
These URLs are fed to a *rate limiter* which acts as a bottleneck that prevents
crawling sites too fast. The downloader fetches URLs from the rate limiter and
downloads them over the network. The storage component saves the downloaded
items in the database. The extractor finds URLs in the downloaded items and
sends them back to the frontier so those URLs can be crawled, too.

Each crawl job creates its own crawling components (frontier, downloader,
storage, extractor) and they run concurrently with all other jobs. The rate
limiter is shared across all jobs to ensure that rate limits are enforced
correctly even when two different jobs are crawling the same domain.

.. graphviz::

    digraph crawl_pipeline {
        graph [bgcolor=transparent];
        node [shape=box, style=filled];

        frontier1 [label="Job #1 Frontier", fillcolor="#9ac2f9"]
        downloader1 [label="Downloader", fillcolor="#9ac2f9"]
        extractor1 [label="Extractor", fillcolor="#9ac2f9"]
        storage1 [label="Storage", fillcolor="#9ac2f9"]

        frontier2 [label="Job #2 Frontier", fillcolor="#9af9ad"];
        downloader2 [label="Downloader", fillcolor="#9af9ad"];
        extractor2 [label="Extractor", fillcolor="#9af9ad"];
        storage2 [label="Storage", fillcolor="#9af9ad"];

        rate_limiter [label="Rate Limiter", fillcolor=grey];

        frontier1 -> rate_limiter -> downloader1 -> storage1 -> extractor1;
        frontier2 -> rate_limiter -> downloader2 -> storage2 -> extractor2;
        frontier1 -> extractor1 [dir=back, style=dashed];
        frontier2 -> extractor2 [dir=back, style=dashed];
    }

This diagram depicts the crawling pipeline for two concurrent jobs: Job #1 in
blue and Job #2 in green.

System Components
-----------------

Starbelly doesn't just contain crawling components: it also contains components
that provide management and introspection for the crawling system. This section
briefly explains each high-level component, and the subsequent sections provide
low-level details for each component.

:ref:`api_server`
    The API server allows clients to interact with Starbelly by
    sending protobuf messages over a WebSocket connection. The server uses a
    simple request/response model for most API calls, and also has a
    subscription/event model when the client wants push updates.

:ref:`captcha`
    Components that deal with CAPTCHA images.

Crawl Manager
    TODO

:ref:`downloader`
    Responsible for fetching items from the network. Although
    this is a seemingly simple responsibility, the downloader is responsible for
    significant portions of the crawling policy, such as enforcing proxy policy
    and MIME type rules.

:ref:`extractor`
    Parses response bodies to discover new URLs that may be
    added to the crawl frontier.

:ref:`login-manager`
    Automates the process of logging in to a site to perform an authenticated
    crawl.

:ref:`policy`
    Controls the crawler's decision making, for example how to handle
    robots.txt exclusion rules, how to prioritize URLs, how long to run the
    crawl, etc.

:ref:`rate-limiter`
    Acts a bottleneck between the jobs' crawl
    frontiers and the jobs' downloaders. It prevents sites from being crawled
    too quickly, even when multiple jobs are crawling the same domain.

:ref:`resource_monitor`
    Provides introspection into other
    components to track things like how many items are currently being download,
    how many items are queued in the rate limiter, etc.

:ref:`robots_txt`
    Responsible for fetching robots.txt files as necessary,
    maintaining a local cache of robots.txt files, and making access control
    decisions, such as, "is job X allowed to access URL Y?"

:ref:`scheduler`
    Controls the crawling schedule. When a job needs
    to run, the scheduler will automatically start it.

.. _api_server:

API Server
----------

The main interaction point for Starbelly is through its WebSocket API.

TODO

.. currentmodule:: starbelly.subscription

The API supports multiple types of subscriptions. Unlike the rest of the API,
which consists of a simple request → response model, subscriptions push data to
the client. Some subscriptions can be paused and resumed using a "sync token".

.. autoclass:: SyncTokenError
    :members:

.. autoclass:: SyncTokenInt
    :members:

The following classes implement subscription behavior.

.. autoclass:: CrawlSyncSubscription
    :members:

.. autoclass:: JobStatusSubscription
    :members:

.. autoclass:: ResourceMonitorSubscription
    :members:

.. autoclass:: TaskMonitorSubscription
    :members:

.. _captcha:

CAPTCHA
-------

Starbelly supports passing CAPTCHA images to third-party solving services.

.. currentmodule:: starbelly.captcha

.. autoclass:: CaptchaSolver
    :members:

.. autofunction:: captcha_doc_to_pb

.. autofunction:: captcha_pb_to_doc

.. _downloader:

Downloader
----------

The downloader is responsible for fetching resources over the network and
sending them back to the crawl manager.

.. currentmodule:: starbelly.downloader

.. autoclass:: DownloadRequest
    :members:

.. autoclass:: DownloadResponse
    :members:

.. autoclass:: Downloader
    :members:

.. autoclass:: MimeNotAllowedError

.. _extractor:

Extractor
---------

.. currentmodule:: starbelly.url_extractor

After a resource is downloaded, the following function is called to extract
URLs from the resource that the crawler can follow.

.. autofunction:: extract_urls

.. _login-manager:

Login Manager
-------------

The login manager uses the `Formasaurus
<https://github.com/TeamHG-Memex/Formasaurus/>`__ library to find a login form
on a page, fill it out, and submit it to get session cookies for authenticated
crawling. Under the hood, Formasaurus uses a pre-built machine learning model (a
conditional random field) to classify types of forms on a page and to classify
the types of inputs in each form. If necessary, the login manager will also
request a CAPTCHA solution from a CAPTCHA solver.

.. currentmodule:: starbelly.login

.. autofunction:: get_login_form

.. autofunction:: solve_captcha_asyncio

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

The following functions are used to determine the token to be used for a
request.

.. autofunction:: get_domain_token

.. _resource_monitor:

Resource Monitor
----------------

.. currentmodule:: starbelly.resource_monitor

The resource monitor introspects various objects in the crawling pipe in order
to keep track of consumption and usage of various resources, such as where items
are in the crawling pipeline, CPU utilization, memory usage, etc.

.. autoclass:: ResourceMonitor
    :members:

.. _robots_txt:

Robots.txt Manager
------------------

.. currentmodule:: starbelly.robots

The Robots.txt manager is responsible for deciding when to download a robots.txt
file and for making enforcement decisions for robots.txt policy.

.. autoclass:: RobotsTxtManager
    :members:

.. autoclass:: RobotsTxt
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

.. _subscription:
