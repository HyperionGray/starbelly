import 'dart:async';

import 'package:angular/angular.dart';
import 'package:angular_router/angular_router.dart';
import 'package:convert/convert.dart' as convert;
import 'package:ng_fontawesome/ng_fontawesome.dart';
import 'package:ng_modular_admin/ng_modular_admin.dart';

import 'package:starbelly/component/external_link.dart';
import 'package:starbelly/component/routes.dart';
import 'package:starbelly/model/item.dart';
import 'package:starbelly/model/job.dart';
import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;
import 'package:starbelly/service/job_status.dart';
import 'package:starbelly/service/server.dart';

/// View successful crawl items.
@Component(
    selector: 'results-success',
    styles: const ['''
        table {
            table-layout: fixed;
        }
        td pre {
            overflow-x: auto;
            margin-bottom: 0;
        }
        td.expanded {
            /* This makes no sense, but it fixes an x-overflow bug. */
            max-width: 0
        }
        td:nth-child(1) {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        th:nth-child(2) {
            width: 5em;
        }
        th:nth-child(3) {
            width: 4em;
        }
        th:nth-child(4) {
            width: 6em;
        }
    '''],
    templateUrl: 'success.html',
    directives: const [coreDirectives, FaIcon, modularAdminDirectives,
        RouterLink, ExternalLinkComponent],
    pipes: const [commonPipes]
)
class ResultSuccessView implements OnActivate {
    int currentPage = 1;
    int endRow = 0;
    List<CrawlItem> items;
    String jobId;
    String jobName;
    int rowsPerPage = 10;
    int showBody;
    int startRow = 0;
    int totalRows = 0;

    DocumentService _document;
    JobStatusService _jobStatus;
    Router _router;
    ServerService _server;
    StreamSubscription<Job> _subscription;

    /// Constructor
    ResultSuccessView(this._document, this._jobStatus, Router router, this._server) : _router = router;

    /// Fetch current page.
    getPage() async {
        this.showBody = null;
        var request = new pb.Request();
        request.getJobItems = new pb.RequestGetJobItems()
            ..jobId = convert.hex.decode(this.jobId)
            ..compressionOk = false
            ..includeSuccess = true;
        request.getJobItems.page = new pb.Page()
            ..limit = this.rowsPerPage
            ..offset = (this.currentPage - 1) * this.rowsPerPage;
        var message = await this._server.sendRequest(request);
        var pbItems = message.response.listItems.items;
        this.totalRows = message.response.listItems.total;
        this.items = new List<CrawlItem>.generate(
            pbItems.length,
            (i) => new CrawlItem.fromPb2(pbItems[i])
        );
        this.startRow = (this.currentPage - 1) * this.rowsPerPage + 1;
        this.endRow = this.startRow + this.items.length - 1;
    }

    /// Called when Angular initializes the view.
    onActivate(_, RouterState current) async {
        this.jobId = current.parameters['id'];
        
        // Read page number from URL query parameter
        var pageParam = current.queryParameters['page'];
        if (pageParam != null) {
            var pageNum = int.tryParse(pageParam);
            if (pageNum != null && pageNum > 0) {
                this.currentPage = pageNum;
            }
        }
        
        this._document.title = 'Successes';
        this._document.breadcrumbs = [
            new Breadcrumb(name: 'Results', icon: 'sitemap',
                link: Routes.resultList.toUrl()),
            new Breadcrumb(name: 'Crawl',
                link: Routes.resultDetail.toUrl({'id': this.jobId})),
            new Breadcrumb(name: 'Successes')
        ];

        this._jobStatus.getName(this.jobId).then((jobName) {
            this.jobName = jobName;
            this._document.breadcrumbs[1].name = jobName;
        });

        this._subscription = this._jobStatus.events.listen((Job update) {
            if (this.jobId == update.jobId &&
                (update.itemCount ?? 0) > this.totalRows) {
                this.totalRows = update.itemCount;
                if (items != null && items.length != this.rowsPerPage) {
                    this.getPage();
                }
            }
        });
        this.getPage();
    }

    /// Called when Angular destroys the view.
    void ngOnDestroy() {
        this._subscription.cancel();
    }

    /// Called by the pager to select a new page.
    void selectPage(Page page) {
        this.currentPage = page.pageNumber;
        // Update URL with new page number
        this._router.navigate(
            Routes.resultSuccess.toUrl({'id': this.jobId}),
            NavigationParams(queryParameters: {'page': page.pageNumber.toString()})
        );
        this.getPage();
    }
}
