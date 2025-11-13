import 'dart:async';

import 'package:angular/angular.dart';
import 'package:angular_router/angular_router.dart';
import 'package:ng_modular_admin/ng_modular_admin.dart';
import 'package:ng_fontawesome/ng_fontawesome.dart';

import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;
import 'package:starbelly/service/server.dart';

class TaskTree {
    String name;
    List<TaskTree> subtasks;
    int count;

    TaskTree.fromPb(pb.TaskTree taskTree) {
        this.name = taskTree.name;
        this.subtasks = new List<TaskTree>.generate(
            taskTree.subtasks.length,
            (i) => TaskTree.fromPb(taskTree.subtasks[i])
        );
        this.count = 1;
        for (var subtask in this.subtasks) {
            this.count += subtask.count;
        }
    }
}

@Component(
    selector: 'task-tree',
    template: '''<ul>
        <li>{{task.name}}</li>
        <ul *ngIf='task.subtasks.length > 0'>
            <task-tree *ngFor='let subtask of task.subtasks' [task]='subtask'>
            </task-tree>
        </ul>
    </ul>''',
    styles: const ['''
        ul {
            list-style-type: square;
            list-style-position: inside;
            padding-left: 1em;
        }
    '''],
    directives: const [coreDirectives, TaskTreeComponent]
)
class TaskTreeComponent {
    @Input()
    TaskTree task;
}

/// View Trio tasks.
@Component(
    selector: 'tasks',
    templateUrl: 'tasks.html',
    directives: const [coreDirectives, fontAwesomeDirectives,
        modularAdminDirectives, TaskTreeComponent],
    pipes: const [commonPipes]
)
class TasksView implements OnActivate, OnDeactivate {
    TaskTree rootTask;
    num period = 5.0;
    bool paused = false;

    DocumentService _document;
    ServerService _server;
    StreamSubscription<pb.Event> _subscription;
    TaskTree _newRootTask;

    /// Constructor
    TasksView(this._document, this._server) {
        this._document.title = 'Task Monitor';
        this._document.breadcrumbs = [
            new Breadcrumb(name: 'System', icon: 'desktop'),
            new Breadcrumb(name: 'Tasks', icon: 'tasks'),
        ];
    }

    /// Called when Angular initializes the view.
    void onActivate(_, RouterState current) {
        this.subscribe();
    }

    /// Called when Angular destroys the view.
    void onDeactivate(_, RouterState current) {
        if (this._subscription != null) {
            this._subscription.cancel();
        }
    }

    void pause() {
        this.paused = !this.paused;
    }

    void resume() {
        this.paused = !this.paused;
        this.rootTask = this._newRootTask;
    }

    /// Subscribe to task monitor events.
    subscribe() async {
        var request = new pb.Request();
        request.subscribeTaskMonitor = new pb.RequestSubscribeTaskMonitor()
            ..period = this.period;
        var response = await this._server.sendRequest(request);
        this._subscription = response.subscription.listen((event) {
            this._newRootTask = TaskTree.fromPb(event.taskTree);
            if (!this.paused) {
                this.rootTask = this._newRootTask;
            }
        });
    }
}
