# Starbelly

## Overview

[Starbelly](http://www.uky.edu/Ag/CritterFiles/casefile/spiders/orbweavers/orb.htm#star)
is a little toy webcrawler written in Python 3.5 and `asyncio`.

The goal of this project is to experiment with designs for a maximally
user-friendly, real-time web crawling system. The crawler and it's minimal UI
constitute a standalone service. This backend service is intended to be plugged
into various front ends to support a wide range of crawling applications. For
example, create a domain-specific search engine by pairing the crawler backend
with a Solr/Elastic Search front end. The project includes a toy front end that
displays crawled pages in real-time.

## API

The API design for a real-time crawler is of particular relevance to this
project. In the pursuit of low latency, polling a web service is not feasible.
Instead, this API uses websockets — a common protocol with implementations
in many programming languages — to stream crawl results to API clients in real
time.

The API is briefly (read: incompletely) documented here for the purpose of
facilitating dicussion about its design.

The Starbelly API uses JSON-encoded messages. There are two types of message:

1. Command
2. Event

A *command* message is sent from the client to the server (a.k.a. the _request_),
and the server sends back one message (a.k.a. the _response_) for each request
that it receives. Responses are not necessarily sent back in the same order that
the corresponding requests are received: if the client sends two commands very
quickly (call them A and B), it may get the responses back in either order, e.g.
A→B or B→A. For this reason, the client should include a unique `command_id`
with each request; the server will include the same `command_id` in its response
so that the client can track which response goes with which request.

As an example, let's say the client wants to start a crawl. (Only the client can
initiate a command; the server may not.) The client sends a message like this:

    {
        "args": {
            "seeds": [
                "rate_limit": 2.5,
                "url": "http://foo.com"
            ]
        },
        "command_id": 0,
        "command": "start_crawl"
    }

