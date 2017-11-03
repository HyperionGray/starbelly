******
Policy
******

.. contents::
   :depth: 2

Overview
========

The *crawl policy* is one of the most important and powerful concepts in
Starbelly. A policy controls the crawler's behavior and decision making, guiding
which links the crawler follows, what kinds of resources it downloads, and how
long or how far it runs. When you start a crawl job, you must specify which
policy that job should use.

In this part of the documentation, we take a look at the features of the crawl
policy. To begin, click *Policy* in the Starbelly menu, then click on an
existing policy to view it, or click *New Policy* to create a new policy.

Authentication
==============

The authentication policy determines how a crawler can authenticate itself to a
web site. When the crawler sees a domain in a crawl for the first time, it
checks to see if it has any credentials for that domain. (See the configuration
of Credentials for more information.) If it does, it picks one
of the appropriate credentials at random and tries to login with it. Some login
forms may require a CAPTCHA. In those cases, you may configure a CAPTCHA solver
and specify that solver in the policy.

Robots.txt
==========

`Robots.txt <http://www.robotstxt.org/>`__ is a standard for specifying how
crawlers should interact with websites. By default, Starbelly will attempt to
download a ``robots.txt`` from each domain that it visits, and it will obey the
directives of any such files that it finds. In some circumstances, however,
such as crawling some old sites, it may be useful to ignore or even invert the
directives in a site's robots.txt, which you can configure using the policy.

URL Normalization
=================

The crawler attempts to avoid crawling the same URL multiple times. If two links
contain exactly identical URLs, then the crawler will only download that
resource once. On some sites, especially dynamically generated sites, multiple
URLs may refer to the same resource and differ only in the order of URL query
parameters or the values of semantically meaningless query parameters like
session IDs.

The URL normalization policy allows you to control this behavior. When enabled,
the crawler normalizes URLS using a number of techniques, including:

- sorting query parameters alphabetically
- upper case percent encodings
- remove query fragments
- etc.

You may specify URL query parameters that should be discarded during
normalization. By default, the crawler discards several common session ID
parameters. Alternatively, you can disable URL normalization completely,
although this may result in lots of duplicated downloads.

URL Rules
=========

The URL rules policy controls how a crawler selects links to follow. For each
page that is downloaded, the crawler extracts candidate links. For each candidate
link, the crawler checks the rules one-by-one until a rule matches, then the crawler
applies the matching rule.

For example, the default *Deep Crawl* policy contains two URL rules:

1. If the URL *matches* the regex ``^https?://({SEED_DOMAINS})/`` then *add* ``1.0``.
2. Else *multiply by* ``0.0``.

Let's say the URL is seeded with ``http://foo.com/bar``. It downloads this
document and assigns it a cost of 1.0. Cost is roughly similar to the concept of
*crawl depth* in other crawlers, but it is a bit more sophisticated. Each link
is assigned a cost based on the cost of the document where it was found and the
URL rule that it matches. If a link cost evaluates to zero, then the link is
thrown away. If the link is greater than zero but less than the "Max Cost"
specified in the crawl policy, then the crawler schedules the link to be
fetched. Links are fetched roughly in order of cost, so lower-cost items are
typically fetched before higher-cost items.

After the crawler downloads the document at ``http://foo.com/bar``, it checks
each link in that document against the URL rules in the policy. For example, if
the link matches the regex in rule #1, then the link will be given a score of
2.0: the rule says to add 1.0 to the cost of its parent (which was 1.0).

If the link matches rule #2, then that rule says to multiply the parent's cost
by zero. This results in the new cost being set to zero, and the crawler
discards links where the cost is zero, so the link will not be followed.

Although the URL rules are a bit complicated at first, they turn out to be a
very powerful way to guide the crawler. For example, if we step back a bit and
consider the effect of the two rules above, we see that it follows links inside
the seed domain and does not follow links outside the seed domain. In other
words, this is a *deep crawl*!

If we replace the two rules here with just a single rule that says "Always add
1.0" , then that would result in a *broad crawl* policy! In fact, you can go
look at the default *Broad Crawl* policy included in Starbelly to confirm that
this is how it works.

User Agents
===========

When the crawler downloads a resource, it sends a *User Agent* string in the
headers. By default, Starbelly sends a user agent that identifies itself with a
version number and includes a URL to its source code repository. You may
customize what user agent is sent using the policy. If you include multiple user
agent strings, one will be chosen at random for each request.

Proxy Rules
===========

By default, the crawler downloads resources directly from their hosts. In some
cases, you may want to proxy requests through an intermediary. The *Proxy Rules*
specify which proxy server should be used for which request, similar to the *URL
Rules* above.

MIME Type Rules
===============

While *URL Rules* determine which links to follow, *MIME Type Rules*  determine
what types of resources to download. By default, the crawler only downloads
resources that have a MIME type matching the regex ``^text/``, which matches
plain text and HTML resources. If you want the crawler to download images, for
example, then you would add a new rule like ``^image/*`` that would match GIF,
JPEG, and PNG resources.

The MIME type of a resource is determined by inspecting the ``Content-Type``
header, which  means that *MIME Type Rules* are not applied until *after the
crawler downloads headers* for a resource. If the crawler determines that a
resource should not be downloaded, then the crawler closes the connection and
discards any data that has already been downloaded.

Limits
======

The *Limits* policy specifies limits on how far and how long the crawl should
run. If a limit is left blank, then that limit will not be applied to the crawl.

- Max cost: the crawler will not follow links that have a cost greater than the
  one specified here.
- Max duration: the maximum amount of time the crawler should run, in seconds.
- Max items: the maximum number of items that the crawler should download. This
  number includes successes, errors, and exceptions.
