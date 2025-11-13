# Page Number URL Changes

## Overview

This document describes the changes made to implement page numbers in URLs for all paginated list views in the Starbelly web client.

## Problem

Previously, when users navigated through paginated lists and then clicked a link or used the browser's back button, they would always return to page 1. This made it difficult to:
- Bookmark specific pages
- Share links to specific pages
- Use browser history navigation effectively

## Solution

All list components now:
1. Read the `page` query parameter from the URL when initializing
2. Update the URL with the current page number when the user navigates to a different page

## Modified Components

The following components were updated:

### List Components with Simple Pagination
- `lib/component/policy/list.dart` - Policy list
- `lib/component/schedule/list.dart` - Schedule list
- `lib/component/captcha/list.dart` - CAPTCHA solver list
- `lib/component/credential/list.dart` - Domain login credentials list
- `lib/component/result/list.dart` - Crawl job results list

### List Components with Job-Specific Pagination
- `lib/component/result/error.dart` - HTTP error items for a specific job
- `lib/component/result/exception.dart` - Exception items for a specific job
- `lib/component/result/success.dart` - Successful items for a specific job
- `lib/component/schedule/jobs.dart` - Jobs for a specific schedule

## Implementation Details

### Reading Page from URL
When a component is activated, it now reads the `page` query parameter:

```dart
onActivate(_, RouterState current) {
    // Read page number from URL query parameter
    var pageParam = current.queryParameters['page'];
    if (pageParam != null) {
        var pageNum = int.tryParse(pageParam);
        if (pageNum != null && pageNum > 0) {
            this.currentPage = pageNum;
        }
    }
    this.getPage();
}
```

### Updating URL on Page Change
When the user selects a new page, the URL is updated:

```dart
selectPage(Page page) {
    this.currentPage = page.pageNumber;
    // Update URL with new page number
    this._router.navigate(
        Routes.policyList.toUrl(),
        NavigationParams(queryParameters: {'page': page.pageNumber.toString()})
    );
    this.getPage();
}
```

### Component Changes
- Components that used `AfterViewInit` were changed to use `OnActivate` to access `RouterState`
- Components that didn't have a `Router` dependency had it added to their constructors

## URL Examples

After these changes, URLs will look like:

- `/policy?page=2` - Page 2 of policies
- `/schedule?page=3` - Page 3 of schedules
- `/result?page=5` - Page 5 of job results
- `/result/abc123/error?page=2` - Page 2 of errors for job abc123
- `/schedule/def456/jobs?page=3` - Page 3 of jobs for schedule def456

## Benefits

1. **Bookmarkable Pages** - Users can bookmark any page in a list
2. **Shareable Links** - Users can share links to specific pages
3. **Browser History** - Browser back/forward buttons work correctly
4. **Better UX** - Users don't lose their place when navigating
5. **Deep Linking** - External links can point to specific pages

## Testing Recommendations

To test these changes:

1. Navigate to any list view
2. Click to page 2 or later
3. Note the URL now includes `?page=N`
4. Click a detail link and then use browser back button
5. Verify you return to the same page number
6. Bookmark a URL with a page number and open it in a new tab
7. Verify the bookmarked page loads correctly

## Breaking Changes

None - this is purely additive functionality. If no `page` parameter is present in the URL, the component defaults to page 1 as before.
