import 'package:angular/angular.dart';
import 'package:angular_forms/angular_forms.dart';
import 'package:ng_modular_admin/ng_modular_admin.dart';
import 'package:ng_fontawesome/ng_fontawesome.dart';

import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;
import 'package:starbelly/service/server.dart';
import 'package:starbelly/validate.dart' as validate;

/// Run a CPU profile.
@Component(
    selector: 'profile',
    templateUrl: 'profile.html',
    styles: const ['''
        form {
            max-width: 30em;
        }
        label {
            min-width: 10em;
        }
    '''],
    directives: const [coreDirectives, FaIcon, formDirectives,
        modularAdminDirectives],
    pipes: const [commonPipes]
)
class ProfileView {
    ControlGroup form;
    String duration = '3.0';
    Control durationControl;
    pb.ResponsePerformanceProfile profile;
    String sort = 'total_time';
    String top = '20';
    Control topControl;

    DocumentService _document;
    ServerService _server;

    /// Constructor
    ProfileView(this._document, this._server) {
        this._document.title = 'Task Monitor';
        this._document.breadcrumbs = [
            new Breadcrumb(name: 'System', icon: 'desktop'),
            new Breadcrumb(name: 'CPU Profile', icon: 'microchip'),
        ];
        this.durationControl = new Control('', Validators.compose([
            validate.required(), validate.number()]));
        this.topControl = new Control('', Validators.compose([
            validate.required(), validate.integer()]));
        this.form = new ControlGroup({
            'duration': this.durationControl,
            'top': this.topControl,
        });
    }

    /// Run a CPU profile.
    runProfile(Button button) async {
        button.busy = true;
        var request = new pb.Request();
        request.performanceProfile = new pb.RequestPerformanceProfile()
            ..duration = double.parse(this.duration)
            ..sortBy = this.sort
            ..topN = int.parse(this.top, radix: 10);
        var response = await this._server.sendRequest(request);
        this.profile = response.response.performanceProfile;
        button.busy = false;
    }
}
