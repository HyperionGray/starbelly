import 'package:angular/angular.dart';
import 'package:angular_forms/angular_forms.dart';
import 'package:convert/convert.dart' as convert;
import 'package:ng_fontawesome/ng_fontawesome.dart';
import 'package:ng_modular_admin/ng_modular_admin.dart';

import 'package:starbelly/model/policy.dart';
import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;
import 'package:starbelly/service/server.dart';
import 'package:starbelly/validate.dart' as validate;

/// Start a new crawl job.
@Component(
    selector: 'crawl-start',
    templateUrl: 'start.html',
    styles: const ['''
        form {
            max-width: 30em;
        }
    '''],
    directives: const [coreDirectives, FaIcon, formDirectives,
        modularAdminDirectives]
)
class StartCrawlView implements AfterViewInit {
    ControlGroup form;
    List<Policy> policies;
    String name = '';
    Control nameControl;
    String policyId;
    String seedUrl = '';
    Control seedUrlControl;
    Policy selectedPolicy;
    String tags = '';
    Control tagsControl;

    List<int> policyIds;
    ServerService _server;
    DocumentService _document;

    /// Constructor
    StartCrawlView(this._document, this._server) {
        this._document.title = 'Start Crawl';
        this._document.breadcrumbs = [
            new Breadcrumb(name: 'Start Crawl', icon: 'play-circle')
        ];
        this._initForm();
    }

    /// Load policy names into select.
    ngAfterViewInit() async {
        var request = new pb.Request()
            ..listPolicies = new pb.RequestListPolicies();
        request.listPolicies.page = new pb.Page()
            ..limit = 100
            ..offset = 0;
        var message = await this._server.sendRequest(request);
        var policies = message.response.listPolicies.policies;
        if (policies.length > 0) {
            this.policies = new List<Policy>.generate(
                policies.length,
                (i) => new Policy.fromPb(policies[i])
            );
            this.selectedPolicy = this.policies[0];
        }
    }

    /// Request a new crawl.
    startCrawl() async {
        var request = new pb.Request();
        request.setJob = new pb.RequestSetJob()
            ..name = this.name
            ..runState = pb.JobRunState.RUNNING
            ..policyId = convert.hex.decode(this.selectedPolicy.policyId)
            ..seeds.add(this.seedUrl);
        for (var tagStr in this.tags.split(new RegExp(r'\s+'))) {
            var tagTrim = tagStr.trim();
            if (tagTrim.isNotEmpty) {
                request.setJob.tags.add(tagTrim);
            }
        }
        await this._server.sendRequest(request);
        this._initForm();
    }

    /// Initialize form controls.
    void _initForm() {
        this.nameControl = new Control('');
        this.seedUrlControl = new Control('', Validators.compose([
            validate.required(), validate.url()]));
        this.tagsControl = new Control('');
        this.form = new ControlGroup({
            'name': this.nameControl,
            'seedUrl': this.seedUrlControl,
            'tags': this.tagsControl,
        });
    }
}