In addition to specifying the seed URL to start crawling from, the client can
optionally specify a `rate_limit`. The rate limit is the number of seconds
after the crawler finishes fetching a resource from a given domain before the
crawler requests another resource from that same domain.
(OK… it's actually the _reciprocal_ of rate.) If not specified,
then a global default rate limit is used.

The server will kick off a crawling job and will send a response to tell the
client whether the command executed successfully.

    {
        "command_id": 0,
        "data": {
            "crawl_id": 0
        },
        "success": true,
        "type": "response"
    }

Note that the `command_id` in the responses matches that of the request, so if
the client has issued multiple crawl commands, it knows that this is the
response for `foo.com` and not one of the other commands. The response contains
a `type` field to indicate that it is a response to a command. (The other `type`
is `event`, which we'll look at next.) The `success` field is set to `true` if
the command executed successfully, and `data` contains any values returned by
the command. If the command fails to execute, then `success` is set to `false`
and `data` will contain an error message.

The immediate result of the command only tells us that the crawl is starting,
but we would like to keep track of the crawl's progress and know when it
finishes. For this purpose, some API commands set up a subscription and will
emit period `event` messages from the server to the client. (The client never
sends `event` messages back to the server.)

Continuing with the example above, now the client wants to subscribe to updates
about the crawl that it just kicked off. It sends a message like this:

    {
        "args": {
            "min_interval": 2
        },
        "command_id": 1,
        "command": "subscribe_crawl_stats"
    }

This particular subscription provides high-level statistics for _all_ crawls, so
it is not necessary to specify a particular crawl in the request. It does take a
`min_interval` argument, though, which specifies how long the server should
wait in between sending updates to the subscriber. In this example, the server
will send no more than 1 `event` every 2 seconds for this subscription.

The server responds like this:

    {
        "command_id": 1,
        "data": {
            "subscription_id": 0
        },
        "success": true,
        "type": "response"
    }

The response includes a `subscription_id` that the client can use to correlate
individual `event` messages with a specific subscription. At this point, the
server begins to send events. The client receives a message like this:

    {
        "data": {
            0: {
                "error": 0,
                "information": 0,
                "not_found": 0,
                "redirect": 0,
                "seed": "http://foo.com",
                "status": "running",
                "success": 1
            }
        },
        "subscription_id": 0,
        "type": "event"
    }

The `data` maps crawl IDs to crawl statistics. Recall from the crawl command
above that the crawl was assigned ID `0`, corresponding to the `0` key in the
`data` field. The keys of this object indicate how many resources the crawler
has encountered with various HTTP status codes, e.g. `error` corresponds to 5xx,
`success` corresponds to 2xx, etc. The server sends complete statistics in the
first message, because this client has no previous knowledge of this crawl's
state.

After 2 seconds (recall the `min_interval` above), the server sends the next
event.

    {
        "data": {
            0: {
                "success": 3
            }
        },
        "subscription_id": 0,
        "type": "event"
    }

Note that this message is much smaller, because the server is only sending the
fields that changed since the previous message. Since the previous event, the
crawl has retrieved two more resources successfully.

After 2 more seconds, the server sends another event:

    {
        "data": {
            0: {
                "status": "complete",
                "success": 5
            }
        },
        "subscription_id": 0,
        "type": "event"
    }

The crawler has now crawled two more resources since the last event, and it has
also set its status to `complete`. The server won't send any more updates after
this, since the crawl stats won't change if there are no crawls running. (If a
new crawl starts, then the server will start sending events to this subscriber
again.)

The final API is a subscription to fetch the resources that the crawler has
crawled. The client sends a command like this:

    {
        "args": {
            "crawl_id": 0
        },
        "command": "subscribe_crawl_items",
        "command_id": 2,
    }

The server responds:

    {
        "command_id": 2,
        "data": {
            "subscription_id": 1
        },
        "success": true,
        "type": "response"
    }

The response indicates that a new subscription has been created.

> Note: There is no `min_interval` for this API: the server will send crawl results as
> quickly as the client can consume. Note that the server does observe TCP flow
> control, so if the client is unable to process messages as quickly as the server
> is sending them, the server will slow down and allow the client to catch up.

Now the server starts sending items to the subscriber as a series of `event`
messages.

    {
        "data": {
            "body": "PCFET0NUWVBFIEhUTUwgUFVCTElDICItLy[snip],
            "completed_at": 1468038794.6994638,
            "crawl_id": 0,
            "depth": 0,
            "duration": 0.0052394866943359375,
            "headers": {
                "CONTENT-LENGTH": "949",
                "CONTENT-TYPE": "text/html; charset=utf-8",
                "DATE": "Sat, 09 Jul 2016 04:33:14 GMT",
                "SERVER": "SimpleHTTP/0.6 Python/3.5.1+"
            },
            "started_at": 1468038794.6942244,
            "status_code": 200,
            "sync_token": "MQ==",
            "url": http://foo.com/bar.html"
        },
        "subscription_id": 1,
        "type": "event"
    }

If the crawler has crawled some items before the subscription began, it will
send all of those pre-existing items to the client first. Then, it will continue
to send new items in real-time as the crawler runs. Therefore, the client never
misses any crawl items, even if it subscribed long after the crawl began.

If the client needs to interrupt its subscription for some reason — maybe it
loses network connectivity or crashes and needs to be restarted — it can use the
`sync_token` field from the item subscription to resume it's subscription
exactly where it left off. This token is an opaque value that the server
generates and provides to the client; the client doesn't need to understand its
meaning, it only needs to store the token associated with the most recent,
successful crawl item. Later, it provides that token back to the server, and
the server can resume the subscription exactly where it left off.

For the sake of example, let's say the client wants to unsubscribe after
receiving the one item shown above. It sends:

    {
        "args": {
            "subscription_id": 1
        },
        "command": "unsubscribe",
        "command_id": 3
    }

The server stops sending crawl items to the client and replies:

    {
        "command_id": 3,
        "data": {
            "subscription_id": 1
        },
        "success": true,
        "type": "response"
    }

Later on, the client wants to subscribe again and pick up where it left off.
It repeats the same subscription command as before, but this time it adds a
`sync_token` parameter:

    {
        "args": {
            "crawl_id": 0,
            "sync_token": "MQ=="
        },
        "command": "subscribe_crawl_items",
        "command_id": 4,
    }

The server responds:

    {
        "command_id": 4,
        "data": {
            "subscription_id": 2
        },
        "success": true,
        "type": "response"
    }

Now the server starts sending items again, but it _skips over the item that the
client has seen already._
