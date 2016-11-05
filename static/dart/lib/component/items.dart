import 'dart:async';
import 'dart:html';

import 'package:angular2/core.dart';

import 'package:starbelly/service/document.dart';
import 'package:starbelly/service/server.dart';

/// View crawl items.
@Component(
    selector: 'items',
    templateUrl: 'items.html'
)
class ItemsComponent implements OnInit, OnDestroy {
    List<Map> crawls;
    List<Map> items;

    DocumentService _document;
    ServerService _server;
    Map<int,StreamSubscription> _subscriptions;
    Map<int,String> _sync_tokens;

    /// Constructor
    ItemsComponent(this._document, this._server) {
        this.crawls = new List<Map>();
        this.items = new List<Map>();
        this._subscriptions = new Map<int,StreamSubscription>();
        this._sync_tokens = new Map<int,String>();
    }

    /// Cancel all subscriptions before the component is destroyed.
    ngOnDestroy() async {
        this._subscriptions.values.forEach((sub) => sub.cancel());
    }

    /// Subscribe to crawl stats after the component is initialized.
    ngOnInit() async {
        this._document.title = 'Items';

        var response = await this._server.command(
            'subscribe_crawl_stats',
            {'min_interval': 5}
        );

        response.subscription.listen((event) {
            event.data.forEach((crawlId, stats) {
                var found = false;

                for (var crawl in this.crawls) {
                    if (crawl['crawl_id'] == crawlId) {
                        crawl.addAll(stats);
                        found = true;
                        break;
                    }
                }

                if (!found) {
                    stats['follow'] = false;
                    stats['crawl_id'] = crawlId;
                    this.crawls.add(stats);
                }
            });
        });
    }

    /// Toggle the follow status for the specified crawl.
    Future<Null> toggleFollow(Map crawl) async {
        crawl['follow'] = !crawl['follow'];
        var crawlId = crawl['crawl_id'];

        if (crawl['follow']) {
            var args = {'crawl_id': crawlId};

            if (this._sync_tokens.containsKey(crawlId)) {
                args['sync_token'] = this._sync_tokens[crawlId];
            }

            var response = await this._server.command(
                'subscribe_crawl_items', args
            );

            this._subscriptions[crawlId] = response.subscription.listen(
                this._handleCrawlItem
            );
        } else {
            this._subscriptions.remove(crawlId).cancel();
        }
    }

    /// Handle a crawl item event.
    void _handleCrawlItem(ServerEvent event) {
        var crawlItem = event.data;
        crawlItem['title'] = this._getHtmlTitle(window.atob(crawlItem['body']));
        crawlItem['flash_on'] = true;
        this.items.insert(0, crawlItem);
        if (this.items.length > 10) {
            this.items.removeLast();
        }
        var crawlId = event.data['crawl_id'];
        var syncToken = event.data['sync_token'];
        this._sync_tokens[crawlId] = syncToken;
        new Timer(new Duration(milliseconds: 500), () {
            crawlItem['flash_on'] = false;
        });
    }

    /// Get title from an HTML document (or N/A if it doesn't have a title).
    void _getHtmlTitle(String body) {
        var parser = new DomParser();
        var doc = parser.parseFromString(body, 'text/html');
        return doc.querySelector('title').text;
    }
}
