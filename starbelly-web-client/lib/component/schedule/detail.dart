import 'dart:async';

import 'package:angular/angular.dart';
import 'package:angular_forms/angular_forms.dart';
import 'package:angular_router/angular_router.dart';
import 'package:convert/convert.dart' as convert;
import 'package:ng_fontawesome/ng_fontawesome.dart';
import 'package:ng_modular_admin/ng_modular_admin.dart';

import 'package:starbelly/component/routes.dart';
import 'package:starbelly/model/job.dart';
import 'package:starbelly/model/policy.dart';
import 'package:starbelly/model/schedule.dart';
import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;
import 'package:starbelly/service/server.dart';

/// View details about a job schedule.
@Component(
    selector: 'schedule-detail',
    styles: const ['''
        .input-label {
            text-align: right;
            width: 8em;
        }
        ma-radio-group {
            margin-bottom: 1.5em;
        }
        .radio-label {
            margin-left: 3.4em;
            margin-right: 0.4em;
        }
        dl {
            display: flex;
        }
        dt {
            text-align: right;
            width: 7em;
            font-size: 16px;
            font-weight: 600;
            padding-right: 0.5em;
        }
        dd {
            margin-bottom: .5rem;
            margin-left: 0;
        }
        p.legend {
            margin-left: 8.4em;
            margin-top: -0.8em;
            font-size: 10pt;
        }
        .row.buttons {
            min-height: 5em;
        }
    '''],
    templateUrl: 'detail.html',
    directives: const [coreDirectives, FaIcon, formDirectives,
        modularAdminDirectives, RouterLink],
    exports: [Routes],
    pipes: const [commonPipes]
)
class ScheduleDetailView implements OnActivate {
    List<Policy> policies;
    String scheduleId;
    Schedule schedule;
    String saveError = '';
    bool saveSuccess = false;
    bool created = false;
    String seedUrl = '';
    Job latestJob = null;

    DocumentService _document;
    Router _router;
    ServerService _server;

    var REGULAR_INTERVAL = pb.ScheduleTiming.REGULAR_INTERVAL;
    var AFTER_PREVIOUS_JOB_FINISHED =
        pb.ScheduleTiming.AFTER_PREVIOUS_JOB_FINISHED;

    var MINUTES = pb.ScheduleTimeUnit.MINUTES;
    var HOURS = pb.ScheduleTimeUnit.HOURS;
    var DAYS = pb.ScheduleTimeUnit.DAYS;
    var WEEKS = pb.ScheduleTimeUnit.WEEKS;
    var MONTHS = pb.ScheduleTimeUnit.MONTHS;
    var YEARS = pb.ScheduleTimeUnit.YEARS;

    /// Constructor
    ScheduleDetailView(this._document, this._router, this._server) {
        this.policies = [];
    }

    /// Create a URL for listing this job's schedules.
    String listScheduleJobsUrl() {
        return Routes.scheduleJobs.toUrl({'id': this.scheduleId});
    }

    /// Save the current schedule.
    ///
    /// If a new schedule is created, then redirect to that new schedule.
    save(Button button) async {
        button.busy = true;
        if (this.schedule.seeds.length == 0) {
            this.schedule.seeds.add(this.seedUrl);
        } else {
            this.schedule.seeds[0] = this.seedUrl;
        }
        var request = new pb.Request()
            ..setSchedule = new pb.RequestSetSchedule();
        try {
            request.setSchedule.schedule = this.schedule.toPb();
            var message = await this._server.sendRequest(request);
            var response = message.response;
            saveError = '';
            saveSuccess = true;
            if (response.hasNewSchedule()) {
                var scheduleId = convert.hex.encode(
                    response.newSchedule.scheduleId);
                this._router.navigate(Routes.scheduleDetail.toUrl(
                    {'id': scheduleId}), NavigationParams(queryParameters:
                    {'created': 'true'}));
            } else {
                this.schedule.updatedAt = new DateTime.now();
                this._document.breadcrumbs.last.name =
                    this.schedule.scheduleName;
                new Timer(new Duration(seconds: 3), () {
                    this.saveSuccess = false;
                });
            }
        } on Exception catch (exc) {
            saveError = 'Cannot save: ${exc}';
            saveSuccess = false;
        }
        button.busy = false;
    }

    /// Implement ngAfterViewInit() as an async method.
    onActivate(_, RouterState current) async {
        this.created = current.queryParameters.containsKey('created');
        this.scheduleId = current.parameters['id'];
        var scheduleName;

        if (this.scheduleId == null) {
            this.schedule = new Schedule.defaultSettings();
            scheduleName = this.schedule.scheduleName;
        } else {
            scheduleName = this.scheduleId.substring(0, 8);
        }

        this._document.title = scheduleName;
        this._document.breadcrumbs = [
            new Breadcrumb(name: 'Schedule', icon: 'calendar',
                link: Routes.scheduleList.toUrl()),
            new Breadcrumb(name: scheduleName),
        ];

        if (this.scheduleId != null) {
            var schedule = await this._fetchSchedule(this.scheduleId);
            this.schedule = schedule;
            this.seedUrl = schedule.seeds.length > 0 ? schedule.seeds[0] : '';
            this._document.title = 'Schedule: ${this.schedule.scheduleName}';
            this._document.breadcrumbs.last.name = this.schedule.scheduleName;
        }

        this.policies = await this._fetchPolicies();
        this.latestJob = await this._fetchJob();
    }

    /// Fetch the latest job for this schedule.
    Future<Job> _fetchJob() async {
        var request = new pb.Request();
        request.listScheduleJobs = new pb.RequestListScheduleJobs()
            ..scheduleId = convert.hex.decode(this.scheduleId);
        var message = await this._server.sendRequest(request);
        var jobList = message.response.listScheduleJobs.jobs;
        var latestJob = null;
        if (jobList.length > 0) {
            latestJob = Job.fromPb2(jobList[0]);
        }
        return latestJob;
    }

    /// Fetch a list of policies.
    Future<List<Policy>> _fetchPolicies() async {
        var request = new pb.Request()
            ..listPolicies = new pb.RequestListPolicies();
        request.listPolicies.page = new pb.Page()
            ..limit = 100
            ..offset = 0;
        var message = await this._server.sendRequest(request);
        var pbPolicies = message.response.listPolicies.policies;
        var policies = new List.generate(
            pbPolicies.length,
            (i) => new Policy.fromPb(pbPolicies[i])
        );
        return policies;
    }

    /// Fetch the job schedule object.
    Future<Schedule> _fetchSchedule(String scheduleId) async {
        var request = new pb.Request();
        request.getSchedule = new pb.RequestGetSchedule()
            ..scheduleId = convert.hex.decode(scheduleId);
        var message = await this._server.sendRequest(request);
        var schedule = new Schedule.fromPb(message.response.schedule);
        return schedule;
    }
}
