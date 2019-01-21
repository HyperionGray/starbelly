*******************
Administrator Guide
*******************

.. contents::
    :depth: 2


Overview
========

This section goes over some common tasks that you may need to perform as a
Starbelly administrator. In the examples below, if a command prompt is prefixed
with a container name, then that indicates that the command must be run inside
a specific Docker container. For example, if you see this:

.. code::

    starbelly-dev-app:/starbelly# ls /usr/local/etc
    jupyter

Then that command should be run inside of the ``starbelly-dev-app`` container.
To obtain a shell inside that container, run:

.. code::

    $ docker exec -it starbelly-dev-app /bin/bash
    starbelly-dev-app#

You can use the same technique to get a shell inside the ``starbelly-dev-db`` or
``starbelly-dev-web`` containers.

Clear Database
==============

To clear all data from the database, including crawl data, job data, and other
state:

.. code::

    starbelly-dev-app:/starbelly# python tools/clear.py

Change Password
===============

Adding or changing passwords is covered in the :doc:`installation` under the
"Security" section.
