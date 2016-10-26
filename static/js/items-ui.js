var commandId = 0;
var crawls = {};
var crawlSubscriptions = {};
var pendingCallbacks = {};
var socket;
var subscriptions = {};
var syncTokens = {};

function addCrawlItemToTable(crawlItem) {
    var parser = new DOMParser();
    var doc = parser.parseFromString(atob(crawlItem.body), 'text/html');
    var title = $('title', doc).text();
    var tbody = $('#page-data tbody');
    var tr = $('<tr>');
    var td = $('<td>');
    td.text(crawlItem.url);
    tr.append(td);
    td = $('<td>');
    td.text(title);
    tr.append(td);
    td = $('<td>');
    td.text(crawlItem.duration);
    tr.append(td);
    tbody.prepend(tr);
    tr.addClass('flashable');
    tr.addClass('flash-on');
    setTimeout(function () {tr.removeClass('flash-on')}, 500);
}

function connect(host) {
    socket = new WebSocket('wss://' + host + '/ws/');
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
        setTimeout(function () {connect(host);}, 3000);
    }
    socket.error = function (event) {
        Materialize.toast('Server error (see console)' + event, 2000);
        console.log(event);
    }
    socket.onopen = function (event) {
        Materialize.toast('Connected to server.', 2000);
        sendCommand('subscribe_crawl_stats', {'min_interval': 1}, function (response) {
            subscriptions[response.data.subscription_id] = handleCrawlStats;
        });
    };
}

function handleCrawlItem(event) {
    item = event.data;
    syncTokens[item.crawl_id] = item.sync_token;
    addCrawlItemToTable(item);
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
    renderCrawlCollection();
}

function renderCrawlCollection() {
    var parent = $('#crawls');

    for (var id in crawls) {
        var crawl = crawls[id];
        var li = parent.find('li[data-crawl-id="' + id + '"]');

        if (li.length == 0) {
            li = $('<li>')
                .addClass('collection-item')
                .attr('data-crawl-id', id);

            var a = $('<a>')
                .attr('href', crawl.seed)
                .attr('target', '_blank')
                .text(crawl.seed);
            li.append(a);

            var div = $('<div>').addClass('switch').addClass('right');
            li.append(div);

            var label = $('<label>');
            label.append(document.createTextNode('Ignore'));
            var input = $('<input>').attr('type', 'checkbox')
            label.append(input);
            label.append($('<span>').addClass('lever'));
            label.append(document.createTextNode('Follow'));
            div.append(label);

            parent.append(li);
            input.change(function (event) {
                if (event.target.checked) {
                    subscribeCrawlItems(id);
                } else {
                    unsubscribeCrawlItems(id);
                }
            });
        }
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

function subscribeCrawlItems(crawlId) {
    var args = {'crawl_id': crawlId};
    if (crawlId in syncTokens) {
        args['sync_token'] = syncTokens[crawlId];
    };

    sendCommand(
        'subscribe_crawl_items',
        args,
        function (response) {
            var subscriptionId = response.data.subscription_id;
            subscriptions[subscriptionId] = handleCrawlItem;
            crawlSubscriptions[crawlId] = subscriptionId;
        }
    );
}

function unsubscribeCrawlItems(crawlId) {
    var subscriptionId = crawlSubscriptions[crawlId];
    sendCommand(
        'unsubscribe',
        {'subscription_id': subscriptionId},
        function (response) {
            delete subscriptions[subscriptionId];
            delete crawlSubscriptions[crawlId];
        }
    );
}

$(function () {
    var host = 'localhost';
    connect(host);
    renderCrawlCollection();
});
