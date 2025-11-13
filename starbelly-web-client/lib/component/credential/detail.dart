import 'dart:async';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:angular_forms/angular_forms.dart';
import 'package:angular_router/angular_router.dart';
import 'package:ng_fontawesome/ng_fontawesome.dart';
import 'package:ng_modular_admin/ng_modular_admin.dart';

import 'package:starbelly/component/routes.dart';
import 'package:starbelly/model/domain_login.dart';
import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;
import 'package:starbelly/service/server.dart';

/// View details about a credential.
@Component(
    selector: 'credential-detail',
    styles: const ['''
        table {
            table-layout: fixed;
        }
        th:nth-child(1) {
            width: 35%;
        }
        th:nth-child(2) {
            width: 40%;
        }
        th:nth-child(3) {
            width: 25%;
        }
        td span.masked, td:hover span.unmasked {
            display: inline;
        }
        td span.unmasked, td:hover span.masked {
            display: none;
        }
        label {
            width: 8em;
        }
    '''],
    templateUrl: 'detail.html',
    directives: const [coreDirectives, FaIcon, formDirectives,
        modularAdminDirectives],
)
class CredentialDetailView implements OnActivate {
    String addError;
    String domain;
    DomainLogin domainLogin;
    String saveError = '';
    bool saveSuccess;
    bool showAddUser = false;

    DocumentService _document;
    ServerService _server;

    /// Constructor
    CredentialDetailView(this._document, this._server);

    /// Add a user.
    addUser(Element usernameEl, Element passwordEl) async {
        var userEl = usernameEl as InputElement;
        var passEl = passwordEl as InputElement;
        var username = userEl.value;
        var password = passEl.value;
        if (username.isEmpty || password.isEmpty) {
            this.addError = 'Username and password are required.';
        } else {
            this.addError = null;
            var user = new DomainLoginUser(username, password);
            this.domainLogin.users.add(user);
            userEl.value = '';
            passEl.value = '';
            this.showAddUser = false;
        }
    }

    /// Delete a user.
    deleteUser(int index) async {
        this.domainLogin.users.removeAt(index);
    }

    /// Called when Angular enters this route.
    onActivate(_, RouterState current) async {
        this.domain = current.parameters['domain'];
        this._document.title = domain;
        this._document.breadcrumbs = [
            new Breadcrumb(name: 'Configuration', icon: 'cogs'),
            new Breadcrumb(name: 'Credentials', icon: 'key',
                link: Routes.credentialList.toUrl()),
            new Breadcrumb(name: domain),
        ];

        var request = new pb.Request();
        request.getDomainLogin = new pb.RequestGetDomainLogin()
            ..domain = this.domain;
        var message = await this._server.sendRequest(request);
        this.domainLogin = new DomainLogin.fromPb(message.response.domainLogin);
    }

    /// Save credential.
    save(Button button) async {
        button.busy = true;
        var request = new pb.Request();
        request.setDomainLogin = new pb.RequestSetDomainLogin()
            ..login = this.domainLogin.toPb();
        var message = await this._server.sendRequest(request);
        this.saveError = '';
        button.busy = false;
        if (message.response.isSuccess) {
            this.saveSuccess = true;
            new Timer(new Duration(seconds: 3), () {
                this.saveSuccess = false;
            });
        } else {
            this.saveError = message.response.errorMessage;
        }
    }

    /// Set the login URL.
    setLoginUrl(String loginUrl) {
        this.domainLogin.loginUrl = loginUrl;
    }
}
