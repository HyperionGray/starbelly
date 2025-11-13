import 'package:angular/angular.dart';
import 'package:angular_router/angular_router.dart';
import 'package:convert/convert.dart' as convert;
import 'package:ng_fontawesome/ng_fontawesome.dart';
import 'package:ng_modular_admin/ng_modular_admin.dart';

import 'package:starbelly/component/routes.dart';
import 'package:starbelly/model/captcha.dart';
import 'package:starbelly/model/job.dart';
import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;
import 'package:starbelly/service/server.dart';

/// View details about a policy.
@Component(
    selector: 'results-policy',
    templateUrl: 'policy.html',
    directives: const [coreDirectives, FaIcon, modularAdminDirectives,
        RouterLink],
    exports: [Routes],
    pipes: const [commonPipes]
)
class ResultPolicyView implements OnActivate {
    CaptchaSolver captchaSolver;
    Job job;

    var ACTION_ADD = pb.PolicyUrlRule_Action.ADD;
    var ACTION_MULTIPLY = pb.PolicyUrlRule_Action.MULTIPLY;

    var MATCHES = pb.PatternMatch.MATCHES;
    var DOES_NOT_MATCH = pb.PatternMatch.DOES_NOT_MATCH;

    var OBEY = pb.PolicyRobotsTxt_Usage.OBEY;
    var INVERT = pb.PolicyRobotsTxt_Usage.INVERT;
    var IGNORE = pb.PolicyRobotsTxt_Usage.IGNORE;

    DocumentService _document;
    ServerService _server;

    /// Constructor
    ResultPolicyView(this._document, this._server);

    /// Called when Angular initializes the view.
    onActivate(_, RouterState current) async {
        var jobId = current.parameters['id'];
        this._document.title = 'Policy';
        this._document.breadcrumbs = [
            new Breadcrumb(name: 'Results', icon: 'sitemap',
                link: Routes.resultList.toUrl()),
            new Breadcrumb(name: 'Crawl',
                link: Routes.resultDetail.toUrl({'id': jobId})),
            new Breadcrumb(name: 'Policy'),
        ];
        var request = new pb.Request();
        request.getJob = new pb.RequestGetJob();
        request.getJob.jobId = convert.hex.decode(jobId);
        var message = await this._server.sendRequest(request);
        this.job = new Job.fromPb2(message.response.job);
        this._document.title = "${this.job.name} Policy";
        var jobCrumb = this._document.breadcrumbs.length - 2;
        this._document.breadcrumbs[jobCrumb].name = this.job.name;

        // Get CAPTCHA solver.
        if (this.job.policy.captchaSolverId.isNotEmpty) {
            request = new pb.Request();
            request.getCaptchaSolver = new pb.RequestGetCaptchaSolver()
                ..solverId = convert.hex.decode(this.job.policy.captchaSolverId);
            var message = await this._server.sendRequest(request);
            this.captchaSolver = new CaptchaSolver.fromPb(message.response.solver);
        }
    }

    String captchaUrl(Job job) {
        return Routes.captchaDetail.toUrl({"id": job.policy.captchaSolverId});
    }

    String policyUrl(Job job) {
        return Routes.policyDetail.toUrl({"id": job.policy.policyId});
    }
}
