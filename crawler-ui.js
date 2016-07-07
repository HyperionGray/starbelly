var _commandId = 0;
var _pendingCallbacks = {};
var socket;

function connect(host, port) {
    socket = new WebSocket('ws://' + host + ':' + port);
    socket.onmessage = function (event) {
        console.log('received: ' + event.data);
    };
    socket.onclose = function (event) {
        Materialize.toast('Server disconnected!', 2000);
        setTimeout(function () {connect(host, port);}, 3000);
    }
    socket.error = function (event) {
        Materialize.toast('Server error (see console)' + event, 2000);
        console.log(event);
    }
    socket.onopen = function (event) {
        Materialize.toast('Connected to server.', 2000);
    };
}

function recvCommand(event) {
    var response = JSON.parse(event.data);
    if (response['success'] === false) {
        Materialize.toast('Error in recvCommand (see console).', 2000);
    }
    console.log('Response:');
    console.log(response);
    var commandId = response['id'];
    callback = _pendingCallbacks[commandId];
    delete _pendingCallbacks[commandId];
    callback(response);
}

function sendCommand(command, args, callback) {
    _pendingCallbacks[_commandId] = callback;
    var message = {
        'id': _commandId,
        'command': command,
        'args': args
    };
    console.log('Sending command:');
    console.log(message);
    socket.send(JSON.stringify(message));
    _commandId++;
}

function startCrawl(event) {
    event.preventDefault();
    var seedUrl = $('#seed-url').val();
    var rateLimit = $('#rate-limit').val();
    var seeds = [{'url': seedUrl, 'rate_limit': rateLimit}];
    sendCommand('start_crawl', {'seeds': seeds}, function (response) {
        console.log(response);
    });
}

$(function () {
    var host = 'localhost';
    var port = 8001;
    connect(host, port);
    $('#crawl-form').submit(startCrawl);
});
