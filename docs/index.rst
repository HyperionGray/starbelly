.. image:: logo.png
    :height: 150px
    :width: 150px
    :align: center

Starbelly
=========

Starbelly is a user-friendly and highly configurable web crawler front end.
Compared to other crawling systems, such as Nutch or Scrapy, Starbelly trades
off lower scalability for improved usability. Starbelly eschews the arcane
configuration files and custom code required for other crawling systems,
favoring a GUI for configuration and managment. Starbelly exposes all of its
features and data through an efficient API, allowing you to build crawling-based
systems on top of it. For example, you might plug in an Elastic Search backend
to build a custom search engine, or plug in a scraper to create a data
collection pipeline.

.. toctree::
    :maxdepth: 1

    installation
    first_crawl
    configuration
    policy
    administration
    websocket_api
    protobuf
    development
    internals
    changelog

.. image:: https://hyperiongray.s3.amazonaws.com/define-hg.svg
    :target: https://www.hyperiongray.com/?pk_campaign=github&pk_kwd=agnostic
    :alt: define hyperiongray
    :width: 500px
