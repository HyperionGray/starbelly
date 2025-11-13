import 'dart:async';

import 'package:angular/angular.dart';
import 'package:angular_forms/angular_forms.dart';
import 'package:angular_router/angular_router.dart';
import 'package:convert/convert.dart' as convert;
import 'package:ng_fontawesome/ng_fontawesome.dart';
import 'package:ng_modular_admin/ng_modular_admin.dart';

import 'package:starbelly/component/routes.dart';
import 'package:starbelly/model/captcha.dart';
import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;
import 'package:starbelly/service/server.dart';

/// View details about a CAPTCHA solver.
@Component(
    selector: 'captcha-detail',
    styles: const ['''
        label input[type="checkbox"] {
            margin-left: 0.7em;
        }
        ma-input-group {
            max-width: 75%;
        }
        .form-labels {
            text-align: right;
            width: 10em;
        }
        ma-checkbox-group.inline label {
            display: inherit;
            margin-left: -0.9em;
        }
        .row.buttons {
            min-height: 5em;
        }
        .result {
            position: relative;
            top: -1em;
        }
    '''],
    templateUrl: 'detail.html',
    directives: const [coreDirectives, FaIcon, formDirectives,
        modularAdminDirectives, RouterLink],
    exports: [Routes],
    pipes: const [commonPipes]
)
class CaptchaDetailView implements OnActivate {
    bool newSolver;
    CaptchaSolver solver;
    String saveError = '';
    bool saveSuccess = false;

    var ALPHANUMERIC = pb.CaptchaSolverAntigateCharacters.ALPHANUMERIC;
    var NUMBERS_ONLY = pb.CaptchaSolverAntigateCharacters.NUMBERS_ONLY;
    var ALPHA_ONLY = pb.CaptchaSolverAntigateCharacters.ALPHA_ONLY;

    DocumentService _document;
    Router _router;
    ServerService _server;

    /// Constructor
    CaptchaDetailView(this._document, this._router, this._server);

    /// Called when Angular initializes the view.
    onActivate(_, RouterState current) async {
        this._document.title = 'CAPTCHA Solver';
        this._document.breadcrumbs = [
            new Breadcrumb(name: 'Configuration', icon: 'cogs'),
            new Breadcrumb(name: 'CAPTCHA Solvers', icon: 'eye',
                link: Routes.captchaList.toUrl()),
            new Breadcrumb(name: 'CAPTCHA Solver'),
        ];
        var captchaId = current.parameters['id'];
        this.newSolver = captchaId == null;
        if (this.newSolver) {
            this.solver = new CaptchaSolver('New Solver');
            this._document.title = 'New Solver';
            this._document.breadcrumbs.last.name = 'New Solver';
        } else {
            var request = new pb.Request();
            request.getCaptchaSolver = new pb.RequestGetCaptchaSolver()
                ..solverId = convert.hex.decode(captchaId);
            var message = await this._server.sendRequest(request);
            this.solver = new CaptchaSolver.fromPb(message.response.solver);
            this._document.title = 'CAPTCHA Solver: ${this.solver.name}';
            this._document.breadcrumbs.last.name = this.solver.name;
        }
    }

    /// Save the current CAPTCHA solver.
    ///
    /// If a new solver is created, then redirect to that new solver.
    save(Button button) async {
        button.busy = true;
        var request = new pb.Request()
            ..setCaptchaSolver = new pb.RequestSetCaptchaSolver();
        request.setCaptchaSolver.solver = this.solver.toPb();

        try {
            var message = await this._server.sendRequest(request);
            var response = message.response;
            saveError = '';
            saveSuccess = true;
            if (response.hasNewSolver()) {
                var solverId = convert.hex.encode(response.newSolver.solverId);
                this._router.navigate(Routes.captchaDetail.toUrl({"id": solverId}));
            } else {
                this._document.breadcrumbs.last.name = this.solver.name;
                new Timer(new Duration(seconds: 3), () {
                    this.saveSuccess = false;
                });
            }
        } on ServerException catch (exc) {
            saveError = 'Cannot save: ${exc.message}';
            saveSuccess = false;
        }
        button.busy = false;
    }
}
