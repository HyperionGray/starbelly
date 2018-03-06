*****************
API Documentation
*****************

.. contents::
    :depth: 1

Overview
========

The crawler is controlled completely by an API. Clients connect to the crawler
using `websockets
<https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API>`__ and
exchange messages with the crawler using `protobuf messages
<https://developers.google.com/protocol-buffers/>`__. The built-in GUI relies
solely on this API, so everything that can be done in the GUI can also be done
with the API – and more!

One of the central goals for the API is to enable clients to synchronize crawl
results in real time. Most crawling systems are batch-oriented: you run the
crawler for a period of time and then collect the results when the crawl is
finished. Starbelly is streaming-oriented: it can send crawl results to a client
as soon as it downloads them.

Let's imagine that a crawl has started running and already has 1,000 results. A
client can connect to Starbelly and quickly fetch the first 1,000 results.
Because the crawler is still running, new results will continue to stream in as
the crawler downloads them. If either the server or the client needs to
disconnect for some reason, the client is able to reconnect later and pick up
the stream exactly where it left off.

Connecting to API
=================

The API is exposed as a websocket service on port 443 at the path ``/ws/``. For
example, if starbelly is running on the host ``starbelly.example.com``, then you
should connect to the web socket using the URL
``wss://starbelly.example.com/ws/``. By default, Starbelly uses HTTP basic
authentication, so you need to include those credentials when you connect to the
API.

Messages
========

Starbelly uses ``protobuf`` to encode messages sent between the client and the
server. There are three types of message used in the API:

1. Request
2. Response
3. Event

The *request* and *response* messages are created in pairs: the client sends a
*request* to the server and the server sends back exactly one *response* per
request. The response indicates whether the request was successful and may
include other data related to the request.

Although each request generates a response, the responses are not necessarily
sent back in the same order that the requests are received. If the client sends
two commands very quickly (call them A and B), it may get the responses back in
either order, e.g. A→B or B→A. For this reason, the client should include a
unique ``request_id`` with each request; the server will include the same
``request_id`` in its response so that the client can track which response goes
with which request. The client can assign request IDs in any manner that it
chooses, but one sensible approach would be to assign an incrementing sequence
of integers.

The third type of message is an *event*, which is pushed from the server to the
client. For example, the client can send a request to subscribe to job status.
The server will send a response containing a subscription ID. Now, whenever a
job has a status event, such as downloading a new resource, the server will send
an event to the client containing the job status data and the corresponding
subscription ID. The client can close the subscription by sending another
request. The server will stop sending event messages and will send a response
indicating that the subscription has been cancelled.

Protobuf is a binary serialization format that supports common data types like
integers, strings, lists, and maps. It is similar in purpose to JSON, but
protobuf is more efficient in terms of encoding overhead and serialization
speed.

Example Session
===============

This section shows a complete interaction where a client starts a crawl and
synchronizes crawl results. To begin, the client sends a ``RequestSetJob``
request to the server that includes the seed URL, a policy identifier, and a
crawl name.

.. code::

    Request {
        request_id: 1
        Command: RequestSetJob {
            run_state: RUNNING
            policy_id: d28b379ff3668322bfd5d56e11d4e34e
            seeds: "https://cnn.com"
            name: "My Crawl"
        }
    }

The server will kick off a crawling job and will send a response telling the
client that the job has started successfully and including an identifier for the
new job.

.. code::

    Response {
        request_id: 1
        is_success: true
        Body: ResponseNewJob {
            job_id: 0514478baffd401546b755bf460b5997
        }
    }

Notice that the response includes the request ID sent by the client, so
we know that this is a response to the above request.

This response tells us that the crawl is starting, but we would like to keep
track of the crawl's progress and know when it finishes. The next step is to
send a subscription request for job status events.

.. code::

    Request {
        request_id: 2
        Command: RequestSubscribeJobStatus {
            min_interval: 3.0
        }
    }

This subscription provides high-level job status for *all* crawl jobs, including
data like how many items have been downloaded, how many pages had errors, how
many pages results in exceptions, etc. Job status can change rapidly when the
crawler is busy, because each item downloaded counts as a change in job status.
The ``min_interval`` parameter specifies the minimum amount of time in between
job status events sent by the server. In this example, if there are multiple job
status events, the server will batch them together and send at most 1 event
every 3 seconds for this subscription. On the other hand, if the crawl is very
slow, then it may send events even less frequently than that.

The server will create the subscription and respond with a subscription
identifier.

.. code::

    Response {
        request_id: 1
        is_success: true
        Body: ResponseNewSubscription {
            subscription_id: 300
        }
    }

When the client first subscribes to job status, the crawler will send the
complete status of each currently running job. For example, if the crawler has
already downloaded one item, the job status may look like this:

.. code::

    Event {
        subscription_id: 300
        Body: JobList {
            jobs: {
                job_id: 0514478baffd401546b755bf460b5997
                seeds: "https://cnn.com"
                policy: d28b379ff3668322bfd5d56e11d4e34e
                name: "My Crawl"
                run_state: RUNNING
                started_at: "2017-11-03T10:14:42.194744"
                item_count: 1
                http_success_count: 1
                http_error_count: 0
                exception_count: 0
                http_status_counts: {
                    200: 1
                }
            }
        }
    }

After sending complete job status, the crawler will send small updates as the
job status changes. For example, after the crawler downloads a second item, it
will send an event like this:

.. code::

    Event {
        subscription_id: 300
        Body: JobList {
            jobs: {
                job_id: 0514478baffd401546b755bf460b5997
                item_count: 2
                http_success_count: 2
                http_status_counts: {
                    200: 2
                }
            }
        }
    }

Notice how the second message is much smaller: it only contains the fields that
have changed since the previous event. This is how the job status subscription
allows clients to efficiently keep track of the status of all jobs. This API is
used in the GUI to power the Dashboard and Results screens.

For a complete list of API messages, look at the `starbelly-protobuf
<https://github.com/hyperiongray/starbelly-protobuf>`__ repository.

Web Client
==========

The crawler GUI is implemented as a stand-alone application written in Dart, and
it interacts with the Starbelly server solely through the public API. Therefore,
anything that you can do in the GUI can also be done through the API.

https://github.com/hyperiongray/starbelly-web-client

Python Client
=============

A very basic and incomplete Python client library implementation is available:

https://github.com/hyperiongray/starbelly-python-client

This client library will be improved over time and made more stable, but for
now it may be used as a reference implementation.
