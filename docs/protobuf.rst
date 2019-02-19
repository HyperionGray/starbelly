Protobuf Messages
=================

The structure of the API is described in :doc:`websocket_api`. The details of
all the individual messages are documened here. The client always sends a
`Request <#.Request>`__ message. The server always sends a `ServerMessage
<#.ServerMessage>`__ message, which contains either a `Response <#.Response>`__
to a request or an `Event <#.Event>`__ belonging to a subscription.

.. raw:: html
   :file: protobuf.html
