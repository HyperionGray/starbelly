# Testing the Pagination URL Changes

This document provides instructions for testing the pagination URL changes.

## Prerequisites

To test these changes, you need:
- Dart SDK 2.7.1 or compatible version
- `webdev` tool: `pub global activate webdev 2.5.4`
- Access to a running Starbelly backend server
- A browser (Chromium or Chrome recommended)

## Setup

1. Install dependencies:
   ```bash
   cd starbelly-web-client
   pub get
   ```

2. Start the development server:
   ```bash
   webdev serve web:8081 --auto=restart
   ```

3. Access the application at `https://localhost` (assuming nginx is configured and pointing to the dev server)

## Test Cases

### Test Case 1: Basic Pagination URL
1. Navigate to any list view (e.g., `/policy`)
2. Verify URL is `/policy` (no page parameter for page 1)
3. Click "Next" or page "2"
4. Verify URL changes to `/policy?page=2`
5. Refresh the page
6. Verify you're still on page 2

### Test Case 2: Browser Back Button
1. Navigate to `/policy`
2. Click to page 2 (`/policy?page=2`)
3. Click to page 3 (`/policy?page=3`)
4. Click browser back button
5. Verify you're on page 2 and URL is `/policy?page=2`
6. Click browser back button again
7. Verify you're on page 1 and URL is `/policy`

### Test Case 3: Browser Forward Button
1. After completing Test Case 2, click browser forward button
2. Verify you're on page 2
3. Click forward again
4. Verify you're on page 3

### Test Case 4: Direct URL Navigation
1. Navigate directly to `/policy?page=5` in the browser
2. Verify you land on page 5 of policies
3. Try `/policy?page=999` (page that likely doesn't exist)
4. Verify it shows an empty page with correct page number

### Test Case 5: Invalid Page Parameters
1. Try `/policy?page=0` - should default to page 1
2. Try `/policy?page=-1` - should default to page 1
3. Try `/policy?page=abc` - should default to page 1
4. Try `/policy?page=` - should default to page 1

### Test Case 6: Bookmarking
1. Navigate to `/policy?page=3`
2. Bookmark the page
3. Close the tab
4. Open the bookmark
5. Verify you land on page 3

### Test Case 7: Link Sharing
1. Navigate to `/schedule?page=4`
2. Copy the URL
3. Open the URL in a new tab/window
4. Verify you land on page 4 of schedules

### Test Case 8: Navigation Between Pages
1. Start at `/policy?page=2`
2. Click on a policy detail link
3. View the policy detail page
4. Click browser back button
5. Verify you return to `/policy?page=2` (not page 1)

### Test Case 9: Job-Specific Lists
1. Navigate to a job detail page
2. Click on "Errors" tab
3. Navigate to page 2 of errors
4. Verify URL is `/result/{job-id}/error?page=2`
5. Refresh the page
6. Verify you're still on page 2 of errors

### Test Case 10: Multiple List Types
Test all list views to ensure consistency:
- `/policy?page=N` - Policies
- `/schedule?page=N` - Schedules
- `/result?page=N` - Job results
- `/captcha?page=N` - CAPTCHA solvers
- `/credential?page=N` - Credentials
- `/result/{id}/error?page=N` - Job errors
- `/result/{id}/exception?page=N` - Job exceptions
- `/result/{id}/success?page=N` - Job successes
- `/schedule/{id}/jobs?page=N` - Schedule jobs

## Expected Behavior

For all test cases:
- Page numbers should persist in the URL
- Browser navigation (back/forward) should work correctly
- Direct URL navigation should work
- Bookmarks should work
- Invalid page numbers should fall back to page 1
- The pager component should highlight the correct page
- Data should load for the correct page

## Regression Testing

Ensure existing functionality still works:
- Sorting (if implemented) should work with pagination
- Filtering (if implemented) should work with pagination
- Creating new items should navigate away correctly
- Deleting items should refresh the current page
- Editing items should return to the correct page after save

## Known Limitations

- If the total number of pages decreases (e.g., due to deletions) while viewing a high page number, the user might see an empty page. This is expected behavior.
- The implementation doesn't preserve page numbers across different list types (e.g., going from policy list page 3 to schedule list will start at page 1 of schedules).
