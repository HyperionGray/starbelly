///
//  Generated code. Do not modify.
//  source: starbelly.proto
///
// ignore_for_file: camel_case_types,non_constant_identifier_names,library_prefixes,unused_import,unused_shown_name

// ignore_for_file: UNDEFINED_SHOWN_NAME,UNUSED_SHOWN_NAME
import 'dart:core' as $core show int, dynamic, String, List, Map;
import 'package:protobuf/protobuf.dart' as $pb;

class CaptchaSolverAntigateCharacters extends $pb.ProtobufEnum {
  static const CaptchaSolverAntigateCharacters ALPHANUMERIC = CaptchaSolverAntigateCharacters._(1, 'ALPHANUMERIC');
  static const CaptchaSolverAntigateCharacters NUMBERS_ONLY = CaptchaSolverAntigateCharacters._(2, 'NUMBERS_ONLY');
  static const CaptchaSolverAntigateCharacters ALPHA_ONLY = CaptchaSolverAntigateCharacters._(3, 'ALPHA_ONLY');

  static const $core.List<CaptchaSolverAntigateCharacters> values = <CaptchaSolverAntigateCharacters> [
    ALPHANUMERIC,
    NUMBERS_ONLY,
    ALPHA_ONLY,
  ];

  static final $core.Map<$core.int, CaptchaSolverAntigateCharacters> _byValue = $pb.ProtobufEnum.initByValue(values);
  static CaptchaSolverAntigateCharacters valueOf($core.int value) => _byValue[value];

  const CaptchaSolverAntigateCharacters._($core.int v, $core.String n) : super(v, n);
}

class JobRunState extends $pb.ProtobufEnum {
  static const JobRunState CANCELLED = JobRunState._(1, 'CANCELLED');
  static const JobRunState COMPLETED = JobRunState._(2, 'COMPLETED');
  static const JobRunState PAUSED = JobRunState._(3, 'PAUSED');
  static const JobRunState PENDING = JobRunState._(4, 'PENDING');
  static const JobRunState RUNNING = JobRunState._(5, 'RUNNING');
  static const JobRunState DELETED = JobRunState._(6, 'DELETED');

  static const $core.List<JobRunState> values = <JobRunState> [
    CANCELLED,
    COMPLETED,
    PAUSED,
    PENDING,
    RUNNING,
    DELETED,
  ];

  static final $core.Map<$core.int, JobRunState> _byValue = $pb.ProtobufEnum.initByValue(values);
  static JobRunState valueOf($core.int value) => _byValue[value];

  const JobRunState._($core.int v, $core.String n) : super(v, n);
}

class ScheduleTimeUnit extends $pb.ProtobufEnum {
  static const ScheduleTimeUnit MINUTES = ScheduleTimeUnit._(1, 'MINUTES');
  static const ScheduleTimeUnit HOURS = ScheduleTimeUnit._(2, 'HOURS');
  static const ScheduleTimeUnit DAYS = ScheduleTimeUnit._(3, 'DAYS');
  static const ScheduleTimeUnit WEEKS = ScheduleTimeUnit._(4, 'WEEKS');
  static const ScheduleTimeUnit MONTHS = ScheduleTimeUnit._(5, 'MONTHS');
  static const ScheduleTimeUnit YEARS = ScheduleTimeUnit._(6, 'YEARS');

  static const $core.List<ScheduleTimeUnit> values = <ScheduleTimeUnit> [
    MINUTES,
    HOURS,
    DAYS,
    WEEKS,
    MONTHS,
    YEARS,
  ];

  static final $core.Map<$core.int, ScheduleTimeUnit> _byValue = $pb.ProtobufEnum.initByValue(values);
  static ScheduleTimeUnit valueOf($core.int value) => _byValue[value];

  const ScheduleTimeUnit._($core.int v, $core.String n) : super(v, n);
}

