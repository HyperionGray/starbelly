import 'package:angular/angular.dart';
import 'package:angular_forms/angular_forms.dart';
import 'package:angular_router/angular_router.dart';
import 'package:ng_fontawesome/ng_fontawesome.dart';
import 'package:ng_modular_admin/ng_modular_admin.dart';
import 'package:ng_modular_admin/validators.dart' as MaValidators;

import 'package:starbelly/component/routes.dart';
import 'package:starbelly/model/domain_login.dart';
import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;
import 'package:starbelly/service/server.dart';
import 'package:starbelly/validate.dart' as validate;

/// View crawl items.
@Component(
    selector: 'credential-list',
    templateUrl: 'list.html',
    directives: const [coreDirectives, FaIcon, formDirectives,
        modularAdminDirectives, RouterLink],
    exports: [Routes]
)
class CredentialListView implements OnActivate {
    int currentPage = 1;
    Control domainControl;
    int endRow = 0;
    List<DomainLogin> domainLogins;
    Control loginUrlControl;
    ControlGroup newDomainLoginForm;
    String newModalError;
    int rowsPerPage = 10;
    bool showNewModal = false;
    int startRow = 0;
    int totalRows = 0;

    DocumentService _document;
    Router _router;
    ServerService _server;

    /// Constructor
    CredentialListView(this._document, this._router, this._server) {
        this._document.title = 'Credentials';
        this._document.breadcrumbs = [
            new Breadcrumb(name: 'Configuration', icon: 'cogs'),
            new Breadcrumb(name: 'Credentials', icon: 'key')
        ];

        this.loginUrlControl = new Control('', Validators.compose([
            MaValidators.required(),
            validate.url()
        ]));
        this.domainControl = new Control();
        this.newDomainLoginForm = new ControlGroup({
            'loginUrl': this.loginUrlControl,
            'domain': this.domainControl,
        });
    }

    /// Create a new rate limit object.
    createDomainLogin(String loginUrl, String domain) async {
        if (domain.isEmpty) {
            var uri = Uri.parse(loginUrl);
            domain = uri.host;
        }
        var request = new pb.Request();
        request.setDomainLogin = new pb.RequestSetDomainLogin();
        request.setDomainLogin.login = new pb.DomainLogin()
            ..domain = domain
            ..loginUrl = loginUrl;
        try {
            await this._server.sendRequest(request);
            newModalError = null;
            showNewModal = false;
            this._router.navigate(Routes.credentialDetail.toUrl(
                {"domain": domain}));
        } on ServerException catch (exc) {
            newModalError = exc.message;
        }
    }

    /// Delete the specified domain login.
    deleteDomainLogin(Button button, DomainLogin domainLogin) async {
        button.busy = true;
        var request = new pb.Request();
        request.deleteDomainLogin = new pb.RequestDeleteDomainLogin()
            ..domain = domainLogin.domain;
        await this._server.sendRequest(request);
        await this.getPage();
        button.busy = false;
    }

    /// Return URL to detail page.
    String detailUrl(DomainLogin domainLogin) {
        return Routes.credentialDetail.toUrl({"domain": domainLogin.domain});
    }

    /// Fetch current page of results.
    getPage() async {
        var request = new pb.Request()
            ..listDomainLogins = new pb.RequestListDomainLogins();
        request.listDomainLogins.page = new pb.Page()
            ..limit = this.rowsPerPage
            ..offset = (this.currentPage - 1) * this.rowsPerPage;
        var message = await this._server.sendRequest(request);
        this.totalRows = message.response.listDomainLogins.total;
        var logins = message.response.listDomainLogins.logins;
        this.domainLogins = new List.generate(
            logins.length,
            (i) => new DomainLogin.fromPb(logins[i])
        );
        this.startRow = (this.currentPage - 1) * this.rowsPerPage + 1;
        this.endRow = this.startRow + this.domainLogins.length - 1;
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
            Routes.credentialList.toUrl(),
            NavigationParams(queryParameters: {'page': page.pageNumber.toString()})
        );
        this.getPage();
    }
}
