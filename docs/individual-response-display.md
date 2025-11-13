# Individual Response Display Implementation Guide

## Overview

This document explains how to implement a dedicated page for viewing individual crawl responses in the Starbelly web client, addressing issue #18.

## Current State

Currently, crawl responses (success/error/exception) are displayed in a list view with a triangle widget (caret-right/caret-down icons) that toggles the visibility of response details inline:

```html
<!-- Current implementation in success.html, error.html, exception.html -->
<fa name='caret-right' (click)='showBody = index'></fa>
<fa name='caret-down' (click)='showBody = null'></fa>
```

## Proposed Solution

### Frontend Changes (starbelly-web-client repository)

#### 1. Create New Route

Add a new route in `lib/component/routes.dart`:

```dart
static final resultItem = RouteDefinition(
    routePath: RoutePath(path: 'result/:jobId/item/:index'),
    component: result_item_template.ResultItemViewNgFactory);
```

Add to the `all` routes list.

#### 2. Create New Component

Create files:
- `lib/component/result/item.dart`
- `lib/component/result/item.html`

**item.dart:**
```dart
import 'dart:async';
import 'package:angular/angular.dart';
import 'package:angular_router/angular_router.dart';
import 'package:convert/convert.dart' as convert;
import 'package:ng_fontawesome/ng_fontawesome.dart';
import 'package:ng_modular_admin/ng_modular_admin.dart';

import 'package:starbelly/component/external_link.dart';
import 'package:starbelly/component/routes.dart';
import 'package:starbelly/model/item.dart';
import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;
import 'package:starbelly/service/server.dart';

@Component(
    selector: 'results-item',
    templateUrl: 'item.html',
    directives: const [coreDirectives, FaIcon, modularAdminDirectives,
        RouterLink, ExternalLinkComponent],
    exports: [Routes],
    pipes: const [commonPipes]
)
class ResultItemView implements OnActivate {
    CrawlItem item;
    String jobId;
    String jobName;
    int itemIndex;
    int totalItems;
    String itemType; // 'success', 'error', or 'exception'

    DocumentService _document;
    ServerService _server;

    ResultItemView(this._document, this._server);

    onActivate(_, RouterState current) async {
        this.jobId = current.parameters['jobId'];
        this.itemIndex = int.parse(current.parameters['index']);
        this.itemType = current.queryParameters['type'] ?? 'success';
        
        this._document.title = 'Response Detail';
        this._document.breadcrumbs = [
            new Breadcrumb(name: 'Results', icon: 'sitemap',
                link: Routes.resultList.toUrl()),
            new Breadcrumb(name: 'Crawl',
                link: Routes.resultDetail.toUrl({'id': this.jobId})),
            new Breadcrumb(name: getTypeLink(),
                link: getTypeUrl()),
            new Breadcrumb(name: 'Response ${this.itemIndex + 1}')
        ];

        // Fetch the item using get_job_items with limit=1 and offset=itemIndex
        var request = new pb.Request();
        request.getJobItems = new pb.RequestGetJobItems()
            ..jobId = convert.hex.decode(this.jobId)
            ..compressionOk = false;
        
        // Set filters based on item type
        if (itemType == 'success') {
            request.getJobItems.includeSuccess = true;
        } else if (itemType == 'error') {
            request.getJobItems.includeError = true;
        } else if (itemType == 'exception') {
            request.getJobItems.includeException = true;
        }
        
        request.getJobItems.page = new pb.Page()
            ..limit = 1
            ..offset = this.itemIndex;
        
        var message = await this._server.sendRequest(request);
        this.totalItems = message.response.listItems.total;
        
        if (message.response.listItems.items.isNotEmpty) {
            this.item = new CrawlItem.fromPb2(
                message.response.listItems.items[0]
            );
        }
    }
    
    String getTypeLink() {
        switch (itemType) {
            case 'success': return 'Successes';
            case 'error': return 'Errors';
            case 'exception': return 'Exceptions';
            default: return 'Items';
        }
    }
    
    String getTypeUrl() {
        Map<String, String> params = {'id': this.jobId};
        switch (itemType) {
            case 'success': return Routes.resultSuccess.toUrl(params);
            case 'error': return Routes.resultError.toUrl(params);
            case 'exception': return Routes.resultException.toUrl(params);
            default: return Routes.resultDetail.toUrl(params);
        }
    }
    
    String prevItemUrl() {
        if (itemIndex <= 0) return null;
        return Routes.resultItem.toUrl({
            'jobId': jobId,
            'index': (itemIndex - 1).toString()
        }) + '?type=$itemType';
    }
    
    String nextItemUrl() {
        if (itemIndex >= totalItems - 1) return null;
        return Routes.resultItem.toUrl({
            'jobId': jobId,
            'index': (itemIndex + 1).toString()
        }) + '?type=$itemType';
    }
}
```

