*******************
Configuration Guide
*******************

.. contents::
    :depth: 2

Overview
========

Starbelly can be configured entirely through its graphical interface. In fact,
this is one of the advantages to using Starbelly: no more arcane configuration
files or custom code! The tradeoff, of course, is that Starbelly has fewer
configuration options than other crawlers and may not be flexible enough to
solve all crawling problems.

The configuration items are all contained in the *Configuration* submenu on the
left side of the interface.

CAPTCHA Solvers
===============

Starbelly has the ability to automatically log into a website if it has the
appropriate credentials (see `Credentials`_ below). Some login forms may
require a CAPTCHA. In those cases, you may configure a CAPTCHA solving service.
Starbelly supports any CAPTCHA service that is compatible with the Antigate API.
You may create multiple configurations in order to use multiple backend solvers
or just to send different configurations to the same service.

Once you have created a CAPTCHA solver, specify that CAPTCHA solver in a crawl
policy in order to send login CAPTCHAs to the solving service during crawls.

Credentials
===========

Starbelly has the ability to automatically log into a website if it has the
appropriate credentials. To configure credentials for a site, you only need to
specify a login URL. (If the login URL enables single sign-on for multiple
subdomains, then you  should also specify the domain name that you wish to
authenticate on.)

For each domain, you may set up multiple username & password credentials. When
the crawler encounters that domain during a crawl, it will randomly pick one of
the credentials and attempt to login with it. (The crawler uses machine learning
to identify and parse the login form.)

Rate Limits
===========

The crawler observes rate limits between subsequent requests to a single domain.
For example, with the default delay of 5 seconds, the crawler will wait 5
seconds after a request completes until it initiates another request to that
same domain. Therfore, the crawler will download at most 12 pages per minute
from a single domain using the default rate limit. In practice, it will download
fewer than 12 pages per minute, since each request itself also takes some
non-negligible amount of time.

Furthermore, rate limits apply across all jobs. For example, if you have two
different jobs crawling one domain, each job will effectively be limited to 6
pages per minute instead of 12.

On the *Rate Limits* configuration screen, you may change the global limit as
well as customize rate limits for specific domains. This allows you to specify
lower rate limits for domains that can handle higher traffic. For example, you
might crawl web servers on your corporate intranet faster than you crawl a
public internet server.
