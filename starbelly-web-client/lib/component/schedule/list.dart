import 'dart:html';

import 'package:angular/angular.dart';
import 'package:angular_router/angular_router.dart';
import 'package:convert/convert.dart' as convert;
import 'package:ng_fontawesome/ng_fontawesome.dart';
import 'package:ng_modular_admin/ng_modular_admin.dart';

import 'package:starbelly/component/routes.dart';
import 'package:starbelly/model/schedule.dart';
import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;
import 'package:starbelly/service/server.dart';

/// View job schedules.
@Component(
    selector: 'schedule-list',
    templateUrl: 'list.html',
    directives: const [coreDirectives, FaIcon, modularAdminDirectives,
        RouterLink],
    pipes: const [commonPipes],
    exports: [Routes]
)
class ScheduleListView implements OnActivate {
    int currentPage = 1;
    int endRow = 0;
    List<Schedule> schedules;
    int rowsPerPage = 10;
    int startRow = 0;
    int totalRows = 0;

    DocumentService _document;
    Router _router;
    ServerService _server;

    /// Constructor
    ScheduleListView(this._document, Router router, this._server) : _router = router {
        this._document.title = 'Schedule';
        this._document.breadcrumbs = [
            new Breadcrumb(name: 'Schedule', icon: 'calendar')
        ];
    }

    /// Delete a job schedule.
    deleteSchedule(Button button, Schedule schedule) async {
        button.busy = true;
        var request = new pb.Request()
            ..deleteSchedule = new pb.RequestDeleteSchedule();
        request.deleteSchedule.scheduleId = convert.hex.decode(
            schedule.scheduleId);
        try {
            await this._server.sendRequest(request);
            await this.getPage();
        } on ServerException catch (exc) {
            window.alert('Could not delete schedule: ${exc}');
        }
        button.busy = false;
    }

    /// Generate a URL to a schedule detail.
    String detailUrl(String scheduleId) {
        return Routes.scheduleDetail.toUrl({"id": scheduleId});
    }

    /// Fetch current page of results.
    getPage() async {
        var request = new pb.Request()
            ..listSchedules = new pb.RequestListSchedules();
        request.listSchedules.page = new pb.Page()
            ..limit = this.rowsPerPage
            ..offset = (this.currentPage - 1) * this.rowsPerPage;
        var message = await this._server.sendRequest(request);
        this.totalRows = message.response.listSchedules.total;
        this.schedules = [];
        for (var pbSchedule in message.response.listSchedules.schedules) {
            this.schedules.add(new Schedule.fromPb(pbSchedule));
        }
        this.startRow = (this.currentPage - 1) * this.rowsPerPage + 1;
        this.endRow = this.startRow + this.schedules.length - 1;
    }

    /// Called when Angular initializes the view.
    void onActivate(_, RouterState current) {
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

    /// Called by the pager to select a new page.
    void selectPage(Page page) {
        this.currentPage = page.pageNumber;
        // Update URL with new page number
        this._router.navigate(
            Routes.scheduleList.toUrl(),
            NavigationParams(queryParameters: {'page': page.pageNumber.toString()})
        );
        this.getPage();
    }
}
