import 'package:angular2/core.dart';
import 'package:angular2/router.dart';

import 'package:starbelly/component/crawl.dart';
import 'package:starbelly/component/items.dart';
import 'package:starbelly/service/server.dart';
import 'package:starbelly/service/document.dart';

@Component(
    selector: 'app',
    templateUrl: 'app.html',
    directives: const [ROUTER_DIRECTIVES],
    providers: const [ROUTER_PROVIDERS, DocumentService, ServerService]
)
@RouteConfig(const [
    const Route(path: '/crawl', name: 'Crawl', component: CrawlComponent, useAsDefault: true),
    const Route(path: '/items', name: 'Items', component: ItemsComponent),
])
class AppComponent {}
