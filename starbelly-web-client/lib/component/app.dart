import 'dart:html';

import 'package:angular/angular.dart';
import 'package:angular_router/angular_router.dart';
import 'package:logging/logging.dart';
import 'package:ng_fontawesome/ng_fontawesome.dart';
import 'package:ng_modular_admin/ng_modular_admin.dart';

import 'package:starbelly/component/routes.dart';
import 'package:starbelly/service/job_status.dart';
import 'package:starbelly/service/server.dart';

@Component(
    selector: 'app',
    templateUrl: 'app.html',
    styles: const ['''
        ma-side-nav-header {
            font-size: 1.5em;
            font-weight: 600;
        }

        ma-side-nav-header img {
            margin-left: -0.2em;
        }

        .breadcrumbs a {
            text-decoration: none;
        }

        .breadcrumbs fa.separator {
            margin-left: 0.5em;
            margin-right: 0.5em;
        }
    '''],
    directives: const [coreDirectives, fontAwesomeDirectives,
        modularAdminDirectives, routerDirectives],
    providers: const [modularAdminProviders, JobStatusService,
        DocumentService, ServerService],
    exports: [Routes]
)
class AppComponent {
    /// Service for getting status of jobs.
    DocumentService document;

    /// Service for getting status of jobs.
    JobStatusService jobStatus;

    /// Server service.
    ServerService server;

    /// Service for creating toast notifications.
    ToastService toast;

    /// Constructor.
    AppComponent(this.document, this.jobStatus, this.server, this.toast) {
        if (window.localStorage['starbelly-debug'] == 'true') {
            Logger.root.level = Level.ALL;
        } else {
            Logger.root.level = Level.SEVERE;
        }

        Logger.root.onRecord.listen((LogRecord r) {
            var msg = '[${r.level.name}] ${r.loggerName}: ${r.message}';
            if (r.object != null) {
                msg += ' (Object: ${r.object.toString()})';
            }
            window.console.log(msg);
        });

        this.server.stayConnected();
    }
}
