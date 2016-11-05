import 'dart:html' show document, window;

import 'package:angular2/platform/browser.dart' show bootstrap;
import 'package:angular2/src/compiler/url_resolver.dart' show UrlResolver;
import 'package:angular2/src/core/di/provider.dart' show provide;

import 'package:starbelly/component/app.dart' show AppComponent;

/// Application entrypoint.
///
/// Create a custom UrlResolver so that Dart knows where to find packages.
void main() {
    bootstrap(AppComponent, [
        provide(UrlResolver, useFactory:() => new UrlResolver('/static/dart/web/packages'))
    ]);
}
