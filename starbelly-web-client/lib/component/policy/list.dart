import 'package:angular/angular.dart';
import 'package:angular_router/angular_router.dart';
import 'package:convert/convert.dart' as convert;
import 'package:ng_fontawesome/ng_fontawesome.dart';
import 'package:ng_modular_admin/ng_modular_admin.dart';

import 'package:starbelly/component/routes.dart';
import 'package:starbelly/model/policy.dart';
import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;
import 'package:starbelly/service/server.dart';

/// List policies.
@Component(
    selector: 'policy-list',
    templateUrl: 'list.html',
    directives: const [coreDirectives, FaIcon, modularAdminDirectives,
        RouterLink],
    exports: [Routes],
    pipes: const [commonPipes]
)
class PolicyListView implements OnActivate {
    int currentPage = 1;
    int endRow = 0;
    List<Policy> policies;
    int rowsPerPage = 10;
    int startRow = 0;
    int totalRows = 0;

    DocumentService _document;
    Router _router;
    ServerService _server;

    /// Constructor
    PolicyListView(this._document, this._router, this._server) {
        this._document.title = 'Policy';
        this._document.breadcrumbs = [
            new Breadcrumb(name: 'Policy', icon: 'book')
        ];
    }

    /// Delete the specified policy
    deletePolicy(Button button, Policy policy) async {
        button.busy = true;
        var request = new pb.Request();
        request.deletePolicy = new pb.RequestDeletePolicy()
            ..policyId = convert.hex.decode(policy.policyId);
        await this._server.sendRequest(request);
        await this.getPage();
        button.busy = false;
    }

    /// Duplicate the specified policy.
    duplicatePolicy(Button button, Policy policyStub) async {
        button.busy = true;

        // Fetch the entire policy.
        var oldPolicyRequest = new pb.Request();
        oldPolicyRequest.getPolicy = new pb.RequestGetPolicy()
            ..policyId = convert.hex.decode(policyStub.policyId);
        var oldPolicyMessage = await this._server.sendRequest(oldPolicyRequest);

        // Create new policy
        var newPolicy = new Policy.fromPb(oldPolicyMessage.response.policy);
        newPolicy.policyId = null;
        newPolicy.name += ' (Copy)';
        newPolicy.createdAt = new DateTime.now();
        newPolicy.updatedAt = newPolicy.createdAt;

        // Save new policy.
        var newPolicyRequest = new pb.Request();
        newPolicyRequest.setPolicy = new pb.RequestSetPolicy();
        newPolicyRequest.setPolicy.policy = newPolicy.toPb();
        var newPolicyMessage = await this._server.sendRequest(newPolicyRequest);
        var newPolicyResponse = newPolicyMessage.response;
        var newPolicyId = convert.hex.encode(
            newPolicyResponse.newPolicy.policyId);
        this._router.navigate(Routes.policyDetail.toUrl({"id": newPolicyId}));
        button.busy = false;
    }

    /// Fetch current page of results.
    getPage() async {
        var request = new pb.Request()
            ..listPolicies = new pb.RequestListPolicies();
        request.listPolicies.page = new pb.Page()
            ..limit = this.rowsPerPage
            ..offset = (this.currentPage - 1) * this.rowsPerPage;
        var message = await this._server.sendRequest(request);
        this.totalRows = message.response.listPolicies.total;
        var policies = message.response.listPolicies.policies;
        this.policies = new List<Policy>.generate(
            policies.length,
            (i) => new Policy.fromPb(policies[i])
        );
        this.startRow = (this.currentPage - 1) * this.rowsPerPage + 1;
        this.endRow = this.startRow + this.policies.length - 1;
    }

    String detailUrl(Policy policy) {
        return Routes.policyDetail.toUrl({'id': policy.policyId});
    }

    /// Called when Angular initializes the view.
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

    /// Called by the pager to select a new page.
    selectPage(Page page) {
        this.currentPage = page.pageNumber;
        // Update URL with new page number
        this._router.navigate(
            Routes.policyList.toUrl(),
            NavigationParams(queryParameters: {'page': page.pageNumber.toString()})
        );
        this.getPage();
    }
}
