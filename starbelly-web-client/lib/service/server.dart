import 'dart:async';
import 'dart:html';
import 'dart:typed_data';

import 'package:angular/angular.dart';
import 'package:logging/logging.dart';

import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;

/// This class handles interaction with the server, abstracting out details like
/// command IDs and pairing responses to requests.
@Injectable()
class ServerService {
    /// Sends true when connected to server and false when disconnected.
    Stream<bool> connected;
    bool isConnected = false;

    int _nextCommandId;
    Map<int,Completer> _pendingRequests;
    Future<WebSocket> _socketFuture;
    Map<int,StreamController> _subscriptions;
    StreamController<bool> _connectedController;

    final Logger log = new Logger('ServerService');

    /// Constructor.
    ServerService() {
        this._clearState();
        this._connectedController = new StreamController<bool>.broadcast();
        this.connected = this._connectedController.stream;
    }

    /// Send a request to the server and return a future response.
    Future<ServerResponse> sendRequest(pb.Request request) async {
        var socket = await this._getSocket();
        var completer = new Completer<ServerResponse>();
        request.requestId = this._nextCommandId;
        this._pendingRequests[request.requestId] = completer;
        this._nextCommandId++;
        var requestData = request.writeToBuffer();
        socket.send(requestData.buffer); // There's no async API for Websocket!
        return completer.future;
    }

    /// Tell the server to connect immediately and automatically re-connect
    /// if the connection drops.
    stayConnected() async {
        await this._getSocket();

        this.connected.listen((isConnected) async {
            if (!isConnected) {
                log.info('Will try to reconnect in 2 seconds.');
                await new Future.delayed(new Duration(seconds: 2));
                this._socketFuture == null;
                await this._getSocket();
            }
        });
    }

    /// Clear out all state related to a connection.
    ///
    /// This is useful for resetting after closing a connection as well as for
    /// initialization of this object.
    void _clearState() {
        this._nextCommandId = 0;
        this._pendingRequests = {};
        this._socketFuture = null;
        this._subscriptions = {};
    }

    /// Return a websocket wrapped in a future. If not already connected, this
    /// method will connect to the websocket before completing the future.
    Future<WebSocket> _getSocket() {
        if (this._socketFuture == null) {
            var completer = new Completer<WebSocket>();
            var currentUri = Uri.parse(window.location.href);
            var socketUri = new Uri(
                scheme: 'wss',
                userInfo: currentUri.userInfo,
                host: currentUri.host,
                port: currentUri.port,
                path: '/ws/',
            );
            var socket = new WebSocket(socketUri.toString());
            socket.binaryType = 'arraybuffer';
            this._socketFuture = completer.future;

            socket.onClose.listen((event) {
                log.info('Socket disconnected.');
                this._clearState();
                this._connectedController.add(false);
                this.isConnected = false;
            });

            socket.onError.listen((event) {
                var err = 'Server error!';
                log.severe(err, event);
                completer.completeError(err);
                this._socketFuture = null;
            });

            socket.onMessage.listen(this._handleServerMessage);

            socket.onOpen.listen((event) {
                log.info('Socket connected.');
                completer.complete(socket);
                this._connectedController.add(true);
                this.isConnected = true;
            });
        }

        return this._socketFuture;
    }

    /// Handles an incoming message from the websocket.
    ///
    /// This either completes a command future with a response, or it sends
    /// a message to a subscription stream.
    void _handleServerMessage(MessageEvent event) {
        var buffer = (event.data as ByteBuffer).asUint8List();
        var message = new pb.ServerMessage.fromBuffer(buffer);

        if (message.hasResponse()) {
            this._handleServerResponse(message.response);
        } else if (message.hasEvent()) {
            this._handleServerEvent(message.event);
        } else {
            /// If we received a message that isn't a response or an event,
            /// there's really nothing we can do about it.
            throw new Exception(
                'Unexpected message type: ' + message.toString()
            );
        }
    }

    /// Handle an Event message.
    ///
    /// This places event data into the stream controller associated with this
    /// subscription.
    void _handleServerEvent(pb.Event event) {
        var controller = this._subscriptions[event.subscriptionId];
        // A race could lead to receiving an event after closing a
        // subscription.
        if (controller != null) {
            if (event.hasSubscriptionClosed()) {
                controller.close();
            } else {
                controller.add(event);
            }
        }
    }

    /// Handle a Response message.
    ///
    /// This returns response data or a subscription stream back to the caller
    /// who sent the request.
    void _handleServerResponse(pb.Response response) {
        var requestId = response.requestId;
        var completer = this._pendingRequests.remove(requestId);
        var serverResponse = new ServerResponse(response);

        if (response.isSuccess) {
            if (response.hasNewSubscription()) {
                var subId = response.newSubscription.subscriptionId;
                serverResponse.subscription = this._newSubscription(subId);
            }
            completer.complete(serverResponse);
        } else {
            completer.completeError(new ServerException(response.errorMessage));
        }
    }

    /// Create a new subscription stream.
    Stream<pb.Event> _newSubscription(int subscriptionId) {
        var controller = new StreamController<pb.Event>();
        this._subscriptions[subscriptionId] = controller;

        controller.onCancel = () async {
            if (!controller.isClosed) {
                var request = new pb.Request();
                request.unsubscribe = new pb.RequestUnsubscribe();
                request.unsubscribe.subscriptionId = subscriptionId;
                await this.sendRequest(request);
            }
            this._subscriptions.remove(subscriptionId);
        };

        return controller.stream;
    }
}

/// A ServerException is thrown if a server-side error occurs while processing
/// a request.
class ServerException implements Exception {
    String message;
    ServerException(this.message);
    String toString() {
        return 'ServerException: "${message}"';
    }
}

/// This class represents a response that is received from the server.
///
/// Some responses also include a subscription which can be listened to for
/// additional server events; otherwise the subscription will be null.
///
/// This class should only be instantiated by the ServerService.
class ServerResponse {
    pb.Response response;
    Stream<pb.Event> subscription;
    ServerResponse(this.response, [this.subscription]);
}
