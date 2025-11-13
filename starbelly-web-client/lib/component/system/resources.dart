import 'dart:async';

import 'package:angular/angular.dart';
import 'package:angular_router/angular_router.dart';
import 'package:convert/convert.dart' as convert;
import 'package:fixnum/fixnum.dart';
import 'package:ng_modular_admin/ng_modular_admin.dart';

import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;
import 'package:starbelly/service/job_status.dart';
import 'package:starbelly/service/server.dart';

@Pipe('dataSize')
class DataSizePipe extends PipeTransform {
    static const bytes = 'bytes';
    static const kb = 'kB';
    static const mb = 'MB';
    static const gb = 'GB';
    static const tb = 'TB';
    static const pb = 'PB';
    static const List<String> units = [bytes, kb, mb, gb, tb, pb];

    String transform(Int64 value) {
        int unitIndex = 0;
        Int64 remainder;
        String remainderStr = '';
        while (value >= 1024 && unitIndex < units.length-1) {
            remainder = value % 1024;
            value >>= 10;
            unitIndex++;
        }
        if (remainder != null) {
            remainderStr = (remainder.toInt() / 1024).toStringAsFixed(2)
                .substring(1);
        }
        return '$value$remainderStr ${units[unitIndex]}';
    }
}

/// View crawl items.
@Component(
    selector: 'resources',
    templateUrl: 'resources.html',
    directives: const [coreDirectives, modularAdminDirectives],
    pipes: const [commonPipes, DataSizePipe]
)
class ResourcesView implements OnActivate, OnDeactivate {
    pb.ResourceFrame frame;
    Map jobNames;

    DocumentService _document;
    JobStatusService _jobStatus;
    ServerService _server;
    StreamSubscription<pb.Event> _subscription;

    /// Constructor
    ResourcesView(this._document, this._jobStatus, this._server) {
        this._document.title = 'Resources';
        this._document.breadcrumbs = [
            new Breadcrumb(name: 'System', icon: 'desktop'),
            new Breadcrumb(name: 'Resource Monitor', icon: 'chart-bar'),
        ];
    }

    /// Compute sum of CPU usages.
    num cpuUsage() {
        num sum = 0;

        for (var cpu in this.frame.cpus) {
            sum += cpu.usage;
        }

        return sum;
    }

    /// Compute percentage of memory usage.
    Int64 memoryUsage() {
        return new Int64(100) * this.frame.memory.used ~/ this.frame.memory.total;
    }

    /// Called when Angular enters this route.
    void onActivate(_, RouterState current) async {
        this._subscription = await this.subscribe();
    }

    /// Called when Angular exits this route.
    void onDeactivate(_, RouterState current) {
        if (this._subscription != null) {
            this._subscription.cancel();
            this._subscription = null;
        }
    }

    /// Subscribe to resource monitor events.
    subscribe() async {
        var request = new pb.Request();
        request.subscribeResourceMonitor =
            new pb.RequestSubscribeResourceMonitor()
                ..history = 1;
        var response = await this._server.sendRequest(request);
        return response.subscription.listen((event) {
            this.frame = event.resourceFrame;
            this.jobNames = {};
            for (var job in this.frame.jobs) {
                var jobId = convert.hex.encode(job.jobId);
                this.jobNames[job.jobId] = jobId.substring(0, 8);
                this._jobStatus.getName(jobId).then((name) {
                    this.jobNames[job.jobId] = name;
                });
            }
        });
    }
}
