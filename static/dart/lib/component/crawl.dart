import 'dart:async';

import 'package:angular2/core.dart';

import 'package:starbelly/service/document.dart';
import 'package:starbelly/service/server.dart';

/// View and manage crawls.
@Component(
    selector: 'crawl',
    templateUrl: 'crawl.html'
)
class CrawlComponent implements OnInit, OnDestroy {
    List<Map> crawls;
    String rateLimit = '';
    String seedUrl = '';

    ServerService _server;
    StreamSubscription _subscription;
    DocumentService _document;

    /// Constructor
    CrawlComponent(this._document, this._server) {
        this.crawls = new List<Map>();
    }

    /// Request a new crawl.
    startCrawl() async {
        var rateLimit = null;

        /// Angular's handling of number inputs is absurd. It if has a value,
        /// it will be a double, but if it's blank, it will be a string!
        if (this.rateLimit is double) {
            rateLimit = this.rateLimit;
        }

        var response = await this._server.command('start_crawl', {
            'seeds': [
                { 'rate_limit': rateLimit, 'url': this.seedUrl },
            ]
        });

        this.seedUrl = '';
    }

    /// Cancel all subscriptions before the component is destroyed.
    ngOnDestroy() async {
        this._subscription.cancel();
    }

    /// Subscribe to crawl stats after the component is initialized.
    ngOnInit() async {
        this._document.title = 'Crawl';

        var response = await this._server.command(
            'subscribe_crawl_stats',
            {'min_interval': 1}
        );

        this._subscription = response.subscription.listen((event) {
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
                    stats['crawl_id'] = crawlId;
                    this.crawls.add(stats);
                }
            });
        });
    }
}
