import 'dart:typed_data';

import 'package:convert/convert.dart' as convert;

import 'package:starbelly/model/policy.dart';
import 'package:starbelly/protobuf/starbelly.pb.dart' as pb;

var RUN_STATE_LABELS = {
    pb.JobRunState.CANCELLED: 'Cancelled',
    pb.JobRunState.COMPLETED: 'Completed',
    pb.JobRunState.PAUSED: 'Paused',
    pb.JobRunState.PENDING: 'Pending',
    pb.JobRunState.RUNNING: 'Running',
};

/// A crawl job.
class Job {
    String jobId;
    List<String> seeds;
    Policy policy;
    String name;
    List<String> tags;
    pb.JobRunState runState;
    DateTime startedAt;
    DateTime completedAt;
    int itemCount;
    int httpSuccessCount;
    int httpErrorCount;
    int exceptionCount;
    Map<int,HttpStatusCount> _httpStatusCounts;
    List<HttpStatusCount> httpStatusCounts;

    String get runStateStr => RUN_STATE_LABELS[runState];
    Uint8List get jobIdBytes => convert.hex.decode(jobId);

    /// Instantiate Job from a protobuf.
    Job.fromPb2(pb.Job pbJob) {
        this.jobId = convert.hex.encode(pbJob.jobId);
        if (pbJob.seeds.length > 0) {
            this.seeds = new List<String>.from(pbJob.seeds);
        }
        if (pbJob.hasPolicy()) {
            this.policy = new Policy.fromPb(pbJob.policy);
        }
        if (pbJob.hasName()) {
            this.name = pbJob.name;
        }
        this.tags = new List<String>.from(pbJob.tags);
        if (pbJob.hasRunState()) {
            this.runState = pbJob.runState;
        }
        if (pbJob.hasStartedAt()) {
            this.startedAt = DateTime.parse(pbJob.startedAt).toLocal();
        }
        if (pbJob.hasCompletedAt()) {
            this.completedAt = DateTime.parse(pbJob.completedAt).toLocal();
        }
        if (pbJob.hasItemCount()) {
            this.itemCount = pbJob.itemCount;
        }
        if (pbJob.hasHttpSuccessCount()) {
            this.httpSuccessCount = pbJob.httpSuccessCount;
        }
        if (pbJob.hasHttpErrorCount()) {
            this.httpErrorCount = pbJob.httpErrorCount;
        }
        if (pbJob.hasExceptionCount()) {
            this.exceptionCount = pbJob.exceptionCount;
        }
        this._httpStatusCounts = {};
        this.httpStatusCounts = [];
        for (var key in pbJob.httpStatusCounts.keys) {
            var value = pbJob.httpStatusCounts[key];
            var statusCount = new HttpStatusCount(key, value);
            this._httpStatusCounts[key] = statusCount;
            this.httpStatusCounts.add(statusCount);
        }
        this.httpStatusCounts.sort();
    }

    /// Merge data from another Job into this instance.
    void mergeFrom(Job other) {
        this.tags = other.tags ?? this.tags;
        this.runState = other.runState ?? this.runState;
        this.startedAt = other.startedAt ?? this.startedAt;
        this.completedAt = other.completedAt ?? this.completedAt;
        this.itemCount = other.itemCount ?? this.itemCount;
        this.httpSuccessCount = other.httpSuccessCount ?? this.httpSuccessCount;
        this.httpErrorCount = other.httpErrorCount ?? this.httpErrorCount;
        this.exceptionCount = other.exceptionCount ?? this.exceptionCount;
        for (var code in other._httpStatusCounts.keys) {
            var otherStatus = other._httpStatusCounts[code];
            if (this._httpStatusCounts.containsKey(code)) {
                this._httpStatusCounts[code].count = otherStatus.count;
            } else {
                var statusCount = new HttpStatusCount.from(otherStatus);
                this._httpStatusCounts[statusCount.code] = statusCount;
                this.httpStatusCounts.add(statusCount);
            }
        }
        if (other._httpStatusCounts.length > 0) {
            this.httpStatusCounts.sort();
        }
    }
}

/// A count of how many items have a particular HTTP status code.
class HttpStatusCount implements Comparable<HttpStatusCount> {
    int code;
    int count;
    HttpStatusCount(this.code, this.count);
    HttpStatusCount.from(HttpStatusCount other) {
        this.code = other.code;
        this.count = other.count;
    }
    int compareTo(HttpStatusCount other) => this.code.compareTo(other.code);
}
