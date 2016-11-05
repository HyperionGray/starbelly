import 'dart:html';

import 'package:angular2/core.dart';

/// A service for manipulating global (i.e. document level) state.
@Injectable()
class DocumentService {
    String _title;

    String get title => this._title;

    void set title(String t) {
        /// Dart analyzer needs some help with window.document: it thinks it
        /// doesn't have a title property, but it actually does.
        (window.document as HtmlDocument).title = '$t — Starbelly';
    }

    DocumentService() {
        this.title = 'Loading…';
    }
}