**item.html:**
```html
<div class='row'>
  <div class='col-lg'>
    <ma-card>
      <h2>Response Details</h2>
      <div *ngIf='item == null'>
        <p>Loading…</p>
      </div>
      <div *ngIf='item != null'>
        <p class='lead'>
          <strong>URL:</strong> <external-link [href]='item.url'></external-link>
        </p>
        
        <div class='row'>
          <div class='col-md-6'>
            <h3>Request Information</h3>
            <table class='striped'>
              <tbody>
                <tr>
                  <td><strong>Started:</strong></td>
                  <td>{{item.startedAt | date:'medium'}}</td>
                </tr>
                <tr>
                  <td><strong>Completed:</strong></td>
                  <td>{{item.completedAt | date:'medium'}}</td>
                </tr>
                <tr>
                  <td><strong>Duration:</strong></td>
                  <td>{{item.duration | number:'1.3'}} seconds</td>
                </tr>
                <tr>
                  <td><strong>Cost:</strong></td>
                  <td>{{item.cost | number:'1.1'}}</td>
                </tr>
                <tr *ngIf='item.statusCode'>
                  <td><strong>Status Code:</strong></td>
                  <td>{{item.statusCode}}</td>
                </tr>
                <tr *ngIf='item.contentType'>
                  <td><strong>Content Type:</strong></td>
                  <td>{{item.contentType}}</td>
                </tr>
                <tr *ngIf='item.exception'>
                  <td><strong>Exception:</strong></td>
                  <td>{{item.exception}}</td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <div class='col-md-6'>
            <h3>Headers</h3>
            <table class='striped'>
              <tbody>
                <tr *ngFor='let header of item.headers'>
                  <td><strong>{{header.key}}:</strong></td>
                  <td>{{header.value}}</td>
                </tr>
                <tr *ngIf='item.headers.length == 0'>
                  <td colspan='2'>No headers</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        
        <h3>Response Body</h3>
        <pre>{{item.bodyStr}}</pre>
        
        <div class='text-xs-center' style='margin-top: 20px;'>
          <a *ngIf='prevItemUrl()' [routerLink]='prevItemUrl()' class='btn btn-secondary'>
            <fa name='angle-left'></fa> Previous
          </a>
          <a [routerLink]='getTypeUrl()' class='btn btn-secondary'>Back to List</a>
          <a *ngIf='nextItemUrl()' [routerLink]='nextItemUrl()' class='btn btn-secondary'>
            Next <fa name='angle-right'></fa>
          </a>
        </div>
      </div>
    </ma-card>
  </div>
</div>
```

#### 3. Update List Views

Modify `success.html`, `error.html`, and `exception.html` to link to the detail page instead of using the toggle widget:

**Before:**
```html
<td [attr.colspan]='showBody == index ? 4 : 1'
    [class.expanded]='showBody == index'>
  <fa name='caret-right' (click)='showBody = index'></fa>
  <fa name='caret-down' (click)='showBody = null'></fa>
  <external-link [href]='item.url'></external-link>
  <pre *ngIf='showBody == index'>...</pre>
</td>
```

**After:**
```html
<td>
  <a [routerLink]='itemDetailUrl(index)'>
    {{item.url}}
  </a>
</td>
```

Add method to component (e.g., in `success.dart`):
```dart
String itemDetailUrl(int index) {
    return Routes.resultItem.toUrl({
        'jobId': this.jobId,
        'index': index.toString()
    }) + '?type=success';
}
```

#### 4. Address Issue #17 (URL Page Numbers)

Update list views to include page number in URL query parameters:
```dart
void selectPage(Page page) {
    this.currentPage = page.pageNumber;
    // Update URL with page number
    router.navigate(Routes.resultSuccess.toUrl({'id': this.jobId}),
        queryParameters: {'page': page.pageNumber.toString()});
    this.getPage();
}
```

## Backend Support

### Current Support (Implemented)

The backend now includes a `get_job_item(job_id, sequence)` database method that can fetch individual responses by their sequence number. This method:

- Fetches a single response from the database by sequence number
- Includes the response body if available
- Verifies the response belongs to the specified job
- Returns `None` if the item doesn't exist or doesn't belong to the job

### Future Enhancement

When the protobuf definitions can be updated (in starbelly-protobuf repository), add:

**RequestGetJobItem message:**
```protobuf
message RequestGetJobItem {
    required bytes job_id = 1;
    required int32 sequence = 2;
    optional bool compression_ok = 3 [default = true];
}
```

Then add API handler in `starbelly/server/job.py`:
```python
@api_handler
async def get_job_item(command, response, server_db):
    """ Get a single item (crawl response) from a job. """
    job_id = str(UUID(bytes=command.job_id))
    sequence = command.sequence
    
    item_doc = await server_db.get_job_item(job_id, sequence)
    
    if not item_doc:
        raise InvalidRequestException(
            f"No item with sequence={sequence} found for job {job_id}"
        )
    
    # Populate response.list_items with single item
    # ... (implementation similar to get_job_items)
```

## Benefits

1. **Better UX**: Each response has a dedicated, shareable URL
2. **Cleaner UI**: List views are simpler without toggle widgets
3. **Navigation**: Previous/Next buttons for browsing responses
4. **Performance**: Only load one response at a time instead of expanding in place
5. **Deep linking**: Users can bookmark specific responses

## Testing

Test the following scenarios:
1. Navigate to a response detail page from success/error/exception lists
2. Use Previous/Next navigation between responses
3. Share a response URL and verify it loads correctly
4. Test with responses that have/don't have bodies
5. Verify breadcrumb navigation works correctly
6. Test pagination state is preserved when returning to lists
