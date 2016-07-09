var commandId = 0;
var crawls = {};
var pendingCallbacks = {};
var socket;
var subscriptions = {};

function connect(host, port) {
    socket = new WebSocket('ws://' + host + ':' + port);
    socket.onmessage = function (event) {
        var response = JSON.parse(event.data);
        console.log('Received message:', response);
        if (response.type === 'response') {
            if (response.success === false) {
                Materialize.toast('Socket error (see console).', 2000);
                console.log('Socket error:');
                console.log(response);
            } else {
                var commandId = response.command_id;
                callback = pendingCallbacks[commandId];
                delete pendingCallbacks[commandId];
                callback(response);
            }
        } else if (response.type === 'event') {
            var subscriptionId = response.subscription_id;
            var callback = subscriptions[subscriptionId];
            callback(response);
        } else {
            console.log('Unknown message type:', response);
            console.log(mess)
        }
    }
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
        crawls = {};
        sendCommand('subscribe_crawl_stats', {'min_interval': 1}, function (response) {
            subscriptions[response.data.subscription_id] = handleCrawlStats;
        });
    };
}

function handleCrawlStats(event) {
    for (var crawlId in event.data) {
        if (!crawls.hasOwnProperty(crawlId)) {
            crawls[crawlId] = {};
        }
        for (var col in event.data[crawlId]) {
            crawls[crawlId][col] = event.data[crawlId][col];
        }
    }
    renderCrawlTable();
}

function renderCrawlTable() {
    var tbody = $('#crawl-status tbody');

    for (var id in crawls) {
        var crawl = crawls[id];
        var tr = tbody.find('tr[data-crawl-id="' + id + '"]');

        if (tr.length == 0) {
            tr = $('<tr>');
            tr.attr('data-crawl-id', id);
            for (var i = 0; i < 6; i++) {
                tr.append($('<td>'));
            }
            tbody.append(tr);
        }

        var tds = tr.find('td');
        var cols = ['seed', 'status', 'success', 'redirect', 'not_found',
                    'error'];
        tds.text(function (index) {return crawl[cols[index]]});
    }
}

function sendCommand(command, args, callback) {
    pendingCallbacks[commandId] = callback;
    var message = {
        'command_id': commandId,
        'command': command,
        'args': args
    };
    console.log('Sending command:', message);
    socket.send(JSON.stringify(message));
    commandId++;
}

function startCrawl(event) {
    event.preventDefault();
    var seedUrl = $('#seed-url').val();
    var rateLimit = $('#rate-limit').val();
    var seeds = [{'url': seedUrl, 'rate_limit': rateLimit}];
    sendCommand('start_crawl', {'seeds': seeds}, function (response) {
        crawls[response.data.crawl_id] = {
            'seed': seedUrl,
            'status': 'submitted',
            'success': '0',
            'redirect': '0',
            'not_found': '0',
            'error': '0',
        };
        renderCrawlTable();
    });
    // $('#crawl-form')[0].reset();
}

$(function () {
    var host = 'localhost';
    var port = 8001;
    connect(host, port);
    renderCrawlTable();
    $('#crawl-form').submit(startCrawl);
});
