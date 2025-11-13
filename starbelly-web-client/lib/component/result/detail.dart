import 'dart:async';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:angular_forms/angular_forms.dart';
import 'package:angular_router/angular_router.dart';
import 'package:convert/convert.dart' as convert;
import 'package:ng_fontawesome/ng_fontawesome.dart';
import 'package:ng_modular_admin/ng_modular_admin.dart';

import 'package:starbelly/component/external_link.dart';
import 'package:starbelly/component/routes.dart';
import 'package:starbelly/model/job.dart';
import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;
import 'package:starbelly/service/job_status.dart';
import 'package:starbelly/service/server.dart';

/// View details about a crawl.
@Component(
    selector: 'results-detail',
    templateUrl: 'detail.html',
    directives: const [coreDirectives, FaIcon, formDirectives,
        modularAdminDirectives, RouterLink, ExternalLinkComponent],
    exports: [Routes],
    pipes: const [commonPipes]
)
class ResultDetailView implements OnActivate, OnDeactivate {
    Job job;
    String tags;

    var ACTION_ADD = pb.PolicyUrlRule_Action.ADD;
    var ACTION_MULTIPLY = pb.PolicyUrlRule_Action.MULTIPLY;

    var MATCHES = pb.PatternMatch.MATCHES;
    var DOES_NOT_MATCH = pb.PatternMatch.DOES_NOT_MATCH;

    var OBEY = pb.PolicyRobotsTxt_Usage.OBEY;
    var INVERT = pb.PolicyRobotsTxt_Usage.INVERT;
    var IGNORE = pb.PolicyRobotsTxt_Usage.IGNORE;

    DocumentService _document;
    JobStatusService _jobStatus;
    ServerService _server;
    StreamSubscription<Job> _subscription;

    /// Constructor
    ResultDetailView(this._document, this._jobStatus, this._server);

    /// Called when Angular enters the route.
    onActivate(_, RouterState current) async {
        this._document.title = 'Results';
        this._document.breadcrumbs = [
            new Breadcrumb(name: 'Results', icon: 'sitemap',
                link: Routes.resultList.toUrl()),
            new Breadcrumb(name: 'Crawl'),
        ];

        this._subscription = this._jobStatus.events.listen((Job update) {
            if (this.job != null && this.job.jobId == update.jobId) {
                this.job.mergeFrom(update);
            }
        });
        var request = new pb.Request();
        request.getJob = new pb.RequestGetJob();
        var jobId = current.parameters['id'];
        request.getJob.jobId = convert.hex.decode(jobId);
        var message = await this._server.sendRequest(request);
        this.job = new Job.fromPb2(message.response.job);
        this.tags = this.job.tags?.join(' ');
        this._document.title = this.job.name;
        this._document.breadcrumbs.last.name = this.job.name;
    }

    /// Called when Angular leaves the route.
    void onDeactivate(_, RouterState current) {
        this._subscription.cancel();
    }

    saveTags() async {
        var request = new pb.Request();
        request.setJob = new pb.RequestSetJob()
            ..jobId = convert.hex.decode(this.job.jobId);
        for (var tagStr in this.tags.split(new RegExp(' +'))) {
            request.setJob.tags.add(tagStr.trim());
        }
        var message = await this._server.sendRequest(request);
        if (!message.response.isSuccess) {
            window.alert('Could not save tags!');
        }
    }

    String successUrl(Job job) {
        return Routes.resultSuccess.toUrl({"id": job.jobId});
    }

    String errorUrl(Job job) {
        return Routes.resultError.toUrl({"id": job.jobId});
    }

    String exceptionUrl(Job job) {
        return Routes.resultException.toUrl({"id": job.jobId});
    }

    String policyUrl(Job job) {
        return Routes.resultPolicy.toUrl({"id": job.jobId});
    }
}