class ScheduleTiming extends $pb.ProtobufEnum {
  static const ScheduleTiming AFTER_PREVIOUS_JOB_FINISHED = ScheduleTiming._(1, 'AFTER_PREVIOUS_JOB_FINISHED');
  static const ScheduleTiming REGULAR_INTERVAL = ScheduleTiming._(2, 'REGULAR_INTERVAL');

  static const $core.List<ScheduleTiming> values = <ScheduleTiming> [
    AFTER_PREVIOUS_JOB_FINISHED,
    REGULAR_INTERVAL,
  ];

  static final $core.Map<$core.int, ScheduleTiming> _byValue = $pb.ProtobufEnum.initByValue(values);
  static ScheduleTiming valueOf($core.int value) => _byValue[value];

  const ScheduleTiming._($core.int v, $core.String n) : super(v, n);
}

class PatternMatch extends $pb.ProtobufEnum {
  static const PatternMatch MATCHES = PatternMatch._(1, 'MATCHES');
  static const PatternMatch DOES_NOT_MATCH = PatternMatch._(2, 'DOES_NOT_MATCH');

  static const $core.List<PatternMatch> values = <PatternMatch> [
    MATCHES,
    DOES_NOT_MATCH,
  ];

  static final $core.Map<$core.int, PatternMatch> _byValue = $pb.ProtobufEnum.initByValue(values);
  static PatternMatch valueOf($core.int value) => _byValue[value];

  const PatternMatch._($core.int v, $core.String n) : super(v, n);
}

class PolicyRobotsTxt_Usage extends $pb.ProtobufEnum {
  static const PolicyRobotsTxt_Usage OBEY = PolicyRobotsTxt_Usage._(1, 'OBEY');
  static const PolicyRobotsTxt_Usage INVERT = PolicyRobotsTxt_Usage._(2, 'INVERT');
  static const PolicyRobotsTxt_Usage IGNORE = PolicyRobotsTxt_Usage._(3, 'IGNORE');

  static const $core.List<PolicyRobotsTxt_Usage> values = <PolicyRobotsTxt_Usage> [
    OBEY,
    INVERT,
    IGNORE,
  ];

  static final $core.Map<$core.int, PolicyRobotsTxt_Usage> _byValue = $pb.ProtobufEnum.initByValue(values);
  static PolicyRobotsTxt_Usage valueOf($core.int value) => _byValue[value];

  const PolicyRobotsTxt_Usage._($core.int v, $core.String n) : super(v, n);
}

class PolicyUrlRule_Action extends $pb.ProtobufEnum {
  static const PolicyUrlRule_Action ADD = PolicyUrlRule_Action._(1, 'ADD');
  static const PolicyUrlRule_Action MULTIPLY = PolicyUrlRule_Action._(2, 'MULTIPLY');

  static const $core.List<PolicyUrlRule_Action> values = <PolicyUrlRule_Action> [
    ADD,
    MULTIPLY,
  ];

  static final $core.Map<$core.int, PolicyUrlRule_Action> _byValue = $pb.ProtobufEnum.initByValue(values);
  static PolicyUrlRule_Action valueOf($core.int value) => _byValue[value];

  const PolicyUrlRule_Action._($core.int v, $core.String n) : super(v, n);
}

class SubscriptionClosed_Reason extends $pb.ProtobufEnum {
  static const SubscriptionClosed_Reason COMPLETE = SubscriptionClosed_Reason._(1, 'COMPLETE');
  static const SubscriptionClosed_Reason ERROR = SubscriptionClosed_Reason._(2, 'ERROR');

  static const $core.List<SubscriptionClosed_Reason> values = <SubscriptionClosed_Reason> [
    COMPLETE,
    ERROR,
  ];

  static final $core.Map<$core.int, SubscriptionClosed_Reason> _byValue = $pb.ProtobufEnum.initByValue(values);
  static SubscriptionClosed_Reason valueOf($core.int value) => _byValue[value];

  const SubscriptionClosed_Reason._($core.int v, $core.String n) : super(v, n);
}

