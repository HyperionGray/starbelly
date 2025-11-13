import 'dart:async';

import 'package:angular/angular.dart';
import 'package:convert/convert.dart' as convert;
import 'package:logging/logging.dart';
import 'package:ng_modular_admin/ng_modular_admin.dart';

import 'package:starbelly/model/job.dart';
import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;
import 'package:starbelly/service/server.dart';

/// A service for tracking crawl state, statistics, etc.
@Injectable()
class JobStatusService {
    Stream<Job> get events => _streamController.stream;
    List<Job> get jobs => _jobs;
    int get newJobCount => _newJobCount;
    String get newJobBadge =>
        _newJobCount == 0 ? '' : _newJobCount.toString();

    Map<String,Job> _jobMap;
    Map<String,String> _jobNames;
    List<Job> _jobs;
    int _newJobCount = 0;
    ServerService _server;
    StreamController<Job> _streamController;
    StreamSubscription _subscription;
    ToastService _toast;

    final Logger log = new Logger('JobStatusService');

    /// Constructor.
    JobStatusService(this._server, this._toast) {
        this._jobs = [];
        this._jobMap = {};
        this._jobNames = {};
        this._streamController = new StreamController<Job>.broadcast();

        // Subscribe automatically whenever we connect to the server.
        this._server.connected.listen((isConnected) {
            if (isConnected) {
                this._subscribe();
            } else if (this._subscription != null) {
                // We can't cancel the subscription because we aren't connected
                // to the server. We'll assume the server cancels subscriptions
                // when it closes a socket.
                this._subscription = null;
            }
        });
    }

    Future<String> getName(String jobId) async {
        if (!this._jobNames.containsKey(jobId)) {
            var request = new pb.Request();
            request.getJob = new pb.RequestGetJob();
            request.getJob.jobId = convert.hex.decode(jobId);
            var message = await this._server.sendRequest(request);
            var job = new Job.fromPb2(message.response.job);
            this._jobNames[jobId] = job.name;
        }

        return this._jobNames[jobId];
    }

    /// Reset the new job count.
    void resetNewJobCount() {
        this._newJobCount = 0;
    }

    /// Subscribe to crawl status events.
    _subscribe() async {
        pb.Request request = new pb.Request();
        request.subscribeJobStatus = new pb.RequestSubscribeJobStatus();
        request.subscribeJobStatus.minInterval = 1.0;
        var response = await this._server.sendRequest(request);
        bool firstEvent = true;

        log.info("Subscribed to crawl status.");

        this._subscription = response.subscription.listen((event) {
            var jobs = new List<Job>.generate(
                event.jobList.jobs.length,
                (i) => new Job.fromPb2(event.jobList.jobs[i])
            );

            for (var jobUpdate in jobs) {
                if (!firstEvent) {
                    // Do this before updating the job model, because a deleted
                    // job won't have a name to show in the toast.
                    this._toastJobUpdate(jobUpdate);
                }
                if (jobUpdate.runState == pb.JobRunState.DELETED) {
                    var job = this._jobMap.remove(jobUpdate.jobId);
                    // Remove name, but not right away: it may be needed for
                    // toasts or other reasons.
                    new Timer(new Duration(seconds: 60), () {
                        this._jobNames.remove(jobUpdate.jobId);
                    });
                    if (job != null) {
                        this._jobs.remove(job);
                    }
                } else {
                    this._streamController.add(jobUpdate);
                    var jobId = jobUpdate.jobId;
                    if (!this._jobMap.containsKey(jobId)) {
                        this._jobMap[jobId] = jobUpdate;
                        this.jobs.add(jobUpdate);
                        if (!firstEvent) {
                            this._newJobCount++;
                        }
                    } else {
                        var existingJob = this._jobMap[jobId];
                        existingJob.mergeFrom(jobUpdate);
                    }
                    if (!this._jobNames.containsKey(jobId) &&
                        jobUpdate.name != null) {
                        this._jobNames[jobId] = jobUpdate.name;
                    }
                }
            }

            this._jobs.sort((job1, job2) => job1.name.compareTo(job2.name));
            firstEvent = false;
        });
    }

    /// Evaluate a job update and display a toast, if appropriate.
    _toastJobUpdate(Job update) async {
        var name = update.name;
        var toast = this._toast.add;

        if (name == null) {
            name = await this.getName(update.jobId);
        }

        if (update.runState == pb.JobRunState.RUNNING) {
            if (!this._jobMap.containsKey(update.jobId) ||
                    this._jobMap[update.jobId].runState != pb.JobRunState.RUNNING) {
                toast('primary', 'Crawl started.', name, icon: 'play-circle');
            }
        } else if (update.runState == pb.JobRunState.PAUSED) {
            toast('primary', 'Crawl paused.', name, icon: 'pause-circle');
        } else if (update.runState == pb.JobRunState.CANCELLED) {
            toast('warning', 'Crawl cancelled.', name, icon: 'times-circle');
        } else if (update.runState == pb.JobRunState.COMPLETED) {
            toast('success', 'Crawl completed.', name, icon: 'check-circle');
        } else if (update.runState == pb.JobRunState.DELETED) {
            toast('danger', 'Crawl deleted.', name, icon: 'trash');
        }
    }
}
