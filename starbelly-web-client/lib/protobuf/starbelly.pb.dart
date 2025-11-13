///
//  Generated code. Do not modify.
//  source: starbelly.proto
///
// ignore_for_file: camel_case_types,non_constant_identifier_names,library_prefixes,unused_import,unused_shown_name

import 'dart:core' as $core show bool, Deprecated, double, int, List, Map, override, String;

import 'package:fixnum/fixnum.dart';
import 'package:protobuf/protobuf.dart' as $pb;

import 'starbelly.pbenum.dart';

export 'starbelly.pbenum.dart';

enum CaptchaSolver_SolverType {
  antigate, 
  notSet
}

class CaptchaSolver extends $pb.GeneratedMessage {
  static const $core.Map<$core.int, CaptchaSolver_SolverType> _CaptchaSolver_SolverTypeByTag = {
    5 : CaptchaSolver_SolverType.antigate,
    0 : CaptchaSolver_SolverType.notSet
  };
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('CaptchaSolver')
    ..a<$core.List<$core.int>>(1, 'solverId', $pb.PbFieldType.OY)
    ..aOS(2, 'name')
    ..aOS(3, 'createdAt')
    ..aOS(4, 'updatedAt')
    ..a<CaptchaSolverAntigate>(5, 'antigate', $pb.PbFieldType.OM, CaptchaSolverAntigate.getDefault, CaptchaSolverAntigate.create)
    ..oo(0, [5])
    ..hasRequiredFields = false
  ;

  CaptchaSolver() : super();
  CaptchaSolver.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  CaptchaSolver.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  CaptchaSolver clone() => CaptchaSolver()..mergeFromMessage(this);
  CaptchaSolver copyWith(void Function(CaptchaSolver) updates) => super.copyWith((message) => updates(message as CaptchaSolver));
  $pb.BuilderInfo get info_ => _i;
  static CaptchaSolver create() => CaptchaSolver();
  CaptchaSolver createEmptyInstance() => create();
  static $pb.PbList<CaptchaSolver> createRepeated() => $pb.PbList<CaptchaSolver>();
  static CaptchaSolver getDefault() => _defaultInstance ??= create()..freeze();
  static CaptchaSolver _defaultInstance;

  CaptchaSolver_SolverType whichSolverType() => _CaptchaSolver_SolverTypeByTag[$_whichOneof(0)];
  void clearSolverType() => clearField($_whichOneof(0));

  $core.List<$core.int> get solverId => $_getN(0);
  set solverId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasSolverId() => $_has(0);
  void clearSolverId() => clearField(1);

  $core.String get name => $_getS(1, '');
  set name($core.String v) { $_setString(1, v); }
  $core.bool hasName() => $_has(1);
  void clearName() => clearField(2);

  $core.String get createdAt => $_getS(2, '');
  set createdAt($core.String v) { $_setString(2, v); }
  $core.bool hasCreatedAt() => $_has(2);
  void clearCreatedAt() => clearField(3);

  $core.String get updatedAt => $_getS(3, '');
  set updatedAt($core.String v) { $_setString(3, v); }
  $core.bool hasUpdatedAt() => $_has(3);
  void clearUpdatedAt() => clearField(4);

  CaptchaSolverAntigate get antigate => $_getN(4);
  set antigate(CaptchaSolverAntigate v) { setField(5, v); }
  $core.bool hasAntigate() => $_has(4);
  void clearAntigate() => clearField(5);
}

class CaptchaSolverAntigate extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('CaptchaSolverAntigate')
    ..aOS(1, 'serviceUrl')
    ..aOS(2, 'apiKey')
    ..aOB(3, 'requirePhrase')
    ..aOB(4, 'caseSensitive')
    ..e<CaptchaSolverAntigateCharacters>(5, 'characters', $pb.PbFieldType.OE, CaptchaSolverAntigateCharacters.ALPHANUMERIC, CaptchaSolverAntigateCharacters.valueOf, CaptchaSolverAntigateCharacters.values)
    ..aOB(6, 'requireMath')
    ..a<$core.int>(7, 'minLength', $pb.PbFieldType.O3)
    ..a<$core.int>(8, 'maxLength', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  CaptchaSolverAntigate() : super();
  CaptchaSolverAntigate.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  CaptchaSolverAntigate.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  CaptchaSolverAntigate clone() => CaptchaSolverAntigate()..mergeFromMessage(this);
  CaptchaSolverAntigate copyWith(void Function(CaptchaSolverAntigate) updates) => super.copyWith((message) => updates(message as CaptchaSolverAntigate));
  $pb.BuilderInfo get info_ => _i;
  static CaptchaSolverAntigate create() => CaptchaSolverAntigate();
  CaptchaSolverAntigate createEmptyInstance() => create();
  static $pb.PbList<CaptchaSolverAntigate> createRepeated() => $pb.PbList<CaptchaSolverAntigate>();
  static CaptchaSolverAntigate getDefault() => _defaultInstance ??= create()..freeze();
  static CaptchaSolverAntigate _defaultInstance;

  $core.String get serviceUrl => $_getS(0, '');
  set serviceUrl($core.String v) { $_setString(0, v); }
  $core.bool hasServiceUrl() => $_has(0);
  void clearServiceUrl() => clearField(1);

  $core.String get apiKey => $_getS(1, '');
  set apiKey($core.String v) { $_setString(1, v); }
  $core.bool hasApiKey() => $_has(1);
  void clearApiKey() => clearField(2);

  $core.bool get requirePhrase => $_get(2, false);
  set requirePhrase($core.bool v) { $_setBool(2, v); }
  $core.bool hasRequirePhrase() => $_has(2);
  void clearRequirePhrase() => clearField(3);

  $core.bool get caseSensitive => $_get(3, false);
  set caseSensitive($core.bool v) { $_setBool(3, v); }
  $core.bool hasCaseSensitive() => $_has(3);
  void clearCaseSensitive() => clearField(4);

  CaptchaSolverAntigateCharacters get characters => $_getN(4);
  set characters(CaptchaSolverAntigateCharacters v) { setField(5, v); }
  $core.bool hasCharacters() => $_has(4);
  void clearCharacters() => clearField(5);

  $core.bool get requireMath => $_get(5, false);
  set requireMath($core.bool v) { $_setBool(5, v); }
  $core.bool hasRequireMath() => $_has(5);
  void clearRequireMath() => clearField(6);

  $core.int get minLength => $_get(6, 0);
  set minLength($core.int v) { $_setSignedInt32(6, v); }
  $core.bool hasMinLength() => $_has(6);
  void clearMinLength() => clearField(7);

  $core.int get maxLength => $_get(7, 0);
  set maxLength($core.int v) { $_setSignedInt32(7, v); }
  $core.bool hasMaxLength() => $_has(7);
  void clearMaxLength() => clearField(8);
}

class CrawlResponse extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('CrawlResponse')
    ..a<$core.List<$core.int>>(1, 'body', $pb.PbFieldType.OY)
    ..aOS(2, 'completedAt')
    ..aOS(3, 'contentType')
    ..a<$core.double>(4, 'cost', $pb.PbFieldType.OD)
    ..a<$core.double>(5, 'duration', $pb.PbFieldType.OD)
    ..aOS(6, 'exception')
    ..pc<Header>(7, 'headers', $pb.PbFieldType.PM,Header.create)
    ..aOB(8, 'isCompressed')
    ..aOB(9, 'isSuccess')
    ..a<$core.List<$core.int>>(10, 'jobId', $pb.PbFieldType.OY)
    ..aOS(11, 'startedAt')
    ..a<$core.int>(12, 'statusCode', $pb.PbFieldType.O3)
    ..aOS(13, 'url')
    ..aOS(14, 'urlCan')
    ..hasRequiredFields = false
  ;

  CrawlResponse() : super();
  CrawlResponse.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  CrawlResponse.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  CrawlResponse clone() => CrawlResponse()..mergeFromMessage(this);
  CrawlResponse copyWith(void Function(CrawlResponse) updates) => super.copyWith((message) => updates(message as CrawlResponse));
  $pb.BuilderInfo get info_ => _i;
  static CrawlResponse create() => CrawlResponse();
  CrawlResponse createEmptyInstance() => create();
  static $pb.PbList<CrawlResponse> createRepeated() => $pb.PbList<CrawlResponse>();
  static CrawlResponse getDefault() => _defaultInstance ??= create()..freeze();
  static CrawlResponse _defaultInstance;

  $core.List<$core.int> get body => $_getN(0);
  set body($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasBody() => $_has(0);
  void clearBody() => clearField(1);

  $core.String get completedAt => $_getS(1, '');
  set completedAt($core.String v) { $_setString(1, v); }
  $core.bool hasCompletedAt() => $_has(1);
  void clearCompletedAt() => clearField(2);

  $core.String get contentType => $_getS(2, '');
  set contentType($core.String v) { $_setString(2, v); }
  $core.bool hasContentType() => $_has(2);
  void clearContentType() => clearField(3);

  $core.double get cost => $_getN(3);
  set cost($core.double v) { $_setDouble(3, v); }
  $core.bool hasCost() => $_has(3);
  void clearCost() => clearField(4);

  $core.double get duration => $_getN(4);
  set duration($core.double v) { $_setDouble(4, v); }
  $core.bool hasDuration() => $_has(4);
  void clearDuration() => clearField(5);

  $core.String get exception => $_getS(5, '');
  set exception($core.String v) { $_setString(5, v); }
  $core.bool hasException() => $_has(5);
  void clearException() => clearField(6);

  $core.List<Header> get headers => $_getList(6);

  $core.bool get isCompressed => $_get(7, false);
  set isCompressed($core.bool v) { $_setBool(7, v); }
  $core.bool hasIsCompressed() => $_has(7);
  void clearIsCompressed() => clearField(8);

  $core.bool get isSuccess => $_get(8, false);
  set isSuccess($core.bool v) { $_setBool(8, v); }
  $core.bool hasIsSuccess() => $_has(8);
  void clearIsSuccess() => clearField(9);

  $core.List<$core.int> get jobId => $_getN(9);
  set jobId($core.List<$core.int> v) { $_setBytes(9, v); }
  $core.bool hasJobId() => $_has(9);
  void clearJobId() => clearField(10);

  $core.String get startedAt => $_getS(10, '');
  set startedAt($core.String v) { $_setString(10, v); }
  $core.bool hasStartedAt() => $_has(10);
  void clearStartedAt() => clearField(11);

  $core.int get statusCode => $_get(11, 0);
  set statusCode($core.int v) { $_setSignedInt32(11, v); }
  $core.bool hasStatusCode() => $_has(11);
  void clearStatusCode() => clearField(12);

  $core.String get url => $_getS(12, '');
  set url($core.String v) { $_setString(12, v); }
  $core.bool hasUrl() => $_has(12);
  void clearUrl() => clearField(13);

  $core.String get urlCan => $_getS(13, '');
  set urlCan($core.String v) { $_setString(13, v); }
  $core.bool hasUrlCan() => $_has(13);
  void clearUrlCan() => clearField(14);
}

class Header extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('Header')
    ..aOS(1, 'key')
    ..aOS(2, 'value')
    ..hasRequiredFields = false
  ;

  Header() : super();
  Header.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  Header.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  Header clone() => Header()..mergeFromMessage(this);
  Header copyWith(void Function(Header) updates) => super.copyWith((message) => updates(message as Header));
  $pb.BuilderInfo get info_ => _i;
  static Header create() => Header();
  Header createEmptyInstance() => create();
  static $pb.PbList<Header> createRepeated() => $pb.PbList<Header>();
  static Header getDefault() => _defaultInstance ??= create()..freeze();
  static Header _defaultInstance;

  $core.String get key => $_getS(0, '');
  set key($core.String v) { $_setString(0, v); }
  $core.bool hasKey() => $_has(0);
  void clearKey() => clearField(1);

  $core.String get value => $_getS(1, '');
  set value($core.String v) { $_setString(1, v); }
  $core.bool hasValue() => $_has(1);
  void clearValue() => clearField(2);
}

class DomainLogin extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('DomainLogin')
    ..aOS(1, 'domain')
    ..aOS(2, 'loginUrl')
    ..aOS(3, 'loginTest')
    ..pc<DomainLoginUser>(5, 'users', $pb.PbFieldType.PM,DomainLoginUser.create)
    ..hasRequiredFields = false
  ;

  DomainLogin() : super();
  DomainLogin.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  DomainLogin.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  DomainLogin clone() => DomainLogin()..mergeFromMessage(this);
  DomainLogin copyWith(void Function(DomainLogin) updates) => super.copyWith((message) => updates(message as DomainLogin));
  $pb.BuilderInfo get info_ => _i;
  static DomainLogin create() => DomainLogin();
  DomainLogin createEmptyInstance() => create();
  static $pb.PbList<DomainLogin> createRepeated() => $pb.PbList<DomainLogin>();
  static DomainLogin getDefault() => _defaultInstance ??= create()..freeze();
  static DomainLogin _defaultInstance;

  $core.String get domain => $_getS(0, '');
  set domain($core.String v) { $_setString(0, v); }
  $core.bool hasDomain() => $_has(0);
  void clearDomain() => clearField(1);

  $core.String get loginUrl => $_getS(1, '');
  set loginUrl($core.String v) { $_setString(1, v); }
  $core.bool hasLoginUrl() => $_has(1);
  void clearLoginUrl() => clearField(2);

  $core.String get loginTest => $_getS(2, '');
  set loginTest($core.String v) { $_setString(2, v); }
  $core.bool hasLoginTest() => $_has(2);
  void clearLoginTest() => clearField(3);

  $core.List<DomainLoginUser> get users => $_getList(3);
}

class DomainLoginUser extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('DomainLoginUser')
    ..aOS(1, 'username')
    ..aOS(2, 'password')
    ..aOB(3, 'working')
    ..hasRequiredFields = false
  ;

  DomainLoginUser() : super();
  DomainLoginUser.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  DomainLoginUser.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  DomainLoginUser clone() => DomainLoginUser()..mergeFromMessage(this);
  DomainLoginUser copyWith(void Function(DomainLoginUser) updates) => super.copyWith((message) => updates(message as DomainLoginUser));
  $pb.BuilderInfo get info_ => _i;
  static DomainLoginUser create() => DomainLoginUser();
  DomainLoginUser createEmptyInstance() => create();
  static $pb.PbList<DomainLoginUser> createRepeated() => $pb.PbList<DomainLoginUser>();
  static DomainLoginUser getDefault() => _defaultInstance ??= create()..freeze();
  static DomainLoginUser _defaultInstance;

  $core.String get username => $_getS(0, '');
  set username($core.String v) { $_setString(0, v); }
  $core.bool hasUsername() => $_has(0);
  void clearUsername() => clearField(1);

  $core.String get password => $_getS(1, '');
  set password($core.String v) { $_setString(1, v); }
  $core.bool hasPassword() => $_has(1);
  void clearPassword() => clearField(2);

  $core.bool get working => $_get(2, false);
  set working($core.bool v) { $_setBool(2, v); }
  $core.bool hasWorking() => $_has(2);
  void clearWorking() => clearField(3);
}

enum Event_Body {
  jobList, 
  resourceFrame, 
  subscriptionClosed, 
  syncItem, 
  taskTree, 
  scheduleList, 
  notSet
}

class Event extends $pb.GeneratedMessage {
  static const $core.Map<$core.int, Event_Body> _Event_BodyByTag = {
    2 : Event_Body.jobList,
    3 : Event_Body.resourceFrame,
    4 : Event_Body.subscriptionClosed,
    5 : Event_Body.syncItem,
    6 : Event_Body.taskTree,
    7 : Event_Body.scheduleList,
    0 : Event_Body.notSet
  };
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('Event')
    ..a<$core.int>(1, 'subscriptionId', $pb.PbFieldType.Q3)
    ..a<JobList>(2, 'jobList', $pb.PbFieldType.OM, JobList.getDefault, JobList.create)
    ..a<ResourceFrame>(3, 'resourceFrame', $pb.PbFieldType.OM, ResourceFrame.getDefault, ResourceFrame.create)
    ..a<SubscriptionClosed>(4, 'subscriptionClosed', $pb.PbFieldType.OM, SubscriptionClosed.getDefault, SubscriptionClosed.create)
    ..a<SyncItem>(5, 'syncItem', $pb.PbFieldType.OM, SyncItem.getDefault, SyncItem.create)
    ..a<TaskTree>(6, 'taskTree', $pb.PbFieldType.OM, TaskTree.getDefault, TaskTree.create)
    ..a<ScheduleList>(7, 'scheduleList', $pb.PbFieldType.OM, ScheduleList.getDefault, ScheduleList.create)
    ..oo(0, [2, 3, 4, 5, 6, 7])
  ;

  Event() : super();
  Event.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  Event.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  Event clone() => Event()..mergeFromMessage(this);
  Event copyWith(void Function(Event) updates) => super.copyWith((message) => updates(message as Event));
  $pb.BuilderInfo get info_ => _i;
  static Event create() => Event();
  Event createEmptyInstance() => create();
  static $pb.PbList<Event> createRepeated() => $pb.PbList<Event>();
  static Event getDefault() => _defaultInstance ??= create()..freeze();
  static Event _defaultInstance;

  Event_Body whichBody() => _Event_BodyByTag[$_whichOneof(0)];
  void clearBody() => clearField($_whichOneof(0));

  $core.int get subscriptionId => $_get(0, 0);
  set subscriptionId($core.int v) { $_setSignedInt32(0, v); }
  $core.bool hasSubscriptionId() => $_has(0);
  void clearSubscriptionId() => clearField(1);

  JobList get jobList => $_getN(1);
  set jobList(JobList v) { setField(2, v); }
  $core.bool hasJobList() => $_has(1);
  void clearJobList() => clearField(2);

  ResourceFrame get resourceFrame => $_getN(2);
  set resourceFrame(ResourceFrame v) { setField(3, v); }
  $core.bool hasResourceFrame() => $_has(2);
  void clearResourceFrame() => clearField(3);

  SubscriptionClosed get subscriptionClosed => $_getN(3);
  set subscriptionClosed(SubscriptionClosed v) { setField(4, v); }
  $core.bool hasSubscriptionClosed() => $_has(3);
  void clearSubscriptionClosed() => clearField(4);

  SyncItem get syncItem => $_getN(4);
  set syncItem(SyncItem v) { setField(5, v); }
  $core.bool hasSyncItem() => $_has(4);
  void clearSyncItem() => clearField(5);

  TaskTree get taskTree => $_getN(5);
  set taskTree(TaskTree v) { setField(6, v); }
  $core.bool hasTaskTree() => $_has(5);
  void clearTaskTree() => clearField(6);

  ScheduleList get scheduleList => $_getN(6);
  set scheduleList(ScheduleList v) { setField(7, v); }
  $core.bool hasScheduleList() => $_has(6);
  void clearScheduleList() => clearField(7);
}

class Job extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('Job')
    ..a<$core.List<$core.int>>(1, 'jobId', $pb.PbFieldType.QY)
    ..pPS(2, 'seeds')
    ..a<Policy>(3, 'policy', $pb.PbFieldType.OM, Policy.getDefault, Policy.create)
    ..aOS(4, 'name')
    ..pPS(5, 'tags')
    ..e<JobRunState>(6, 'runState', $pb.PbFieldType.OE, JobRunState.CANCELLED, JobRunState.valueOf, JobRunState.values)
    ..aOS(7, 'startedAt')
    ..aOS(8, 'completedAt')
    ..a<$core.int>(9, 'itemCount', $pb.PbFieldType.O3, -1)
    ..a<$core.int>(10, 'httpSuccessCount', $pb.PbFieldType.O3, -1)
    ..a<$core.int>(11, 'httpErrorCount', $pb.PbFieldType.O3, -1)
    ..a<$core.int>(12, 'exceptionCount', $pb.PbFieldType.O3, -1)
    ..m<$core.int, $core.int>(13, 'httpStatusCounts', 'Job.HttpStatusCountsEntry',$pb.PbFieldType.O3, $pb.PbFieldType.O3, null, null, null )
  ;

  Job() : super();
  Job.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  Job.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  Job clone() => Job()..mergeFromMessage(this);
  Job copyWith(void Function(Job) updates) => super.copyWith((message) => updates(message as Job));
  $pb.BuilderInfo get info_ => _i;
  static Job create() => Job();
  Job createEmptyInstance() => create();
  static $pb.PbList<Job> createRepeated() => $pb.PbList<Job>();
  static Job getDefault() => _defaultInstance ??= create()..freeze();
  static Job _defaultInstance;

  $core.List<$core.int> get jobId => $_getN(0);
  set jobId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasJobId() => $_has(0);
  void clearJobId() => clearField(1);

  $core.List<$core.String> get seeds => $_getList(1);

  Policy get policy => $_getN(2);
  set policy(Policy v) { setField(3, v); }
  $core.bool hasPolicy() => $_has(2);
  void clearPolicy() => clearField(3);

  $core.String get name => $_getS(3, '');
  set name($core.String v) { $_setString(3, v); }
  $core.bool hasName() => $_has(3);
  void clearName() => clearField(4);

  $core.List<$core.String> get tags => $_getList(4);

  JobRunState get runState => $_getN(5);
  set runState(JobRunState v) { setField(6, v); }
  $core.bool hasRunState() => $_has(5);
  void clearRunState() => clearField(6);

  $core.String get startedAt => $_getS(6, '');
  set startedAt($core.String v) { $_setString(6, v); }
  $core.bool hasStartedAt() => $_has(6);
  void clearStartedAt() => clearField(7);

  $core.String get completedAt => $_getS(7, '');
  set completedAt($core.String v) { $_setString(7, v); }
  $core.bool hasCompletedAt() => $_has(7);
  void clearCompletedAt() => clearField(8);

  $core.int get itemCount => $_get(8, -1);
  set itemCount($core.int v) { $_setSignedInt32(8, v); }
  $core.bool hasItemCount() => $_has(8);
  void clearItemCount() => clearField(9);

  $core.int get httpSuccessCount => $_get(9, -1);
  set httpSuccessCount($core.int v) { $_setSignedInt32(9, v); }
  $core.bool hasHttpSuccessCount() => $_has(9);
  void clearHttpSuccessCount() => clearField(10);

  $core.int get httpErrorCount => $_get(10, -1);
  set httpErrorCount($core.int v) { $_setSignedInt32(10, v); }
  $core.bool hasHttpErrorCount() => $_has(10);
  void clearHttpErrorCount() => clearField(11);

  $core.int get exceptionCount => $_get(11, -1);
  set exceptionCount($core.int v) { $_setSignedInt32(11, v); }
  $core.bool hasExceptionCount() => $_has(11);
  void clearExceptionCount() => clearField(12);

  $core.Map<$core.int, $core.int> get httpStatusCounts => $_getMap(12);
}

class JobList extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('JobList')
    ..pc<Job>(1, 'jobs', $pb.PbFieldType.PM,Job.create)
  ;

  JobList() : super();
  JobList.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  JobList.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  JobList clone() => JobList()..mergeFromMessage(this);
  JobList copyWith(void Function(JobList) updates) => super.copyWith((message) => updates(message as JobList));
  $pb.BuilderInfo get info_ => _i;
  static JobList create() => JobList();
  JobList createEmptyInstance() => create();
  static $pb.PbList<JobList> createRepeated() => $pb.PbList<JobList>();
  static JobList getDefault() => _defaultInstance ??= create()..freeze();
  static JobList _defaultInstance;

  $core.List<Job> get jobs => $_getList(0);
}

class Schedule extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('Schedule')
    ..a<$core.List<$core.int>>(1, 'scheduleId', $pb.PbFieldType.OY)
    ..aOS(2, 'createdAt')
    ..aOS(3, 'updatedAt')
    ..aOB(4, 'enabled')
    ..e<ScheduleTimeUnit>(5, 'timeUnit', $pb.PbFieldType.OE, ScheduleTimeUnit.MINUTES, ScheduleTimeUnit.valueOf, ScheduleTimeUnit.values)
    ..a<$core.int>(6, 'numUnits', $pb.PbFieldType.O3)
    ..e<ScheduleTiming>(7, 'timing', $pb.PbFieldType.OE, ScheduleTiming.AFTER_PREVIOUS_JOB_FINISHED, ScheduleTiming.valueOf, ScheduleTiming.values)
    ..aOS(8, 'scheduleName')
    ..aOS(9, 'jobName')
    ..pPS(10, 'seeds')
    ..a<$core.List<$core.int>>(11, 'policyId', $pb.PbFieldType.OY)
    ..pPS(12, 'tags')
    ..a<$core.int>(13, 'jobCount', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  Schedule() : super();
  Schedule.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  Schedule.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  Schedule clone() => Schedule()..mergeFromMessage(this);
  Schedule copyWith(void Function(Schedule) updates) => super.copyWith((message) => updates(message as Schedule));
  $pb.BuilderInfo get info_ => _i;
  static Schedule create() => Schedule();
  Schedule createEmptyInstance() => create();
  static $pb.PbList<Schedule> createRepeated() => $pb.PbList<Schedule>();
  static Schedule getDefault() => _defaultInstance ??= create()..freeze();
  static Schedule _defaultInstance;

  $core.List<$core.int> get scheduleId => $_getN(0);
  set scheduleId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasScheduleId() => $_has(0);
  void clearScheduleId() => clearField(1);

  $core.String get createdAt => $_getS(1, '');
  set createdAt($core.String v) { $_setString(1, v); }
  $core.bool hasCreatedAt() => $_has(1);
  void clearCreatedAt() => clearField(2);

  $core.String get updatedAt => $_getS(2, '');
  set updatedAt($core.String v) { $_setString(2, v); }
  $core.bool hasUpdatedAt() => $_has(2);
  void clearUpdatedAt() => clearField(3);

  $core.bool get enabled => $_get(3, false);
  set enabled($core.bool v) { $_setBool(3, v); }
  $core.bool hasEnabled() => $_has(3);
  void clearEnabled() => clearField(4);

  ScheduleTimeUnit get timeUnit => $_getN(4);
  set timeUnit(ScheduleTimeUnit v) { setField(5, v); }
  $core.bool hasTimeUnit() => $_has(4);
  void clearTimeUnit() => clearField(5);

  $core.int get numUnits => $_get(5, 0);
  set numUnits($core.int v) { $_setSignedInt32(5, v); }
  $core.bool hasNumUnits() => $_has(5);
  void clearNumUnits() => clearField(6);

  ScheduleTiming get timing => $_getN(6);
  set timing(ScheduleTiming v) { setField(7, v); }
  $core.bool hasTiming() => $_has(6);
  void clearTiming() => clearField(7);

  $core.String get scheduleName => $_getS(7, '');
  set scheduleName($core.String v) { $_setString(7, v); }
  $core.bool hasScheduleName() => $_has(7);
  void clearScheduleName() => clearField(8);

  $core.String get jobName => $_getS(8, '');
  set jobName($core.String v) { $_setString(8, v); }
  $core.bool hasJobName() => $_has(8);
  void clearJobName() => clearField(9);

  $core.List<$core.String> get seeds => $_getList(9);

  $core.List<$core.int> get policyId => $_getN(10);
  set policyId($core.List<$core.int> v) { $_setBytes(10, v); }
  $core.bool hasPolicyId() => $_has(10);
  void clearPolicyId() => clearField(11);

  $core.List<$core.String> get tags => $_getList(11);

  $core.int get jobCount => $_get(12, 0);
  set jobCount($core.int v) { $_setSignedInt32(12, v); }
  $core.bool hasJobCount() => $_has(12);
  void clearJobCount() => clearField(13);
}

class ScheduleList extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ScheduleList')
    ..pc<Schedule>(1, 'schedules', $pb.PbFieldType.PM,Schedule.create)
    ..hasRequiredFields = false
  ;

  ScheduleList() : super();
  ScheduleList.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ScheduleList.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ScheduleList clone() => ScheduleList()..mergeFromMessage(this);
  ScheduleList copyWith(void Function(ScheduleList) updates) => super.copyWith((message) => updates(message as ScheduleList));
  $pb.BuilderInfo get info_ => _i;
  static ScheduleList create() => ScheduleList();
  ScheduleList createEmptyInstance() => create();
  static $pb.PbList<ScheduleList> createRepeated() => $pb.PbList<ScheduleList>();
  static ScheduleList getDefault() => _defaultInstance ??= create()..freeze();
  static ScheduleList _defaultInstance;

  $core.List<Schedule> get schedules => $_getList(0);
}

class Page extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('Page')
    ..a<$core.int>(1, 'limit', $pb.PbFieldType.O3, 10)
    ..a<$core.int>(2, 'offset', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  Page() : super();
  Page.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  Page.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  Page clone() => Page()..mergeFromMessage(this);
  Page copyWith(void Function(Page) updates) => super.copyWith((message) => updates(message as Page));
  $pb.BuilderInfo get info_ => _i;
  static Page create() => Page();
  Page createEmptyInstance() => create();
  static $pb.PbList<Page> createRepeated() => $pb.PbList<Page>();
  static Page getDefault() => _defaultInstance ??= create()..freeze();
  static Page _defaultInstance;

  $core.int get limit => $_get(0, 10);
  set limit($core.int v) { $_setSignedInt32(0, v); }
  $core.bool hasLimit() => $_has(0);
  void clearLimit() => clearField(1);

  $core.int get offset => $_get(1, 0);
  set offset($core.int v) { $_setSignedInt32(1, v); }
  $core.bool hasOffset() => $_has(1);
  void clearOffset() => clearField(2);
}

class Policy extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('Policy')
    ..a<$core.List<$core.int>>(1, 'policyId', $pb.PbFieldType.OY)
    ..aOS(2, 'name')
    ..aOS(3, 'createdAt')
    ..aOS(4, 'updatedAt')
    ..a<PolicyAuthentication>(6, 'authentication', $pb.PbFieldType.OM, PolicyAuthentication.getDefault, PolicyAuthentication.create)
    ..a<PolicyLimits>(7, 'limits', $pb.PbFieldType.OM, PolicyLimits.getDefault, PolicyLimits.create)
    ..pc<PolicyProxyRule>(8, 'proxyRules', $pb.PbFieldType.PM,PolicyProxyRule.create)
    ..pc<PolicyMimeTypeRule>(9, 'mimeTypeRules', $pb.PbFieldType.PM,PolicyMimeTypeRule.create)
    ..a<PolicyRobotsTxt>(10, 'robotsTxt', $pb.PbFieldType.OM, PolicyRobotsTxt.getDefault, PolicyRobotsTxt.create)
    ..pc<PolicyUrlRule>(11, 'urlRules', $pb.PbFieldType.PM,PolicyUrlRule.create)
    ..pc<PolicyUserAgent>(12, 'userAgents', $pb.PbFieldType.PM,PolicyUserAgent.create)
    ..a<PolicyUrlNormalization>(13, 'urlNormalization', $pb.PbFieldType.OM, PolicyUrlNormalization.getDefault, PolicyUrlNormalization.create)
    ..a<$core.List<$core.int>>(14, 'captchaSolverId', $pb.PbFieldType.OY)
  ;

  Policy() : super();
  Policy.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  Policy.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  Policy clone() => Policy()..mergeFromMessage(this);
  Policy copyWith(void Function(Policy) updates) => super.copyWith((message) => updates(message as Policy));
  $pb.BuilderInfo get info_ => _i;
  static Policy create() => Policy();
  Policy createEmptyInstance() => create();
  static $pb.PbList<Policy> createRepeated() => $pb.PbList<Policy>();
  static Policy getDefault() => _defaultInstance ??= create()..freeze();
  static Policy _defaultInstance;

  $core.List<$core.int> get policyId => $_getN(0);
  set policyId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasPolicyId() => $_has(0);
  void clearPolicyId() => clearField(1);

  $core.String get name => $_getS(1, '');
  set name($core.String v) { $_setString(1, v); }
  $core.bool hasName() => $_has(1);
  void clearName() => clearField(2);

  $core.String get createdAt => $_getS(2, '');
  set createdAt($core.String v) { $_setString(2, v); }
  $core.bool hasCreatedAt() => $_has(2);
  void clearCreatedAt() => clearField(3);

  $core.String get updatedAt => $_getS(3, '');
  set updatedAt($core.String v) { $_setString(3, v); }
  $core.bool hasUpdatedAt() => $_has(3);
  void clearUpdatedAt() => clearField(4);

  PolicyAuthentication get authentication => $_getN(4);
  set authentication(PolicyAuthentication v) { setField(6, v); }
  $core.bool hasAuthentication() => $_has(4);
  void clearAuthentication() => clearField(6);

  PolicyLimits get limits => $_getN(5);
  set limits(PolicyLimits v) { setField(7, v); }
  $core.bool hasLimits() => $_has(5);
  void clearLimits() => clearField(7);

  $core.List<PolicyProxyRule> get proxyRules => $_getList(6);

  $core.List<PolicyMimeTypeRule> get mimeTypeRules => $_getList(7);

  PolicyRobotsTxt get robotsTxt => $_getN(8);
  set robotsTxt(PolicyRobotsTxt v) { setField(10, v); }
  $core.bool hasRobotsTxt() => $_has(8);
  void clearRobotsTxt() => clearField(10);

  $core.List<PolicyUrlRule> get urlRules => $_getList(9);

  $core.List<PolicyUserAgent> get userAgents => $_getList(10);

  PolicyUrlNormalization get urlNormalization => $_getN(11);
  set urlNormalization(PolicyUrlNormalization v) { setField(13, v); }
  $core.bool hasUrlNormalization() => $_has(11);
  void clearUrlNormalization() => clearField(13);

  $core.List<$core.int> get captchaSolverId => $_getN(12);
  set captchaSolverId($core.List<$core.int> v) { $_setBytes(12, v); }
  $core.bool hasCaptchaSolverId() => $_has(12);
  void clearCaptchaSolverId() => clearField(14);
}

class PolicyAuthentication extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('PolicyAuthentication')
    ..aOB(1, 'enabled')
    ..hasRequiredFields = false
  ;

  PolicyAuthentication() : super();
  PolicyAuthentication.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  PolicyAuthentication.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  PolicyAuthentication clone() => PolicyAuthentication()..mergeFromMessage(this);
  PolicyAuthentication copyWith(void Function(PolicyAuthentication) updates) => super.copyWith((message) => updates(message as PolicyAuthentication));
  $pb.BuilderInfo get info_ => _i;
  static PolicyAuthentication create() => PolicyAuthentication();
  PolicyAuthentication createEmptyInstance() => create();
  static $pb.PbList<PolicyAuthentication> createRepeated() => $pb.PbList<PolicyAuthentication>();
  static PolicyAuthentication getDefault() => _defaultInstance ??= create()..freeze();
  static PolicyAuthentication _defaultInstance;

  $core.bool get enabled => $_get(0, false);
  set enabled($core.bool v) { $_setBool(0, v); }
  $core.bool hasEnabled() => $_has(0);
  void clearEnabled() => clearField(1);
}

class PolicyLimits extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('PolicyLimits')
    ..a<$core.double>(1, 'maxCost', $pb.PbFieldType.OD)
    ..a<$core.double>(2, 'maxDuration', $pb.PbFieldType.OD)
    ..a<$core.int>(3, 'maxItems', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  PolicyLimits() : super();
  PolicyLimits.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  PolicyLimits.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  PolicyLimits clone() => PolicyLimits()..mergeFromMessage(this);
  PolicyLimits copyWith(void Function(PolicyLimits) updates) => super.copyWith((message) => updates(message as PolicyLimits));
  $pb.BuilderInfo get info_ => _i;
  static PolicyLimits create() => PolicyLimits();
  PolicyLimits createEmptyInstance() => create();
  static $pb.PbList<PolicyLimits> createRepeated() => $pb.PbList<PolicyLimits>();
  static PolicyLimits getDefault() => _defaultInstance ??= create()..freeze();
  static PolicyLimits _defaultInstance;

  $core.double get maxCost => $_getN(0);
  set maxCost($core.double v) { $_setDouble(0, v); }
  $core.bool hasMaxCost() => $_has(0);
  void clearMaxCost() => clearField(1);

  $core.double get maxDuration => $_getN(1);
  set maxDuration($core.double v) { $_setDouble(1, v); }
  $core.bool hasMaxDuration() => $_has(1);
  void clearMaxDuration() => clearField(2);

  $core.int get maxItems => $_get(2, 0);
  set maxItems($core.int v) { $_setSignedInt32(2, v); }
  $core.bool hasMaxItems() => $_has(2);
  void clearMaxItems() => clearField(3);
}

class PolicyMimeTypeRule extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('PolicyMimeTypeRule')
    ..aOS(1, 'pattern')
    ..e<PatternMatch>(2, 'match', $pb.PbFieldType.OE, PatternMatch.MATCHES, PatternMatch.valueOf, PatternMatch.values)
    ..aOB(3, 'save')
    ..hasRequiredFields = false
  ;

  PolicyMimeTypeRule() : super();
  PolicyMimeTypeRule.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  PolicyMimeTypeRule.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  PolicyMimeTypeRule clone() => PolicyMimeTypeRule()..mergeFromMessage(this);
  PolicyMimeTypeRule copyWith(void Function(PolicyMimeTypeRule) updates) => super.copyWith((message) => updates(message as PolicyMimeTypeRule));
  $pb.BuilderInfo get info_ => _i;
  static PolicyMimeTypeRule create() => PolicyMimeTypeRule();
  PolicyMimeTypeRule createEmptyInstance() => create();
  static $pb.PbList<PolicyMimeTypeRule> createRepeated() => $pb.PbList<PolicyMimeTypeRule>();
  static PolicyMimeTypeRule getDefault() => _defaultInstance ??= create()..freeze();
  static PolicyMimeTypeRule _defaultInstance;

  $core.String get pattern => $_getS(0, '');
  set pattern($core.String v) { $_setString(0, v); }
  $core.bool hasPattern() => $_has(0);
  void clearPattern() => clearField(1);

  PatternMatch get match => $_getN(1);
  set match(PatternMatch v) { setField(2, v); }
  $core.bool hasMatch() => $_has(1);
  void clearMatch() => clearField(2);

  $core.bool get save => $_get(2, false);
  set save($core.bool v) { $_setBool(2, v); }
  $core.bool hasSave() => $_has(2);
  void clearSave() => clearField(3);
}

class PolicyProxyRule extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('PolicyProxyRule')
    ..aOS(1, 'pattern')
    ..e<PatternMatch>(2, 'match', $pb.PbFieldType.OE, PatternMatch.MATCHES, PatternMatch.valueOf, PatternMatch.values)
    ..aOS(3, 'proxyUrl')
    ..hasRequiredFields = false
  ;

  PolicyProxyRule() : super();
  PolicyProxyRule.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  PolicyProxyRule.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  PolicyProxyRule clone() => PolicyProxyRule()..mergeFromMessage(this);
  PolicyProxyRule copyWith(void Function(PolicyProxyRule) updates) => super.copyWith((message) => updates(message as PolicyProxyRule));
  $pb.BuilderInfo get info_ => _i;
  static PolicyProxyRule create() => PolicyProxyRule();
  PolicyProxyRule createEmptyInstance() => create();
  static $pb.PbList<PolicyProxyRule> createRepeated() => $pb.PbList<PolicyProxyRule>();
  static PolicyProxyRule getDefault() => _defaultInstance ??= create()..freeze();
  static PolicyProxyRule _defaultInstance;

  $core.String get pattern => $_getS(0, '');
  set pattern($core.String v) { $_setString(0, v); }
  $core.bool hasPattern() => $_has(0);
  void clearPattern() => clearField(1);

  PatternMatch get match => $_getN(1);
  set match(PatternMatch v) { setField(2, v); }
  $core.bool hasMatch() => $_has(1);
  void clearMatch() => clearField(2);

  $core.String get proxyUrl => $_getS(2, '');
  set proxyUrl($core.String v) { $_setString(2, v); }
  $core.bool hasProxyUrl() => $_has(2);
  void clearProxyUrl() => clearField(3);
}

class PolicyRobotsTxt extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('PolicyRobotsTxt')
    ..e<PolicyRobotsTxt_Usage>(1, 'usage', $pb.PbFieldType.QE, PolicyRobotsTxt_Usage.OBEY, PolicyRobotsTxt_Usage.valueOf, PolicyRobotsTxt_Usage.values)
  ;

  PolicyRobotsTxt() : super();
  PolicyRobotsTxt.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  PolicyRobotsTxt.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  PolicyRobotsTxt clone() => PolicyRobotsTxt()..mergeFromMessage(this);
  PolicyRobotsTxt copyWith(void Function(PolicyRobotsTxt) updates) => super.copyWith((message) => updates(message as PolicyRobotsTxt));
  $pb.BuilderInfo get info_ => _i;
  static PolicyRobotsTxt create() => PolicyRobotsTxt();
  PolicyRobotsTxt createEmptyInstance() => create();
  static $pb.PbList<PolicyRobotsTxt> createRepeated() => $pb.PbList<PolicyRobotsTxt>();
  static PolicyRobotsTxt getDefault() => _defaultInstance ??= create()..freeze();
  static PolicyRobotsTxt _defaultInstance;

  PolicyRobotsTxt_Usage get usage => $_getN(0);
  set usage(PolicyRobotsTxt_Usage v) { setField(1, v); }
  $core.bool hasUsage() => $_has(0);
  void clearUsage() => clearField(1);
}

class PolicyUrlNormalization extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('PolicyUrlNormalization')
    ..aOB(1, 'enabled')
    ..pPS(2, 'stripParameters')
    ..hasRequiredFields = false
  ;

  PolicyUrlNormalization() : super();
  PolicyUrlNormalization.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  PolicyUrlNormalization.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  PolicyUrlNormalization clone() => PolicyUrlNormalization()..mergeFromMessage(this);
  PolicyUrlNormalization copyWith(void Function(PolicyUrlNormalization) updates) => super.copyWith((message) => updates(message as PolicyUrlNormalization));
  $pb.BuilderInfo get info_ => _i;
  static PolicyUrlNormalization create() => PolicyUrlNormalization();
  PolicyUrlNormalization createEmptyInstance() => create();
  static $pb.PbList<PolicyUrlNormalization> createRepeated() => $pb.PbList<PolicyUrlNormalization>();
  static PolicyUrlNormalization getDefault() => _defaultInstance ??= create()..freeze();
  static PolicyUrlNormalization _defaultInstance;

  $core.bool get enabled => $_get(0, false);
  set enabled($core.bool v) { $_setBool(0, v); }
  $core.bool hasEnabled() => $_has(0);
  void clearEnabled() => clearField(1);

  $core.List<$core.String> get stripParameters => $_getList(1);
}

class PolicyUrlRule extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('PolicyUrlRule')
    ..aOS(1, 'pattern')
    ..e<PatternMatch>(2, 'match', $pb.PbFieldType.OE, PatternMatch.MATCHES, PatternMatch.valueOf, PatternMatch.values)
    ..e<PolicyUrlRule_Action>(3, 'action', $pb.PbFieldType.OE, PolicyUrlRule_Action.ADD, PolicyUrlRule_Action.valueOf, PolicyUrlRule_Action.values)
    ..a<$core.double>(4, 'amount', $pb.PbFieldType.OD)
    ..hasRequiredFields = false
  ;

  PolicyUrlRule() : super();
  PolicyUrlRule.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  PolicyUrlRule.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  PolicyUrlRule clone() => PolicyUrlRule()..mergeFromMessage(this);
  PolicyUrlRule copyWith(void Function(PolicyUrlRule) updates) => super.copyWith((message) => updates(message as PolicyUrlRule));
  $pb.BuilderInfo get info_ => _i;
  static PolicyUrlRule create() => PolicyUrlRule();
  PolicyUrlRule createEmptyInstance() => create();
  static $pb.PbList<PolicyUrlRule> createRepeated() => $pb.PbList<PolicyUrlRule>();
  static PolicyUrlRule getDefault() => _defaultInstance ??= create()..freeze();
  static PolicyUrlRule _defaultInstance;

  $core.String get pattern => $_getS(0, '');
  set pattern($core.String v) { $_setString(0, v); }
  $core.bool hasPattern() => $_has(0);
  void clearPattern() => clearField(1);

  PatternMatch get match => $_getN(1);
  set match(PatternMatch v) { setField(2, v); }
  $core.bool hasMatch() => $_has(1);
  void clearMatch() => clearField(2);

  PolicyUrlRule_Action get action => $_getN(2);
  set action(PolicyUrlRule_Action v) { setField(3, v); }
  $core.bool hasAction() => $_has(2);
  void clearAction() => clearField(3);

  $core.double get amount => $_getN(3);
  set amount($core.double v) { $_setDouble(3, v); }
  $core.bool hasAmount() => $_has(3);
  void clearAmount() => clearField(4);
}

class PolicyUserAgent extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('PolicyUserAgent')
    ..aQS(1, 'name')
  ;

  PolicyUserAgent() : super();
  PolicyUserAgent.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  PolicyUserAgent.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  PolicyUserAgent clone() => PolicyUserAgent()..mergeFromMessage(this);
  PolicyUserAgent copyWith(void Function(PolicyUserAgent) updates) => super.copyWith((message) => updates(message as PolicyUserAgent));
  $pb.BuilderInfo get info_ => _i;
  static PolicyUserAgent create() => PolicyUserAgent();
  PolicyUserAgent createEmptyInstance() => create();
  static $pb.PbList<PolicyUserAgent> createRepeated() => $pb.PbList<PolicyUserAgent>();
  static PolicyUserAgent getDefault() => _defaultInstance ??= create()..freeze();
  static PolicyUserAgent _defaultInstance;

  $core.String get name => $_getS(0, '');
  set name($core.String v) { $_setString(0, v); }
  $core.bool hasName() => $_has(0);
  void clearName() => clearField(1);
}

enum Request_Command {
  deleteDomainLogin, 
  deleteJob, 
  deletePolicy, 
  getDomainLogin, 
  getJob, 
  getJobItems, 
  getPolicy, 
  listRateLimits, 
  listDomainLogins, 
  listJobs, 
  listPolicies, 
  performanceProfile, 
  setDomainLogin, 
  setJob, 
  setPolicy, 
  setRateLimit, 
  subscribeJobStatus, 
  subscribeJobSync, 
  subscribeResourceMonitor, 
  subscribeTaskMonitor, 
  unsubscribe, 
  deleteSchedule, 
  getSchedule, 
  listSchedules, 
  setSchedule, 
  getCaptchaSolver, 
  listCaptchaSolvers, 
  setCaptchaSolver, 
  deleteCaptchaSolver, 
  listScheduleJobs, 
  notSet
}

class Request extends $pb.GeneratedMessage {
  static const $core.Map<$core.int, Request_Command> _Request_CommandByTag = {
    2 : Request_Command.deleteDomainLogin,
    3 : Request_Command.deleteJob,
    4 : Request_Command.deletePolicy,
    5 : Request_Command.getDomainLogin,
    6 : Request_Command.getJob,
    7 : Request_Command.getJobItems,
    8 : Request_Command.getPolicy,
    9 : Request_Command.listRateLimits,
    10 : Request_Command.listDomainLogins,
    11 : Request_Command.listJobs,
    12 : Request_Command.listPolicies,
    13 : Request_Command.performanceProfile,
    15 : Request_Command.setDomainLogin,
    16 : Request_Command.setJob,
    17 : Request_Command.setPolicy,
    18 : Request_Command.setRateLimit,
    19 : Request_Command.subscribeJobStatus,
    20 : Request_Command.subscribeJobSync,
    21 : Request_Command.subscribeResourceMonitor,
    22 : Request_Command.subscribeTaskMonitor,
    23 : Request_Command.unsubscribe,
    24 : Request_Command.deleteSchedule,
    25 : Request_Command.getSchedule,
    26 : Request_Command.listSchedules,
    27 : Request_Command.setSchedule,
    28 : Request_Command.getCaptchaSolver,
    29 : Request_Command.listCaptchaSolvers,
    30 : Request_Command.setCaptchaSolver,
    31 : Request_Command.deleteCaptchaSolver,
    32 : Request_Command.listScheduleJobs,
    0 : Request_Command.notSet
  };
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('Request')
    ..a<$core.int>(1, 'requestId', $pb.PbFieldType.Q3)
    ..a<RequestDeleteDomainLogin>(2, 'deleteDomainLogin', $pb.PbFieldType.OM, RequestDeleteDomainLogin.getDefault, RequestDeleteDomainLogin.create)
    ..a<RequestDeleteJob>(3, 'deleteJob', $pb.PbFieldType.OM, RequestDeleteJob.getDefault, RequestDeleteJob.create)
    ..a<RequestDeletePolicy>(4, 'deletePolicy', $pb.PbFieldType.OM, RequestDeletePolicy.getDefault, RequestDeletePolicy.create)
    ..a<RequestGetDomainLogin>(5, 'getDomainLogin', $pb.PbFieldType.OM, RequestGetDomainLogin.getDefault, RequestGetDomainLogin.create)
    ..a<RequestGetJob>(6, 'getJob', $pb.PbFieldType.OM, RequestGetJob.getDefault, RequestGetJob.create)
    ..a<RequestGetJobItems>(7, 'getJobItems', $pb.PbFieldType.OM, RequestGetJobItems.getDefault, RequestGetJobItems.create)
    ..a<RequestGetPolicy>(8, 'getPolicy', $pb.PbFieldType.OM, RequestGetPolicy.getDefault, RequestGetPolicy.create)
    ..a<RequestListRateLimits>(9, 'listRateLimits', $pb.PbFieldType.OM, RequestListRateLimits.getDefault, RequestListRateLimits.create)
    ..a<RequestListDomainLogins>(10, 'listDomainLogins', $pb.PbFieldType.OM, RequestListDomainLogins.getDefault, RequestListDomainLogins.create)
    ..a<RequestListJobs>(11, 'listJobs', $pb.PbFieldType.OM, RequestListJobs.getDefault, RequestListJobs.create)
    ..a<RequestListPolicies>(12, 'listPolicies', $pb.PbFieldType.OM, RequestListPolicies.getDefault, RequestListPolicies.create)
    ..a<RequestPerformanceProfile>(13, 'performanceProfile', $pb.PbFieldType.OM, RequestPerformanceProfile.getDefault, RequestPerformanceProfile.create)
    ..a<RequestSetDomainLogin>(15, 'setDomainLogin', $pb.PbFieldType.OM, RequestSetDomainLogin.getDefault, RequestSetDomainLogin.create)
    ..a<RequestSetJob>(16, 'setJob', $pb.PbFieldType.OM, RequestSetJob.getDefault, RequestSetJob.create)
    ..a<RequestSetPolicy>(17, 'setPolicy', $pb.PbFieldType.OM, RequestSetPolicy.getDefault, RequestSetPolicy.create)
    ..a<RequestSetRateLimit>(18, 'setRateLimit', $pb.PbFieldType.OM, RequestSetRateLimit.getDefault, RequestSetRateLimit.create)
    ..a<RequestSubscribeJobStatus>(19, 'subscribeJobStatus', $pb.PbFieldType.OM, RequestSubscribeJobStatus.getDefault, RequestSubscribeJobStatus.create)
    ..a<RequestSubscribeJobSync>(20, 'subscribeJobSync', $pb.PbFieldType.OM, RequestSubscribeJobSync.getDefault, RequestSubscribeJobSync.create)
    ..a<RequestSubscribeResourceMonitor>(21, 'subscribeResourceMonitor', $pb.PbFieldType.OM, RequestSubscribeResourceMonitor.getDefault, RequestSubscribeResourceMonitor.create)
    ..a<RequestSubscribeTaskMonitor>(22, 'subscribeTaskMonitor', $pb.PbFieldType.OM, RequestSubscribeTaskMonitor.getDefault, RequestSubscribeTaskMonitor.create)
    ..a<RequestUnsubscribe>(23, 'unsubscribe', $pb.PbFieldType.OM, RequestUnsubscribe.getDefault, RequestUnsubscribe.create)
    ..a<RequestDeleteSchedule>(24, 'deleteSchedule', $pb.PbFieldType.OM, RequestDeleteSchedule.getDefault, RequestDeleteSchedule.create)
    ..a<RequestGetSchedule>(25, 'getSchedule', $pb.PbFieldType.OM, RequestGetSchedule.getDefault, RequestGetSchedule.create)
    ..a<RequestListSchedules>(26, 'listSchedules', $pb.PbFieldType.OM, RequestListSchedules.getDefault, RequestListSchedules.create)
    ..a<RequestSetSchedule>(27, 'setSchedule', $pb.PbFieldType.OM, RequestSetSchedule.getDefault, RequestSetSchedule.create)
    ..a<RequestGetCaptchaSolver>(28, 'getCaptchaSolver', $pb.PbFieldType.OM, RequestGetCaptchaSolver.getDefault, RequestGetCaptchaSolver.create)
    ..a<RequestListCaptchaSolvers>(29, 'listCaptchaSolvers', $pb.PbFieldType.OM, RequestListCaptchaSolvers.getDefault, RequestListCaptchaSolvers.create)
    ..a<RequestSetCaptchaSolver>(30, 'setCaptchaSolver', $pb.PbFieldType.OM, RequestSetCaptchaSolver.getDefault, RequestSetCaptchaSolver.create)
    ..a<RequestDeleteCaptchaSolver>(31, 'deleteCaptchaSolver', $pb.PbFieldType.OM, RequestDeleteCaptchaSolver.getDefault, RequestDeleteCaptchaSolver.create)
    ..a<RequestListScheduleJobs>(32, 'listScheduleJobs', $pb.PbFieldType.OM, RequestListScheduleJobs.getDefault, RequestListScheduleJobs.create)
    ..oo(0, [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32])
  ;

  Request() : super();
  Request.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  Request.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  Request clone() => Request()..mergeFromMessage(this);
  Request copyWith(void Function(Request) updates) => super.copyWith((message) => updates(message as Request));
  $pb.BuilderInfo get info_ => _i;
  static Request create() => Request();
  Request createEmptyInstance() => create();
  static $pb.PbList<Request> createRepeated() => $pb.PbList<Request>();
  static Request getDefault() => _defaultInstance ??= create()..freeze();
  static Request _defaultInstance;

  Request_Command whichCommand() => _Request_CommandByTag[$_whichOneof(0)];
  void clearCommand() => clearField($_whichOneof(0));

  $core.int get requestId => $_get(0, 0);
  set requestId($core.int v) { $_setSignedInt32(0, v); }
  $core.bool hasRequestId() => $_has(0);
  void clearRequestId() => clearField(1);

  RequestDeleteDomainLogin get deleteDomainLogin => $_getN(1);
  set deleteDomainLogin(RequestDeleteDomainLogin v) { setField(2, v); }
  $core.bool hasDeleteDomainLogin() => $_has(1);
  void clearDeleteDomainLogin() => clearField(2);

  RequestDeleteJob get deleteJob => $_getN(2);
  set deleteJob(RequestDeleteJob v) { setField(3, v); }
  $core.bool hasDeleteJob() => $_has(2);
  void clearDeleteJob() => clearField(3);

  RequestDeletePolicy get deletePolicy => $_getN(3);
  set deletePolicy(RequestDeletePolicy v) { setField(4, v); }
  $core.bool hasDeletePolicy() => $_has(3);
  void clearDeletePolicy() => clearField(4);

  RequestGetDomainLogin get getDomainLogin => $_getN(4);
  set getDomainLogin(RequestGetDomainLogin v) { setField(5, v); }
  $core.bool hasGetDomainLogin() => $_has(4);
  void clearGetDomainLogin() => clearField(5);

  RequestGetJob get getJob => $_getN(5);
  set getJob(RequestGetJob v) { setField(6, v); }
  $core.bool hasGetJob() => $_has(5);
  void clearGetJob() => clearField(6);

  RequestGetJobItems get getJobItems => $_getN(6);
  set getJobItems(RequestGetJobItems v) { setField(7, v); }
  $core.bool hasGetJobItems() => $_has(6);
  void clearGetJobItems() => clearField(7);

  RequestGetPolicy get getPolicy => $_getN(7);
  set getPolicy(RequestGetPolicy v) { setField(8, v); }
  $core.bool hasGetPolicy() => $_has(7);
  void clearGetPolicy() => clearField(8);

  RequestListRateLimits get listRateLimits => $_getN(8);
  set listRateLimits(RequestListRateLimits v) { setField(9, v); }
  $core.bool hasListRateLimits() => $_has(8);
  void clearListRateLimits() => clearField(9);

  RequestListDomainLogins get listDomainLogins => $_getN(9);
  set listDomainLogins(RequestListDomainLogins v) { setField(10, v); }
  $core.bool hasListDomainLogins() => $_has(9);
  void clearListDomainLogins() => clearField(10);

  RequestListJobs get listJobs => $_getN(10);
  set listJobs(RequestListJobs v) { setField(11, v); }
  $core.bool hasListJobs() => $_has(10);
  void clearListJobs() => clearField(11);

  RequestListPolicies get listPolicies => $_getN(11);
  set listPolicies(RequestListPolicies v) { setField(12, v); }
  $core.bool hasListPolicies() => $_has(11);
  void clearListPolicies() => clearField(12);

  RequestPerformanceProfile get performanceProfile => $_getN(12);
  set performanceProfile(RequestPerformanceProfile v) { setField(13, v); }
  $core.bool hasPerformanceProfile() => $_has(12);
  void clearPerformanceProfile() => clearField(13);

  RequestSetDomainLogin get setDomainLogin => $_getN(13);
  set setDomainLogin(RequestSetDomainLogin v) { setField(15, v); }
  $core.bool hasSetDomainLogin() => $_has(13);
  void clearSetDomainLogin() => clearField(15);

  RequestSetJob get setJob => $_getN(14);
  set setJob(RequestSetJob v) { setField(16, v); }
  $core.bool hasSetJob() => $_has(14);
  void clearSetJob() => clearField(16);

  RequestSetPolicy get setPolicy => $_getN(15);
  set setPolicy(RequestSetPolicy v) { setField(17, v); }
  $core.bool hasSetPolicy() => $_has(15);
  void clearSetPolicy() => clearField(17);

  RequestSetRateLimit get setRateLimit => $_getN(16);
  set setRateLimit(RequestSetRateLimit v) { setField(18, v); }
  $core.bool hasSetRateLimit() => $_has(16);
  void clearSetRateLimit() => clearField(18);

  RequestSubscribeJobStatus get subscribeJobStatus => $_getN(17);
  set subscribeJobStatus(RequestSubscribeJobStatus v) { setField(19, v); }
  $core.bool hasSubscribeJobStatus() => $_has(17);
  void clearSubscribeJobStatus() => clearField(19);

  RequestSubscribeJobSync get subscribeJobSync => $_getN(18);
  set subscribeJobSync(RequestSubscribeJobSync v) { setField(20, v); }
  $core.bool hasSubscribeJobSync() => $_has(18);
  void clearSubscribeJobSync() => clearField(20);

  RequestSubscribeResourceMonitor get subscribeResourceMonitor => $_getN(19);
  set subscribeResourceMonitor(RequestSubscribeResourceMonitor v) { setField(21, v); }
  $core.bool hasSubscribeResourceMonitor() => $_has(19);
  void clearSubscribeResourceMonitor() => clearField(21);

  RequestSubscribeTaskMonitor get subscribeTaskMonitor => $_getN(20);
  set subscribeTaskMonitor(RequestSubscribeTaskMonitor v) { setField(22, v); }
  $core.bool hasSubscribeTaskMonitor() => $_has(20);
  void clearSubscribeTaskMonitor() => clearField(22);

  RequestUnsubscribe get unsubscribe => $_getN(21);
  set unsubscribe(RequestUnsubscribe v) { setField(23, v); }
  $core.bool hasUnsubscribe() => $_has(21);
  void clearUnsubscribe() => clearField(23);

  RequestDeleteSchedule get deleteSchedule => $_getN(22);
  set deleteSchedule(RequestDeleteSchedule v) { setField(24, v); }
  $core.bool hasDeleteSchedule() => $_has(22);
  void clearDeleteSchedule() => clearField(24);

  RequestGetSchedule get getSchedule => $_getN(23);
  set getSchedule(RequestGetSchedule v) { setField(25, v); }
  $core.bool hasGetSchedule() => $_has(23);
  void clearGetSchedule() => clearField(25);

  RequestListSchedules get listSchedules => $_getN(24);
  set listSchedules(RequestListSchedules v) { setField(26, v); }
  $core.bool hasListSchedules() => $_has(24);
  void clearListSchedules() => clearField(26);

  RequestSetSchedule get setSchedule => $_getN(25);
  set setSchedule(RequestSetSchedule v) { setField(27, v); }
  $core.bool hasSetSchedule() => $_has(25);
  void clearSetSchedule() => clearField(27);

  RequestGetCaptchaSolver get getCaptchaSolver => $_getN(26);
  set getCaptchaSolver(RequestGetCaptchaSolver v) { setField(28, v); }
  $core.bool hasGetCaptchaSolver() => $_has(26);
  void clearGetCaptchaSolver() => clearField(28);

  RequestListCaptchaSolvers get listCaptchaSolvers => $_getN(27);
  set listCaptchaSolvers(RequestListCaptchaSolvers v) { setField(29, v); }
  $core.bool hasListCaptchaSolvers() => $_has(27);
  void clearListCaptchaSolvers() => clearField(29);

  RequestSetCaptchaSolver get setCaptchaSolver => $_getN(28);
  set setCaptchaSolver(RequestSetCaptchaSolver v) { setField(30, v); }
  $core.bool hasSetCaptchaSolver() => $_has(28);
  void clearSetCaptchaSolver() => clearField(30);

  RequestDeleteCaptchaSolver get deleteCaptchaSolver => $_getN(29);
  set deleteCaptchaSolver(RequestDeleteCaptchaSolver v) { setField(31, v); }
  $core.bool hasDeleteCaptchaSolver() => $_has(29);
  void clearDeleteCaptchaSolver() => clearField(31);

  RequestListScheduleJobs get listScheduleJobs => $_getN(30);
  set listScheduleJobs(RequestListScheduleJobs v) { setField(32, v); }
  $core.bool hasListScheduleJobs() => $_has(30);
  void clearListScheduleJobs() => clearField(32);
}

enum Response_Body {
  domainLogin, 
  domainLoginUser, 
  job, 
  policy, 
  listDomainLogins, 
  listItems, 
  listJobs, 
  listPolicies, 
  listRateLimits, 
  newJob, 
  newPolicy, 
  newSubscription, 
  performanceProfile, 
  schedule, 
  listSchedules, 
  newSchedule, 
  solver, 
  listCaptchaSolvers, 
  newSolver, 
  listScheduleJobs, 
  notSet
}

class Response extends $pb.GeneratedMessage {
  static const $core.Map<$core.int, Response_Body> _Response_BodyByTag = {
    5 : Response_Body.domainLogin,
    6 : Response_Body.domainLoginUser,
    7 : Response_Body.job,
    8 : Response_Body.policy,
    9 : Response_Body.listDomainLogins,
    10 : Response_Body.listItems,
    11 : Response_Body.listJobs,
    12 : Response_Body.listPolicies,
    13 : Response_Body.listRateLimits,
    14 : Response_Body.newJob,
    15 : Response_Body.newPolicy,
    16 : Response_Body.newSubscription,
    17 : Response_Body.performanceProfile,
    19 : Response_Body.schedule,
    20 : Response_Body.listSchedules,
    21 : Response_Body.newSchedule,
    22 : Response_Body.solver,
    23 : Response_Body.listCaptchaSolvers,
    24 : Response_Body.newSolver,
    25 : Response_Body.listScheduleJobs,
    0 : Response_Body.notSet
  };
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('Response')
    ..a<$core.int>(1, 'requestId', $pb.PbFieldType.Q3)
    ..a<$core.bool>(2, 'isSuccess', $pb.PbFieldType.QB)
    ..aOS(3, 'errorMessage')
    ..a<DomainLogin>(5, 'domainLogin', $pb.PbFieldType.OM, DomainLogin.getDefault, DomainLogin.create)
    ..a<DomainLoginUser>(6, 'domainLoginUser', $pb.PbFieldType.OM, DomainLoginUser.getDefault, DomainLoginUser.create)
    ..a<Job>(7, 'job', $pb.PbFieldType.OM, Job.getDefault, Job.create)
    ..a<Policy>(8, 'policy', $pb.PbFieldType.OM, Policy.getDefault, Policy.create)
    ..a<ResponseListDomainLogins>(9, 'listDomainLogins', $pb.PbFieldType.OM, ResponseListDomainLogins.getDefault, ResponseListDomainLogins.create)
    ..a<ResponseListItems>(10, 'listItems', $pb.PbFieldType.OM, ResponseListItems.getDefault, ResponseListItems.create)
    ..a<ResponseListJobs>(11, 'listJobs', $pb.PbFieldType.OM, ResponseListJobs.getDefault, ResponseListJobs.create)
    ..a<ResponseListPolicies>(12, 'listPolicies', $pb.PbFieldType.OM, ResponseListPolicies.getDefault, ResponseListPolicies.create)
    ..a<ResponseListRateLimits>(13, 'listRateLimits', $pb.PbFieldType.OM, ResponseListRateLimits.getDefault, ResponseListRateLimits.create)
    ..a<ResponseNewJob>(14, 'newJob', $pb.PbFieldType.OM, ResponseNewJob.getDefault, ResponseNewJob.create)
    ..a<ResponseNewPolicy>(15, 'newPolicy', $pb.PbFieldType.OM, ResponseNewPolicy.getDefault, ResponseNewPolicy.create)
    ..a<ResponseNewSubscription>(16, 'newSubscription', $pb.PbFieldType.OM, ResponseNewSubscription.getDefault, ResponseNewSubscription.create)
    ..a<ResponsePerformanceProfile>(17, 'performanceProfile', $pb.PbFieldType.OM, ResponsePerformanceProfile.getDefault, ResponsePerformanceProfile.create)
    ..a<Schedule>(19, 'schedule', $pb.PbFieldType.OM, Schedule.getDefault, Schedule.create)
    ..a<ResponseListSchedules>(20, 'listSchedules', $pb.PbFieldType.OM, ResponseListSchedules.getDefault, ResponseListSchedules.create)
    ..a<ResponseNewSchedule>(21, 'newSchedule', $pb.PbFieldType.OM, ResponseNewSchedule.getDefault, ResponseNewSchedule.create)
    ..a<CaptchaSolver>(22, 'solver', $pb.PbFieldType.OM, CaptchaSolver.getDefault, CaptchaSolver.create)
    ..a<ResponseListCaptchaSolvers>(23, 'listCaptchaSolvers', $pb.PbFieldType.OM, ResponseListCaptchaSolvers.getDefault, ResponseListCaptchaSolvers.create)
    ..a<ResponseNewCaptchaSolver>(24, 'newSolver', $pb.PbFieldType.OM, ResponseNewCaptchaSolver.getDefault, ResponseNewCaptchaSolver.create)
    ..a<ResponseListScheduleJobs>(25, 'listScheduleJobs', $pb.PbFieldType.OM, ResponseListScheduleJobs.getDefault, ResponseListScheduleJobs.create)
    ..oo(0, [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25])
  ;

  Response() : super();
  Response.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  Response.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  Response clone() => Response()..mergeFromMessage(this);
  Response copyWith(void Function(Response) updates) => super.copyWith((message) => updates(message as Response));
  $pb.BuilderInfo get info_ => _i;
  static Response create() => Response();
  Response createEmptyInstance() => create();
  static $pb.PbList<Response> createRepeated() => $pb.PbList<Response>();
  static Response getDefault() => _defaultInstance ??= create()..freeze();
  static Response _defaultInstance;

  Response_Body whichBody() => _Response_BodyByTag[$_whichOneof(0)];
  void clearBody() => clearField($_whichOneof(0));

  $core.int get requestId => $_get(0, 0);
  set requestId($core.int v) { $_setSignedInt32(0, v); }
  $core.bool hasRequestId() => $_has(0);
  void clearRequestId() => clearField(1);

  $core.bool get isSuccess => $_get(1, false);
  set isSuccess($core.bool v) { $_setBool(1, v); }
  $core.bool hasIsSuccess() => $_has(1);
  void clearIsSuccess() => clearField(2);

  $core.String get errorMessage => $_getS(2, '');
  set errorMessage($core.String v) { $_setString(2, v); }
  $core.bool hasErrorMessage() => $_has(2);
  void clearErrorMessage() => clearField(3);

  DomainLogin get domainLogin => $_getN(3);
  set domainLogin(DomainLogin v) { setField(5, v); }
  $core.bool hasDomainLogin() => $_has(3);
  void clearDomainLogin() => clearField(5);

  DomainLoginUser get domainLoginUser => $_getN(4);
  set domainLoginUser(DomainLoginUser v) { setField(6, v); }
  $core.bool hasDomainLoginUser() => $_has(4);
  void clearDomainLoginUser() => clearField(6);

  Job get job => $_getN(5);
  set job(Job v) { setField(7, v); }
  $core.bool hasJob() => $_has(5);
  void clearJob() => clearField(7);

  Policy get policy => $_getN(6);
  set policy(Policy v) { setField(8, v); }
  $core.bool hasPolicy() => $_has(6);
  void clearPolicy() => clearField(8);

  ResponseListDomainLogins get listDomainLogins => $_getN(7);
  set listDomainLogins(ResponseListDomainLogins v) { setField(9, v); }
  $core.bool hasListDomainLogins() => $_has(7);
  void clearListDomainLogins() => clearField(9);

  ResponseListItems get listItems => $_getN(8);
  set listItems(ResponseListItems v) { setField(10, v); }
  $core.bool hasListItems() => $_has(8);
  void clearListItems() => clearField(10);

  ResponseListJobs get listJobs => $_getN(9);
  set listJobs(ResponseListJobs v) { setField(11, v); }
  $core.bool hasListJobs() => $_has(9);
  void clearListJobs() => clearField(11);

  ResponseListPolicies get listPolicies => $_getN(10);
  set listPolicies(ResponseListPolicies v) { setField(12, v); }
  $core.bool hasListPolicies() => $_has(10);
  void clearListPolicies() => clearField(12);

  ResponseListRateLimits get listRateLimits => $_getN(11);
  set listRateLimits(ResponseListRateLimits v) { setField(13, v); }
  $core.bool hasListRateLimits() => $_has(11);
  void clearListRateLimits() => clearField(13);

  ResponseNewJob get newJob => $_getN(12);
  set newJob(ResponseNewJob v) { setField(14, v); }
  $core.bool hasNewJob() => $_has(12);
  void clearNewJob() => clearField(14);

  ResponseNewPolicy get newPolicy => $_getN(13);
  set newPolicy(ResponseNewPolicy v) { setField(15, v); }
  $core.bool hasNewPolicy() => $_has(13);
  void clearNewPolicy() => clearField(15);

  ResponseNewSubscription get newSubscription => $_getN(14);
  set newSubscription(ResponseNewSubscription v) { setField(16, v); }
  $core.bool hasNewSubscription() => $_has(14);
  void clearNewSubscription() => clearField(16);

  ResponsePerformanceProfile get performanceProfile => $_getN(15);
  set performanceProfile(ResponsePerformanceProfile v) { setField(17, v); }
  $core.bool hasPerformanceProfile() => $_has(15);
  void clearPerformanceProfile() => clearField(17);

  Schedule get schedule => $_getN(16);
  set schedule(Schedule v) { setField(19, v); }
  $core.bool hasSchedule() => $_has(16);
  void clearSchedule() => clearField(19);

  ResponseListSchedules get listSchedules => $_getN(17);
  set listSchedules(ResponseListSchedules v) { setField(20, v); }
  $core.bool hasListSchedules() => $_has(17);
  void clearListSchedules() => clearField(20);

  ResponseNewSchedule get newSchedule => $_getN(18);
  set newSchedule(ResponseNewSchedule v) { setField(21, v); }
  $core.bool hasNewSchedule() => $_has(18);
  void clearNewSchedule() => clearField(21);

  CaptchaSolver get solver => $_getN(19);
  set solver(CaptchaSolver v) { setField(22, v); }
  $core.bool hasSolver() => $_has(19);
  void clearSolver() => clearField(22);

  ResponseListCaptchaSolvers get listCaptchaSolvers => $_getN(20);
  set listCaptchaSolvers(ResponseListCaptchaSolvers v) { setField(23, v); }
  $core.bool hasListCaptchaSolvers() => $_has(20);
  void clearListCaptchaSolvers() => clearField(23);

  ResponseNewCaptchaSolver get newSolver => $_getN(21);
  set newSolver(ResponseNewCaptchaSolver v) { setField(24, v); }
  $core.bool hasNewSolver() => $_has(21);
  void clearNewSolver() => clearField(24);

  ResponseListScheduleJobs get listScheduleJobs => $_getN(22);
  set listScheduleJobs(ResponseListScheduleJobs v) { setField(25, v); }
  $core.bool hasListScheduleJobs() => $_has(22);
  void clearListScheduleJobs() => clearField(25);
}

class RequestDeleteCaptchaSolver extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestDeleteCaptchaSolver')
    ..a<$core.List<$core.int>>(1, 'solverId', $pb.PbFieldType.OY)
    ..hasRequiredFields = false
  ;

  RequestDeleteCaptchaSolver() : super();
  RequestDeleteCaptchaSolver.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestDeleteCaptchaSolver.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestDeleteCaptchaSolver clone() => RequestDeleteCaptchaSolver()..mergeFromMessage(this);
  RequestDeleteCaptchaSolver copyWith(void Function(RequestDeleteCaptchaSolver) updates) => super.copyWith((message) => updates(message as RequestDeleteCaptchaSolver));
  $pb.BuilderInfo get info_ => _i;
  static RequestDeleteCaptchaSolver create() => RequestDeleteCaptchaSolver();
  RequestDeleteCaptchaSolver createEmptyInstance() => create();
  static $pb.PbList<RequestDeleteCaptchaSolver> createRepeated() => $pb.PbList<RequestDeleteCaptchaSolver>();
  static RequestDeleteCaptchaSolver getDefault() => _defaultInstance ??= create()..freeze();
  static RequestDeleteCaptchaSolver _defaultInstance;

  $core.List<$core.int> get solverId => $_getN(0);
  set solverId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasSolverId() => $_has(0);
  void clearSolverId() => clearField(1);
}

class RequestGetCaptchaSolver extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestGetCaptchaSolver')
    ..a<$core.List<$core.int>>(1, 'solverId', $pb.PbFieldType.QY)
  ;

  RequestGetCaptchaSolver() : super();
  RequestGetCaptchaSolver.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestGetCaptchaSolver.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestGetCaptchaSolver clone() => RequestGetCaptchaSolver()..mergeFromMessage(this);
  RequestGetCaptchaSolver copyWith(void Function(RequestGetCaptchaSolver) updates) => super.copyWith((message) => updates(message as RequestGetCaptchaSolver));
  $pb.BuilderInfo get info_ => _i;
  static RequestGetCaptchaSolver create() => RequestGetCaptchaSolver();
  RequestGetCaptchaSolver createEmptyInstance() => create();
  static $pb.PbList<RequestGetCaptchaSolver> createRepeated() => $pb.PbList<RequestGetCaptchaSolver>();
  static RequestGetCaptchaSolver getDefault() => _defaultInstance ??= create()..freeze();
  static RequestGetCaptchaSolver _defaultInstance;

  $core.List<$core.int> get solverId => $_getN(0);
  set solverId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasSolverId() => $_has(0);
  void clearSolverId() => clearField(1);
}

class RequestListCaptchaSolvers extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestListCaptchaSolvers')
    ..a<Page>(1, 'page', $pb.PbFieldType.OM, Page.getDefault, Page.create)
    ..hasRequiredFields = false
  ;

  RequestListCaptchaSolvers() : super();
  RequestListCaptchaSolvers.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestListCaptchaSolvers.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestListCaptchaSolvers clone() => RequestListCaptchaSolvers()..mergeFromMessage(this);
  RequestListCaptchaSolvers copyWith(void Function(RequestListCaptchaSolvers) updates) => super.copyWith((message) => updates(message as RequestListCaptchaSolvers));
  $pb.BuilderInfo get info_ => _i;
  static RequestListCaptchaSolvers create() => RequestListCaptchaSolvers();
  RequestListCaptchaSolvers createEmptyInstance() => create();
  static $pb.PbList<RequestListCaptchaSolvers> createRepeated() => $pb.PbList<RequestListCaptchaSolvers>();
  static RequestListCaptchaSolvers getDefault() => _defaultInstance ??= create()..freeze();
  static RequestListCaptchaSolvers _defaultInstance;

  Page get page => $_getN(0);
  set page(Page v) { setField(1, v); }
  $core.bool hasPage() => $_has(0);
  void clearPage() => clearField(1);
}

class ResponseListCaptchaSolvers extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResponseListCaptchaSolvers')
    ..pc<CaptchaSolver>(1, 'solvers', $pb.PbFieldType.PM,CaptchaSolver.create)
    ..a<$core.int>(2, 'total', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  ResponseListCaptchaSolvers() : super();
  ResponseListCaptchaSolvers.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResponseListCaptchaSolvers.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResponseListCaptchaSolvers clone() => ResponseListCaptchaSolvers()..mergeFromMessage(this);
  ResponseListCaptchaSolvers copyWith(void Function(ResponseListCaptchaSolvers) updates) => super.copyWith((message) => updates(message as ResponseListCaptchaSolvers));
  $pb.BuilderInfo get info_ => _i;
  static ResponseListCaptchaSolvers create() => ResponseListCaptchaSolvers();
  ResponseListCaptchaSolvers createEmptyInstance() => create();
  static $pb.PbList<ResponseListCaptchaSolvers> createRepeated() => $pb.PbList<ResponseListCaptchaSolvers>();
  static ResponseListCaptchaSolvers getDefault() => _defaultInstance ??= create()..freeze();
  static ResponseListCaptchaSolvers _defaultInstance;

  $core.List<CaptchaSolver> get solvers => $_getList(0);

  $core.int get total => $_get(1, 0);
  set total($core.int v) { $_setSignedInt32(1, v); }
  $core.bool hasTotal() => $_has(1);
  void clearTotal() => clearField(2);
}

class RequestSetCaptchaSolver extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestSetCaptchaSolver')
    ..a<CaptchaSolver>(1, 'solver', $pb.PbFieldType.OM, CaptchaSolver.getDefault, CaptchaSolver.create)
    ..hasRequiredFields = false
  ;

  RequestSetCaptchaSolver() : super();
  RequestSetCaptchaSolver.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestSetCaptchaSolver.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestSetCaptchaSolver clone() => RequestSetCaptchaSolver()..mergeFromMessage(this);
  RequestSetCaptchaSolver copyWith(void Function(RequestSetCaptchaSolver) updates) => super.copyWith((message) => updates(message as RequestSetCaptchaSolver));
  $pb.BuilderInfo get info_ => _i;
  static RequestSetCaptchaSolver create() => RequestSetCaptchaSolver();
  RequestSetCaptchaSolver createEmptyInstance() => create();
  static $pb.PbList<RequestSetCaptchaSolver> createRepeated() => $pb.PbList<RequestSetCaptchaSolver>();
  static RequestSetCaptchaSolver getDefault() => _defaultInstance ??= create()..freeze();
  static RequestSetCaptchaSolver _defaultInstance;

  CaptchaSolver get solver => $_getN(0);
  set solver(CaptchaSolver v) { setField(1, v); }
  $core.bool hasSolver() => $_has(0);
  void clearSolver() => clearField(1);
}

class ResponseNewCaptchaSolver extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResponseNewCaptchaSolver')
    ..a<$core.List<$core.int>>(1, 'solverId', $pb.PbFieldType.QY)
  ;

  ResponseNewCaptchaSolver() : super();
  ResponseNewCaptchaSolver.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResponseNewCaptchaSolver.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResponseNewCaptchaSolver clone() => ResponseNewCaptchaSolver()..mergeFromMessage(this);
  ResponseNewCaptchaSolver copyWith(void Function(ResponseNewCaptchaSolver) updates) => super.copyWith((message) => updates(message as ResponseNewCaptchaSolver));
  $pb.BuilderInfo get info_ => _i;
  static ResponseNewCaptchaSolver create() => ResponseNewCaptchaSolver();
  ResponseNewCaptchaSolver createEmptyInstance() => create();
  static $pb.PbList<ResponseNewCaptchaSolver> createRepeated() => $pb.PbList<ResponseNewCaptchaSolver>();
  static ResponseNewCaptchaSolver getDefault() => _defaultInstance ??= create()..freeze();
  static ResponseNewCaptchaSolver _defaultInstance;

  $core.List<$core.int> get solverId => $_getN(0);
  set solverId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasSolverId() => $_has(0);
  void clearSolverId() => clearField(1);
}

class RequestDeleteDomainLogin extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestDeleteDomainLogin')
    ..aOS(1, 'domain')
    ..hasRequiredFields = false
  ;

  RequestDeleteDomainLogin() : super();
  RequestDeleteDomainLogin.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestDeleteDomainLogin.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestDeleteDomainLogin clone() => RequestDeleteDomainLogin()..mergeFromMessage(this);
  RequestDeleteDomainLogin copyWith(void Function(RequestDeleteDomainLogin) updates) => super.copyWith((message) => updates(message as RequestDeleteDomainLogin));
  $pb.BuilderInfo get info_ => _i;
  static RequestDeleteDomainLogin create() => RequestDeleteDomainLogin();
  RequestDeleteDomainLogin createEmptyInstance() => create();
  static $pb.PbList<RequestDeleteDomainLogin> createRepeated() => $pb.PbList<RequestDeleteDomainLogin>();
  static RequestDeleteDomainLogin getDefault() => _defaultInstance ??= create()..freeze();
  static RequestDeleteDomainLogin _defaultInstance;

  $core.String get domain => $_getS(0, '');
  set domain($core.String v) { $_setString(0, v); }
  $core.bool hasDomain() => $_has(0);
  void clearDomain() => clearField(1);
}

class RequestGetDomainLogin extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestGetDomainLogin')
    ..aQS(1, 'domain')
  ;

  RequestGetDomainLogin() : super();
  RequestGetDomainLogin.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestGetDomainLogin.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestGetDomainLogin clone() => RequestGetDomainLogin()..mergeFromMessage(this);
  RequestGetDomainLogin copyWith(void Function(RequestGetDomainLogin) updates) => super.copyWith((message) => updates(message as RequestGetDomainLogin));
  $pb.BuilderInfo get info_ => _i;
  static RequestGetDomainLogin create() => RequestGetDomainLogin();
  RequestGetDomainLogin createEmptyInstance() => create();
  static $pb.PbList<RequestGetDomainLogin> createRepeated() => $pb.PbList<RequestGetDomainLogin>();
  static RequestGetDomainLogin getDefault() => _defaultInstance ??= create()..freeze();
  static RequestGetDomainLogin _defaultInstance;

  $core.String get domain => $_getS(0, '');
  set domain($core.String v) { $_setString(0, v); }
  $core.bool hasDomain() => $_has(0);
  void clearDomain() => clearField(1);
}

class RequestListDomainLogins extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestListDomainLogins')
    ..a<Page>(1, 'page', $pb.PbFieldType.OM, Page.getDefault, Page.create)
    ..hasRequiredFields = false
  ;

  RequestListDomainLogins() : super();
  RequestListDomainLogins.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestListDomainLogins.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestListDomainLogins clone() => RequestListDomainLogins()..mergeFromMessage(this);
  RequestListDomainLogins copyWith(void Function(RequestListDomainLogins) updates) => super.copyWith((message) => updates(message as RequestListDomainLogins));
  $pb.BuilderInfo get info_ => _i;
  static RequestListDomainLogins create() => RequestListDomainLogins();
  RequestListDomainLogins createEmptyInstance() => create();
  static $pb.PbList<RequestListDomainLogins> createRepeated() => $pb.PbList<RequestListDomainLogins>();
  static RequestListDomainLogins getDefault() => _defaultInstance ??= create()..freeze();
  static RequestListDomainLogins _defaultInstance;

  Page get page => $_getN(0);
  set page(Page v) { setField(1, v); }
  $core.bool hasPage() => $_has(0);
  void clearPage() => clearField(1);
}

class ResponseListDomainLogins extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResponseListDomainLogins')
    ..pc<DomainLogin>(1, 'logins', $pb.PbFieldType.PM,DomainLogin.create)
    ..a<$core.int>(2, 'total', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  ResponseListDomainLogins() : super();
  ResponseListDomainLogins.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResponseListDomainLogins.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResponseListDomainLogins clone() => ResponseListDomainLogins()..mergeFromMessage(this);
  ResponseListDomainLogins copyWith(void Function(ResponseListDomainLogins) updates) => super.copyWith((message) => updates(message as ResponseListDomainLogins));
  $pb.BuilderInfo get info_ => _i;
  static ResponseListDomainLogins create() => ResponseListDomainLogins();
  ResponseListDomainLogins createEmptyInstance() => create();
  static $pb.PbList<ResponseListDomainLogins> createRepeated() => $pb.PbList<ResponseListDomainLogins>();
  static ResponseListDomainLogins getDefault() => _defaultInstance ??= create()..freeze();
  static ResponseListDomainLogins _defaultInstance;

  $core.List<DomainLogin> get logins => $_getList(0);

  $core.int get total => $_get(1, 0);
  set total($core.int v) { $_setSignedInt32(1, v); }
  $core.bool hasTotal() => $_has(1);
  void clearTotal() => clearField(2);
}

class RequestSetDomainLogin extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestSetDomainLogin')
    ..a<DomainLogin>(1, 'login', $pb.PbFieldType.OM, DomainLogin.getDefault, DomainLogin.create)
    ..hasRequiredFields = false
  ;

  RequestSetDomainLogin() : super();
  RequestSetDomainLogin.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestSetDomainLogin.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestSetDomainLogin clone() => RequestSetDomainLogin()..mergeFromMessage(this);
  RequestSetDomainLogin copyWith(void Function(RequestSetDomainLogin) updates) => super.copyWith((message) => updates(message as RequestSetDomainLogin));
  $pb.BuilderInfo get info_ => _i;
  static RequestSetDomainLogin create() => RequestSetDomainLogin();
  RequestSetDomainLogin createEmptyInstance() => create();
  static $pb.PbList<RequestSetDomainLogin> createRepeated() => $pb.PbList<RequestSetDomainLogin>();
  static RequestSetDomainLogin getDefault() => _defaultInstance ??= create()..freeze();
  static RequestSetDomainLogin _defaultInstance;

  DomainLogin get login => $_getN(0);
  set login(DomainLogin v) { setField(1, v); }
  $core.bool hasLogin() => $_has(0);
  void clearLogin() => clearField(1);
}

class RequestDeleteJob extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestDeleteJob')
    ..a<$core.List<$core.int>>(1, 'jobId', $pb.PbFieldType.QY)
  ;

  RequestDeleteJob() : super();
  RequestDeleteJob.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestDeleteJob.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestDeleteJob clone() => RequestDeleteJob()..mergeFromMessage(this);
  RequestDeleteJob copyWith(void Function(RequestDeleteJob) updates) => super.copyWith((message) => updates(message as RequestDeleteJob));
  $pb.BuilderInfo get info_ => _i;
  static RequestDeleteJob create() => RequestDeleteJob();
  RequestDeleteJob createEmptyInstance() => create();
  static $pb.PbList<RequestDeleteJob> createRepeated() => $pb.PbList<RequestDeleteJob>();
  static RequestDeleteJob getDefault() => _defaultInstance ??= create()..freeze();
  static RequestDeleteJob _defaultInstance;

  $core.List<$core.int> get jobId => $_getN(0);
  set jobId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasJobId() => $_has(0);
  void clearJobId() => clearField(1);
}

class RequestGetJob extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestGetJob')
    ..a<$core.List<$core.int>>(1, 'jobId', $pb.PbFieldType.QY)
  ;

  RequestGetJob() : super();
  RequestGetJob.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestGetJob.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestGetJob clone() => RequestGetJob()..mergeFromMessage(this);
  RequestGetJob copyWith(void Function(RequestGetJob) updates) => super.copyWith((message) => updates(message as RequestGetJob));
  $pb.BuilderInfo get info_ => _i;
  static RequestGetJob create() => RequestGetJob();
  RequestGetJob createEmptyInstance() => create();
  static $pb.PbList<RequestGetJob> createRepeated() => $pb.PbList<RequestGetJob>();
  static RequestGetJob getDefault() => _defaultInstance ??= create()..freeze();
  static RequestGetJob _defaultInstance;

  $core.List<$core.int> get jobId => $_getN(0);
  set jobId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasJobId() => $_has(0);
  void clearJobId() => clearField(1);
}

class RequestListJobs extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestListJobs')
    ..a<Page>(1, 'page', $pb.PbFieldType.OM, Page.getDefault, Page.create)
    ..aOS(2, 'startedAfter')
    ..aOS(3, 'tag')
    ..a<$core.List<$core.int>>(4, 'scheduleId', $pb.PbFieldType.OY)
    ..hasRequiredFields = false
  ;

  RequestListJobs() : super();
  RequestListJobs.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestListJobs.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestListJobs clone() => RequestListJobs()..mergeFromMessage(this);
  RequestListJobs copyWith(void Function(RequestListJobs) updates) => super.copyWith((message) => updates(message as RequestListJobs));
  $pb.BuilderInfo get info_ => _i;
  static RequestListJobs create() => RequestListJobs();
  RequestListJobs createEmptyInstance() => create();
  static $pb.PbList<RequestListJobs> createRepeated() => $pb.PbList<RequestListJobs>();
  static RequestListJobs getDefault() => _defaultInstance ??= create()..freeze();
  static RequestListJobs _defaultInstance;

  Page get page => $_getN(0);
  set page(Page v) { setField(1, v); }
  $core.bool hasPage() => $_has(0);
  void clearPage() => clearField(1);

  $core.String get startedAfter => $_getS(1, '');
  set startedAfter($core.String v) { $_setString(1, v); }
  $core.bool hasStartedAfter() => $_has(1);
  void clearStartedAfter() => clearField(2);

  $core.String get tag => $_getS(2, '');
  set tag($core.String v) { $_setString(2, v); }
  $core.bool hasTag() => $_has(2);
  void clearTag() => clearField(3);

  $core.List<$core.int> get scheduleId => $_getN(3);
  set scheduleId($core.List<$core.int> v) { $_setBytes(3, v); }
  $core.bool hasScheduleId() => $_has(3);
  void clearScheduleId() => clearField(4);
}

class ResponseListJobs extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResponseListJobs')
    ..pc<Job>(1, 'jobs', $pb.PbFieldType.PM,Job.create)
    ..a<$core.int>(2, 'total', $pb.PbFieldType.O3)
  ;

  ResponseListJobs() : super();
  ResponseListJobs.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResponseListJobs.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResponseListJobs clone() => ResponseListJobs()..mergeFromMessage(this);
  ResponseListJobs copyWith(void Function(ResponseListJobs) updates) => super.copyWith((message) => updates(message as ResponseListJobs));
  $pb.BuilderInfo get info_ => _i;
  static ResponseListJobs create() => ResponseListJobs();
  ResponseListJobs createEmptyInstance() => create();
  static $pb.PbList<ResponseListJobs> createRepeated() => $pb.PbList<ResponseListJobs>();
  static ResponseListJobs getDefault() => _defaultInstance ??= create()..freeze();
  static ResponseListJobs _defaultInstance;

  $core.List<Job> get jobs => $_getList(0);

  $core.int get total => $_get(1, 0);
  set total($core.int v) { $_setSignedInt32(1, v); }
  $core.bool hasTotal() => $_has(1);
  void clearTotal() => clearField(2);
}

class RequestSetJob extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestSetJob')
    ..a<$core.List<$core.int>>(1, 'jobId', $pb.PbFieldType.OY)
    ..e<JobRunState>(2, 'runState', $pb.PbFieldType.OE, JobRunState.CANCELLED, JobRunState.valueOf, JobRunState.values)
    ..a<$core.List<$core.int>>(3, 'policyId', $pb.PbFieldType.OY)
    ..pPS(4, 'seeds')
    ..aOS(5, 'name')
    ..pPS(6, 'tags')
    ..hasRequiredFields = false
  ;

  RequestSetJob() : super();
  RequestSetJob.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestSetJob.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestSetJob clone() => RequestSetJob()..mergeFromMessage(this);
  RequestSetJob copyWith(void Function(RequestSetJob) updates) => super.copyWith((message) => updates(message as RequestSetJob));
  $pb.BuilderInfo get info_ => _i;
  static RequestSetJob create() => RequestSetJob();
  RequestSetJob createEmptyInstance() => create();
  static $pb.PbList<RequestSetJob> createRepeated() => $pb.PbList<RequestSetJob>();
  static RequestSetJob getDefault() => _defaultInstance ??= create()..freeze();
  static RequestSetJob _defaultInstance;

  $core.List<$core.int> get jobId => $_getN(0);
  set jobId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasJobId() => $_has(0);
  void clearJobId() => clearField(1);

  JobRunState get runState => $_getN(1);
  set runState(JobRunState v) { setField(2, v); }
  $core.bool hasRunState() => $_has(1);
  void clearRunState() => clearField(2);

  $core.List<$core.int> get policyId => $_getN(2);
  set policyId($core.List<$core.int> v) { $_setBytes(2, v); }
  $core.bool hasPolicyId() => $_has(2);
  void clearPolicyId() => clearField(3);

  $core.List<$core.String> get seeds => $_getList(3);

  $core.String get name => $_getS(4, '');
  set name($core.String v) { $_setString(4, v); }
  $core.bool hasName() => $_has(4);
  void clearName() => clearField(5);

  $core.List<$core.String> get tags => $_getList(5);
}

class ResponseNewJob extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResponseNewJob')
    ..a<$core.List<$core.int>>(1, 'jobId', $pb.PbFieldType.QY)
  ;

  ResponseNewJob() : super();
  ResponseNewJob.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResponseNewJob.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResponseNewJob clone() => ResponseNewJob()..mergeFromMessage(this);
  ResponseNewJob copyWith(void Function(ResponseNewJob) updates) => super.copyWith((message) => updates(message as ResponseNewJob));
  $pb.BuilderInfo get info_ => _i;
  static ResponseNewJob create() => ResponseNewJob();
  ResponseNewJob createEmptyInstance() => create();
  static $pb.PbList<ResponseNewJob> createRepeated() => $pb.PbList<ResponseNewJob>();
  static ResponseNewJob getDefault() => _defaultInstance ??= create()..freeze();
  static ResponseNewJob _defaultInstance;

  $core.List<$core.int> get jobId => $_getN(0);
  set jobId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasJobId() => $_has(0);
  void clearJobId() => clearField(1);
}

class RequestGetJobItems extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestGetJobItems')
    ..a<$core.List<$core.int>>(1, 'jobId', $pb.PbFieldType.QY)
    ..aOB(2, 'includeSuccess')
    ..aOB(3, 'includeError')
    ..aOB(4, 'includeException')
    ..a<$core.bool>(5, 'compressionOk', $pb.PbFieldType.OB, true)
    ..a<Page>(6, 'page', $pb.PbFieldType.OM, Page.getDefault, Page.create)
  ;

  RequestGetJobItems() : super();
  RequestGetJobItems.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestGetJobItems.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestGetJobItems clone() => RequestGetJobItems()..mergeFromMessage(this);
  RequestGetJobItems copyWith(void Function(RequestGetJobItems) updates) => super.copyWith((message) => updates(message as RequestGetJobItems));
  $pb.BuilderInfo get info_ => _i;
  static RequestGetJobItems create() => RequestGetJobItems();
  RequestGetJobItems createEmptyInstance() => create();
  static $pb.PbList<RequestGetJobItems> createRepeated() => $pb.PbList<RequestGetJobItems>();
  static RequestGetJobItems getDefault() => _defaultInstance ??= create()..freeze();
  static RequestGetJobItems _defaultInstance;

  $core.List<$core.int> get jobId => $_getN(0);
  set jobId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasJobId() => $_has(0);
  void clearJobId() => clearField(1);

  $core.bool get includeSuccess => $_get(1, false);
  set includeSuccess($core.bool v) { $_setBool(1, v); }
  $core.bool hasIncludeSuccess() => $_has(1);
  void clearIncludeSuccess() => clearField(2);

  $core.bool get includeError => $_get(2, false);
  set includeError($core.bool v) { $_setBool(2, v); }
  $core.bool hasIncludeError() => $_has(2);
  void clearIncludeError() => clearField(3);

  $core.bool get includeException => $_get(3, false);
  set includeException($core.bool v) { $_setBool(3, v); }
  $core.bool hasIncludeException() => $_has(3);
  void clearIncludeException() => clearField(4);

  $core.bool get compressionOk => $_get(4, true);
  set compressionOk($core.bool v) { $_setBool(4, v); }
  $core.bool hasCompressionOk() => $_has(4);
  void clearCompressionOk() => clearField(5);

  Page get page => $_getN(5);
  set page(Page v) { setField(6, v); }
  $core.bool hasPage() => $_has(5);
  void clearPage() => clearField(6);
}

class ResponseListItems extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResponseListItems')
    ..pc<CrawlResponse>(1, 'items', $pb.PbFieldType.PM,CrawlResponse.create)
    ..a<$core.int>(2, 'total', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  ResponseListItems() : super();
  ResponseListItems.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResponseListItems.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResponseListItems clone() => ResponseListItems()..mergeFromMessage(this);
  ResponseListItems copyWith(void Function(ResponseListItems) updates) => super.copyWith((message) => updates(message as ResponseListItems));
  $pb.BuilderInfo get info_ => _i;
  static ResponseListItems create() => ResponseListItems();
  ResponseListItems createEmptyInstance() => create();
  static $pb.PbList<ResponseListItems> createRepeated() => $pb.PbList<ResponseListItems>();
  static ResponseListItems getDefault() => _defaultInstance ??= create()..freeze();
  static ResponseListItems _defaultInstance;

  $core.List<CrawlResponse> get items => $_getList(0);

  $core.int get total => $_get(1, 0);
  set total($core.int v) { $_setSignedInt32(1, v); }
  $core.bool hasTotal() => $_has(1);
  void clearTotal() => clearField(2);
}

class RequestDeleteSchedule extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestDeleteSchedule')
    ..a<$core.List<$core.int>>(1, 'scheduleId', $pb.PbFieldType.QY)
  ;

  RequestDeleteSchedule() : super();
  RequestDeleteSchedule.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestDeleteSchedule.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestDeleteSchedule clone() => RequestDeleteSchedule()..mergeFromMessage(this);
  RequestDeleteSchedule copyWith(void Function(RequestDeleteSchedule) updates) => super.copyWith((message) => updates(message as RequestDeleteSchedule));
  $pb.BuilderInfo get info_ => _i;
  static RequestDeleteSchedule create() => RequestDeleteSchedule();
  RequestDeleteSchedule createEmptyInstance() => create();
  static $pb.PbList<RequestDeleteSchedule> createRepeated() => $pb.PbList<RequestDeleteSchedule>();
  static RequestDeleteSchedule getDefault() => _defaultInstance ??= create()..freeze();
  static RequestDeleteSchedule _defaultInstance;

  $core.List<$core.int> get scheduleId => $_getN(0);
  set scheduleId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasScheduleId() => $_has(0);
  void clearScheduleId() => clearField(1);
}

class RequestGetSchedule extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestGetSchedule')
    ..a<$core.List<$core.int>>(1, 'scheduleId', $pb.PbFieldType.QY)
  ;

  RequestGetSchedule() : super();
  RequestGetSchedule.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestGetSchedule.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestGetSchedule clone() => RequestGetSchedule()..mergeFromMessage(this);
  RequestGetSchedule copyWith(void Function(RequestGetSchedule) updates) => super.copyWith((message) => updates(message as RequestGetSchedule));
  $pb.BuilderInfo get info_ => _i;
  static RequestGetSchedule create() => RequestGetSchedule();
  RequestGetSchedule createEmptyInstance() => create();
  static $pb.PbList<RequestGetSchedule> createRepeated() => $pb.PbList<RequestGetSchedule>();
  static RequestGetSchedule getDefault() => _defaultInstance ??= create()..freeze();
  static RequestGetSchedule _defaultInstance;

  $core.List<$core.int> get scheduleId => $_getN(0);
  set scheduleId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasScheduleId() => $_has(0);
  void clearScheduleId() => clearField(1);
}

class RequestListSchedules extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestListSchedules')
    ..a<Page>(1, 'page', $pb.PbFieldType.OM, Page.getDefault, Page.create)
    ..hasRequiredFields = false
  ;

  RequestListSchedules() : super();
  RequestListSchedules.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestListSchedules.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestListSchedules clone() => RequestListSchedules()..mergeFromMessage(this);
  RequestListSchedules copyWith(void Function(RequestListSchedules) updates) => super.copyWith((message) => updates(message as RequestListSchedules));
  $pb.BuilderInfo get info_ => _i;
  static RequestListSchedules create() => RequestListSchedules();
  RequestListSchedules createEmptyInstance() => create();
  static $pb.PbList<RequestListSchedules> createRepeated() => $pb.PbList<RequestListSchedules>();
  static RequestListSchedules getDefault() => _defaultInstance ??= create()..freeze();
  static RequestListSchedules _defaultInstance;

  Page get page => $_getN(0);
  set page(Page v) { setField(1, v); }
  $core.bool hasPage() => $_has(0);
  void clearPage() => clearField(1);
}

class ResponseListSchedules extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResponseListSchedules')
    ..pc<Schedule>(1, 'schedules', $pb.PbFieldType.PM,Schedule.create)
    ..a<$core.int>(2, 'total', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  ResponseListSchedules() : super();
  ResponseListSchedules.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResponseListSchedules.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResponseListSchedules clone() => ResponseListSchedules()..mergeFromMessage(this);
  ResponseListSchedules copyWith(void Function(ResponseListSchedules) updates) => super.copyWith((message) => updates(message as ResponseListSchedules));
  $pb.BuilderInfo get info_ => _i;
  static ResponseListSchedules create() => ResponseListSchedules();
  ResponseListSchedules createEmptyInstance() => create();
  static $pb.PbList<ResponseListSchedules> createRepeated() => $pb.PbList<ResponseListSchedules>();
  static ResponseListSchedules getDefault() => _defaultInstance ??= create()..freeze();
  static ResponseListSchedules _defaultInstance;

  $core.List<Schedule> get schedules => $_getList(0);

  $core.int get total => $_get(1, 0);
  set total($core.int v) { $_setSignedInt32(1, v); }
  $core.bool hasTotal() => $_has(1);
  void clearTotal() => clearField(2);
}

class RequestListScheduleJobs extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestListScheduleJobs')
    ..a<$core.List<$core.int>>(1, 'scheduleId', $pb.PbFieldType.QY)
    ..a<Page>(2, 'page', $pb.PbFieldType.OM, Page.getDefault, Page.create)
  ;

  RequestListScheduleJobs() : super();
  RequestListScheduleJobs.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestListScheduleJobs.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestListScheduleJobs clone() => RequestListScheduleJobs()..mergeFromMessage(this);
  RequestListScheduleJobs copyWith(void Function(RequestListScheduleJobs) updates) => super.copyWith((message) => updates(message as RequestListScheduleJobs));
  $pb.BuilderInfo get info_ => _i;
  static RequestListScheduleJobs create() => RequestListScheduleJobs();
  RequestListScheduleJobs createEmptyInstance() => create();
  static $pb.PbList<RequestListScheduleJobs> createRepeated() => $pb.PbList<RequestListScheduleJobs>();
  static RequestListScheduleJobs getDefault() => _defaultInstance ??= create()..freeze();
  static RequestListScheduleJobs _defaultInstance;

  $core.List<$core.int> get scheduleId => $_getN(0);
  set scheduleId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasScheduleId() => $_has(0);
  void clearScheduleId() => clearField(1);

  Page get page => $_getN(1);
  set page(Page v) { setField(2, v); }
  $core.bool hasPage() => $_has(1);
  void clearPage() => clearField(2);
}

class ResponseListScheduleJobs extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResponseListScheduleJobs')
    ..pc<Job>(1, 'jobs', $pb.PbFieldType.PM,Job.create)
    ..a<$core.int>(2, 'total', $pb.PbFieldType.O3)
  ;

  ResponseListScheduleJobs() : super();
  ResponseListScheduleJobs.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResponseListScheduleJobs.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResponseListScheduleJobs clone() => ResponseListScheduleJobs()..mergeFromMessage(this);
  ResponseListScheduleJobs copyWith(void Function(ResponseListScheduleJobs) updates) => super.copyWith((message) => updates(message as ResponseListScheduleJobs));
  $pb.BuilderInfo get info_ => _i;
  static ResponseListScheduleJobs create() => ResponseListScheduleJobs();
  ResponseListScheduleJobs createEmptyInstance() => create();
  static $pb.PbList<ResponseListScheduleJobs> createRepeated() => $pb.PbList<ResponseListScheduleJobs>();
  static ResponseListScheduleJobs getDefault() => _defaultInstance ??= create()..freeze();
  static ResponseListScheduleJobs _defaultInstance;

  $core.List<Job> get jobs => $_getList(0);

  $core.int get total => $_get(1, 0);
  set total($core.int v) { $_setSignedInt32(1, v); }
  $core.bool hasTotal() => $_has(1);
  void clearTotal() => clearField(2);
}

class RequestSetSchedule extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestSetSchedule')
    ..a<Schedule>(1, 'schedule', $pb.PbFieldType.OM, Schedule.getDefault, Schedule.create)
    ..hasRequiredFields = false
  ;

  RequestSetSchedule() : super();
  RequestSetSchedule.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestSetSchedule.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestSetSchedule clone() => RequestSetSchedule()..mergeFromMessage(this);
  RequestSetSchedule copyWith(void Function(RequestSetSchedule) updates) => super.copyWith((message) => updates(message as RequestSetSchedule));
  $pb.BuilderInfo get info_ => _i;
  static RequestSetSchedule create() => RequestSetSchedule();
  RequestSetSchedule createEmptyInstance() => create();
  static $pb.PbList<RequestSetSchedule> createRepeated() => $pb.PbList<RequestSetSchedule>();
  static RequestSetSchedule getDefault() => _defaultInstance ??= create()..freeze();
  static RequestSetSchedule _defaultInstance;

  Schedule get schedule => $_getN(0);
  set schedule(Schedule v) { setField(1, v); }
  $core.bool hasSchedule() => $_has(0);
  void clearSchedule() => clearField(1);
}

class ResponseNewSchedule extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResponseNewSchedule')
    ..a<$core.List<$core.int>>(1, 'scheduleId', $pb.PbFieldType.QY)
  ;

  ResponseNewSchedule() : super();
  ResponseNewSchedule.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResponseNewSchedule.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResponseNewSchedule clone() => ResponseNewSchedule()..mergeFromMessage(this);
  ResponseNewSchedule copyWith(void Function(ResponseNewSchedule) updates) => super.copyWith((message) => updates(message as ResponseNewSchedule));
  $pb.BuilderInfo get info_ => _i;
  static ResponseNewSchedule create() => ResponseNewSchedule();
  ResponseNewSchedule createEmptyInstance() => create();
  static $pb.PbList<ResponseNewSchedule> createRepeated() => $pb.PbList<ResponseNewSchedule>();
  static ResponseNewSchedule getDefault() => _defaultInstance ??= create()..freeze();
  static ResponseNewSchedule _defaultInstance;

  $core.List<$core.int> get scheduleId => $_getN(0);
  set scheduleId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasScheduleId() => $_has(0);
  void clearScheduleId() => clearField(1);
}

class RequestDeletePolicy extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestDeletePolicy')
    ..a<$core.List<$core.int>>(1, 'policyId', $pb.PbFieldType.QY)
  ;

  RequestDeletePolicy() : super();
  RequestDeletePolicy.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestDeletePolicy.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestDeletePolicy clone() => RequestDeletePolicy()..mergeFromMessage(this);
  RequestDeletePolicy copyWith(void Function(RequestDeletePolicy) updates) => super.copyWith((message) => updates(message as RequestDeletePolicy));
  $pb.BuilderInfo get info_ => _i;
  static RequestDeletePolicy create() => RequestDeletePolicy();
  RequestDeletePolicy createEmptyInstance() => create();
  static $pb.PbList<RequestDeletePolicy> createRepeated() => $pb.PbList<RequestDeletePolicy>();
  static RequestDeletePolicy getDefault() => _defaultInstance ??= create()..freeze();
  static RequestDeletePolicy _defaultInstance;

  $core.List<$core.int> get policyId => $_getN(0);
  set policyId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasPolicyId() => $_has(0);
  void clearPolicyId() => clearField(1);
}

class RequestGetPolicy extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestGetPolicy')
    ..a<$core.List<$core.int>>(1, 'policyId', $pb.PbFieldType.QY)
  ;

  RequestGetPolicy() : super();
  RequestGetPolicy.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestGetPolicy.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestGetPolicy clone() => RequestGetPolicy()..mergeFromMessage(this);
  RequestGetPolicy copyWith(void Function(RequestGetPolicy) updates) => super.copyWith((message) => updates(message as RequestGetPolicy));
  $pb.BuilderInfo get info_ => _i;
  static RequestGetPolicy create() => RequestGetPolicy();
  RequestGetPolicy createEmptyInstance() => create();
  static $pb.PbList<RequestGetPolicy> createRepeated() => $pb.PbList<RequestGetPolicy>();
  static RequestGetPolicy getDefault() => _defaultInstance ??= create()..freeze();
  static RequestGetPolicy _defaultInstance;

  $core.List<$core.int> get policyId => $_getN(0);
  set policyId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasPolicyId() => $_has(0);
  void clearPolicyId() => clearField(1);
}

class RequestListPolicies extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestListPolicies')
    ..a<Page>(1, 'page', $pb.PbFieldType.OM, Page.getDefault, Page.create)
    ..hasRequiredFields = false
  ;

  RequestListPolicies() : super();
  RequestListPolicies.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestListPolicies.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestListPolicies clone() => RequestListPolicies()..mergeFromMessage(this);
  RequestListPolicies copyWith(void Function(RequestListPolicies) updates) => super.copyWith((message) => updates(message as RequestListPolicies));
  $pb.BuilderInfo get info_ => _i;
  static RequestListPolicies create() => RequestListPolicies();
  RequestListPolicies createEmptyInstance() => create();
  static $pb.PbList<RequestListPolicies> createRepeated() => $pb.PbList<RequestListPolicies>();
  static RequestListPolicies getDefault() => _defaultInstance ??= create()..freeze();
  static RequestListPolicies _defaultInstance;

  Page get page => $_getN(0);
  set page(Page v) { setField(1, v); }
  $core.bool hasPage() => $_has(0);
  void clearPage() => clearField(1);
}

class ResponseListPolicies extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResponseListPolicies')
    ..pc<Policy>(1, 'policies', $pb.PbFieldType.PM,Policy.create)
    ..a<$core.int>(2, 'total', $pb.PbFieldType.O3)
  ;

  ResponseListPolicies() : super();
  ResponseListPolicies.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResponseListPolicies.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResponseListPolicies clone() => ResponseListPolicies()..mergeFromMessage(this);
  ResponseListPolicies copyWith(void Function(ResponseListPolicies) updates) => super.copyWith((message) => updates(message as ResponseListPolicies));
  $pb.BuilderInfo get info_ => _i;
  static ResponseListPolicies create() => ResponseListPolicies();
  ResponseListPolicies createEmptyInstance() => create();
  static $pb.PbList<ResponseListPolicies> createRepeated() => $pb.PbList<ResponseListPolicies>();
  static ResponseListPolicies getDefault() => _defaultInstance ??= create()..freeze();
  static ResponseListPolicies _defaultInstance;

  $core.List<Policy> get policies => $_getList(0);

  $core.int get total => $_get(1, 0);
  set total($core.int v) { $_setSignedInt32(1, v); }
  $core.bool hasTotal() => $_has(1);
  void clearTotal() => clearField(2);
}

class RequestSetPolicy extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestSetPolicy')
    ..a<Policy>(1, 'policy', $pb.PbFieldType.QM, Policy.getDefault, Policy.create)
  ;

  RequestSetPolicy() : super();
  RequestSetPolicy.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestSetPolicy.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestSetPolicy clone() => RequestSetPolicy()..mergeFromMessage(this);
  RequestSetPolicy copyWith(void Function(RequestSetPolicy) updates) => super.copyWith((message) => updates(message as RequestSetPolicy));
  $pb.BuilderInfo get info_ => _i;
  static RequestSetPolicy create() => RequestSetPolicy();
  RequestSetPolicy createEmptyInstance() => create();
  static $pb.PbList<RequestSetPolicy> createRepeated() => $pb.PbList<RequestSetPolicy>();
  static RequestSetPolicy getDefault() => _defaultInstance ??= create()..freeze();
  static RequestSetPolicy _defaultInstance;

  Policy get policy => $_getN(0);
  set policy(Policy v) { setField(1, v); }
  $core.bool hasPolicy() => $_has(0);
  void clearPolicy() => clearField(1);
}

class ResponseNewPolicy extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResponseNewPolicy')
    ..a<$core.List<$core.int>>(1, 'policyId', $pb.PbFieldType.QY)
  ;

  ResponseNewPolicy() : super();
  ResponseNewPolicy.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResponseNewPolicy.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResponseNewPolicy clone() => ResponseNewPolicy()..mergeFromMessage(this);
  ResponseNewPolicy copyWith(void Function(ResponseNewPolicy) updates) => super.copyWith((message) => updates(message as ResponseNewPolicy));
  $pb.BuilderInfo get info_ => _i;
  static ResponseNewPolicy create() => ResponseNewPolicy();
  ResponseNewPolicy createEmptyInstance() => create();
  static $pb.PbList<ResponseNewPolicy> createRepeated() => $pb.PbList<ResponseNewPolicy>();
  static ResponseNewPolicy getDefault() => _defaultInstance ??= create()..freeze();
  static ResponseNewPolicy _defaultInstance;

  $core.List<$core.int> get policyId => $_getN(0);
  set policyId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasPolicyId() => $_has(0);
  void clearPolicyId() => clearField(1);
}

class RateLimit extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RateLimit')
    ..aOS(1, 'name')
    ..a<$core.double>(2, 'delay', $pb.PbFieldType.OF)
    ..a<$core.List<$core.int>>(3, 'token', $pb.PbFieldType.OY)
    ..aOS(4, 'domain')
    ..hasRequiredFields = false
  ;

  RateLimit() : super();
  RateLimit.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RateLimit.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RateLimit clone() => RateLimit()..mergeFromMessage(this);
  RateLimit copyWith(void Function(RateLimit) updates) => super.copyWith((message) => updates(message as RateLimit));
  $pb.BuilderInfo get info_ => _i;
  static RateLimit create() => RateLimit();
  RateLimit createEmptyInstance() => create();
  static $pb.PbList<RateLimit> createRepeated() => $pb.PbList<RateLimit>();
  static RateLimit getDefault() => _defaultInstance ??= create()..freeze();
  static RateLimit _defaultInstance;

  $core.String get name => $_getS(0, '');
  set name($core.String v) { $_setString(0, v); }
  $core.bool hasName() => $_has(0);
  void clearName() => clearField(1);

  $core.double get delay => $_getN(1);
  set delay($core.double v) { $_setFloat(1, v); }
  $core.bool hasDelay() => $_has(1);
  void clearDelay() => clearField(2);

  $core.List<$core.int> get token => $_getN(2);
  set token($core.List<$core.int> v) { $_setBytes(2, v); }
  $core.bool hasToken() => $_has(2);
  void clearToken() => clearField(3);

  $core.String get domain => $_getS(3, '');
  set domain($core.String v) { $_setString(3, v); }
  $core.bool hasDomain() => $_has(3);
  void clearDomain() => clearField(4);
}

class RequestListRateLimits extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestListRateLimits')
    ..a<Page>(1, 'page', $pb.PbFieldType.OM, Page.getDefault, Page.create)
    ..hasRequiredFields = false
  ;

  RequestListRateLimits() : super();
  RequestListRateLimits.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestListRateLimits.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestListRateLimits clone() => RequestListRateLimits()..mergeFromMessage(this);
  RequestListRateLimits copyWith(void Function(RequestListRateLimits) updates) => super.copyWith((message) => updates(message as RequestListRateLimits));
  $pb.BuilderInfo get info_ => _i;
  static RequestListRateLimits create() => RequestListRateLimits();
  RequestListRateLimits createEmptyInstance() => create();
  static $pb.PbList<RequestListRateLimits> createRepeated() => $pb.PbList<RequestListRateLimits>();
  static RequestListRateLimits getDefault() => _defaultInstance ??= create()..freeze();
  static RequestListRateLimits _defaultInstance;

  Page get page => $_getN(0);
  set page(Page v) { setField(1, v); }
  $core.bool hasPage() => $_has(0);
  void clearPage() => clearField(1);
}

class ResponseListRateLimits extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResponseListRateLimits')
    ..pc<RateLimit>(1, 'rateLimits', $pb.PbFieldType.PM,RateLimit.create)
    ..a<$core.int>(2, 'total', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  ResponseListRateLimits() : super();
  ResponseListRateLimits.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResponseListRateLimits.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResponseListRateLimits clone() => ResponseListRateLimits()..mergeFromMessage(this);
  ResponseListRateLimits copyWith(void Function(ResponseListRateLimits) updates) => super.copyWith((message) => updates(message as ResponseListRateLimits));
  $pb.BuilderInfo get info_ => _i;
  static ResponseListRateLimits create() => ResponseListRateLimits();
  ResponseListRateLimits createEmptyInstance() => create();
  static $pb.PbList<ResponseListRateLimits> createRepeated() => $pb.PbList<ResponseListRateLimits>();
  static ResponseListRateLimits getDefault() => _defaultInstance ??= create()..freeze();
  static ResponseListRateLimits _defaultInstance;

  $core.List<RateLimit> get rateLimits => $_getList(0);

  $core.int get total => $_get(1, 0);
  set total($core.int v) { $_setSignedInt32(1, v); }
  $core.bool hasTotal() => $_has(1);
  void clearTotal() => clearField(2);
}

class RequestSetRateLimit extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestSetRateLimit')
    ..aOS(1, 'domain')
    ..a<$core.double>(2, 'delay', $pb.PbFieldType.OF)
    ..hasRequiredFields = false
  ;

  RequestSetRateLimit() : super();
  RequestSetRateLimit.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestSetRateLimit.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestSetRateLimit clone() => RequestSetRateLimit()..mergeFromMessage(this);
  RequestSetRateLimit copyWith(void Function(RequestSetRateLimit) updates) => super.copyWith((message) => updates(message as RequestSetRateLimit));
  $pb.BuilderInfo get info_ => _i;
  static RequestSetRateLimit create() => RequestSetRateLimit();
  RequestSetRateLimit createEmptyInstance() => create();
  static $pb.PbList<RequestSetRateLimit> createRepeated() => $pb.PbList<RequestSetRateLimit>();
  static RequestSetRateLimit getDefault() => _defaultInstance ??= create()..freeze();
  static RequestSetRateLimit _defaultInstance;

  $core.String get domain => $_getS(0, '');
  set domain($core.String v) { $_setString(0, v); }
  $core.bool hasDomain() => $_has(0);
  void clearDomain() => clearField(1);

  $core.double get delay => $_getN(1);
  set delay($core.double v) { $_setFloat(1, v); }
  $core.bool hasDelay() => $_has(1);
  void clearDelay() => clearField(2);
}

class RequestPerformanceProfile extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestPerformanceProfile')
    ..a<$core.double>(1, 'duration', $pb.PbFieldType.OD, 5.0)
    ..a<$core.String>(2, 'sortBy', $pb.PbFieldType.OS, 'total_time')
    ..a<$core.int>(3, 'topN', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  RequestPerformanceProfile() : super();
  RequestPerformanceProfile.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestPerformanceProfile.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestPerformanceProfile clone() => RequestPerformanceProfile()..mergeFromMessage(this);
  RequestPerformanceProfile copyWith(void Function(RequestPerformanceProfile) updates) => super.copyWith((message) => updates(message as RequestPerformanceProfile));
  $pb.BuilderInfo get info_ => _i;
  static RequestPerformanceProfile create() => RequestPerformanceProfile();
  RequestPerformanceProfile createEmptyInstance() => create();
  static $pb.PbList<RequestPerformanceProfile> createRepeated() => $pb.PbList<RequestPerformanceProfile>();
  static RequestPerformanceProfile getDefault() => _defaultInstance ??= create()..freeze();
  static RequestPerformanceProfile _defaultInstance;

  $core.double get duration => $_getN(0);
  set duration($core.double v) { $_setDouble(0, v); }
  $core.bool hasDuration() => $_has(0);
  void clearDuration() => clearField(1);

  $core.String get sortBy => $_getS(1, 'total_time');
  set sortBy($core.String v) { $_setString(1, v); }
  $core.bool hasSortBy() => $_has(1);
  void clearSortBy() => clearField(2);

  $core.int get topN => $_get(2, 0);
  set topN($core.int v) { $_setSignedInt32(2, v); }
  $core.bool hasTopN() => $_has(2);
  void clearTopN() => clearField(3);
}

class PerformanceProfileFunction extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('PerformanceProfileFunction')
    ..aOS(1, 'file')
    ..a<$core.int>(2, 'lineNumber', $pb.PbFieldType.O3)
    ..aOS(3, 'function')
    ..a<$core.int>(4, 'calls', $pb.PbFieldType.O3)
    ..a<$core.int>(5, 'nonRecursiveCalls', $pb.PbFieldType.O3)
    ..a<$core.double>(6, 'totalTime', $pb.PbFieldType.OD)
    ..a<$core.double>(7, 'cumulativeTime', $pb.PbFieldType.OD)
    ..hasRequiredFields = false
  ;

  PerformanceProfileFunction() : super();
  PerformanceProfileFunction.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  PerformanceProfileFunction.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  PerformanceProfileFunction clone() => PerformanceProfileFunction()..mergeFromMessage(this);
  PerformanceProfileFunction copyWith(void Function(PerformanceProfileFunction) updates) => super.copyWith((message) => updates(message as PerformanceProfileFunction));
  $pb.BuilderInfo get info_ => _i;
  static PerformanceProfileFunction create() => PerformanceProfileFunction();
  PerformanceProfileFunction createEmptyInstance() => create();
  static $pb.PbList<PerformanceProfileFunction> createRepeated() => $pb.PbList<PerformanceProfileFunction>();
  static PerformanceProfileFunction getDefault() => _defaultInstance ??= create()..freeze();
  static PerformanceProfileFunction _defaultInstance;

  $core.String get file => $_getS(0, '');
  set file($core.String v) { $_setString(0, v); }
  $core.bool hasFile() => $_has(0);
  void clearFile() => clearField(1);

  $core.int get lineNumber => $_get(1, 0);
  set lineNumber($core.int v) { $_setSignedInt32(1, v); }
  $core.bool hasLineNumber() => $_has(1);
  void clearLineNumber() => clearField(2);

  $core.String get function => $_getS(2, '');
  set function($core.String v) { $_setString(2, v); }
  $core.bool hasFunction() => $_has(2);
  void clearFunction() => clearField(3);

  $core.int get calls => $_get(3, 0);
  set calls($core.int v) { $_setSignedInt32(3, v); }
  $core.bool hasCalls() => $_has(3);
  void clearCalls() => clearField(4);

  $core.int get nonRecursiveCalls => $_get(4, 0);
  set nonRecursiveCalls($core.int v) { $_setSignedInt32(4, v); }
  $core.bool hasNonRecursiveCalls() => $_has(4);
  void clearNonRecursiveCalls() => clearField(5);

  $core.double get totalTime => $_getN(5);
  set totalTime($core.double v) { $_setDouble(5, v); }
  $core.bool hasTotalTime() => $_has(5);
  void clearTotalTime() => clearField(6);

  $core.double get cumulativeTime => $_getN(6);
  set cumulativeTime($core.double v) { $_setDouble(6, v); }
  $core.bool hasCumulativeTime() => $_has(6);
  void clearCumulativeTime() => clearField(7);
}

class ResponsePerformanceProfile extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResponsePerformanceProfile')
    ..a<$core.int>(1, 'totalCalls', $pb.PbFieldType.O3)
    ..a<$core.double>(2, 'totalTime', $pb.PbFieldType.OD)
    ..pc<PerformanceProfileFunction>(3, 'functions', $pb.PbFieldType.PM,PerformanceProfileFunction.create)
    ..hasRequiredFields = false
  ;

  ResponsePerformanceProfile() : super();
  ResponsePerformanceProfile.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResponsePerformanceProfile.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResponsePerformanceProfile clone() => ResponsePerformanceProfile()..mergeFromMessage(this);
  ResponsePerformanceProfile copyWith(void Function(ResponsePerformanceProfile) updates) => super.copyWith((message) => updates(message as ResponsePerformanceProfile));
  $pb.BuilderInfo get info_ => _i;
  static ResponsePerformanceProfile create() => ResponsePerformanceProfile();
  ResponsePerformanceProfile createEmptyInstance() => create();
  static $pb.PbList<ResponsePerformanceProfile> createRepeated() => $pb.PbList<ResponsePerformanceProfile>();
  static ResponsePerformanceProfile getDefault() => _defaultInstance ??= create()..freeze();
  static ResponsePerformanceProfile _defaultInstance;

  $core.int get totalCalls => $_get(0, 0);
  set totalCalls($core.int v) { $_setSignedInt32(0, v); }
  $core.bool hasTotalCalls() => $_has(0);
  void clearTotalCalls() => clearField(1);

  $core.double get totalTime => $_getN(1);
  set totalTime($core.double v) { $_setDouble(1, v); }
  $core.bool hasTotalTime() => $_has(1);
  void clearTotalTime() => clearField(2);

  $core.List<PerformanceProfileFunction> get functions => $_getList(2);
}

class RequestSubscribeJobStatus extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestSubscribeJobStatus')
    ..a<$core.double>(1, 'minInterval', $pb.PbFieldType.OD, 1.0)
    ..hasRequiredFields = false
  ;

  RequestSubscribeJobStatus() : super();
  RequestSubscribeJobStatus.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestSubscribeJobStatus.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestSubscribeJobStatus clone() => RequestSubscribeJobStatus()..mergeFromMessage(this);
  RequestSubscribeJobStatus copyWith(void Function(RequestSubscribeJobStatus) updates) => super.copyWith((message) => updates(message as RequestSubscribeJobStatus));
  $pb.BuilderInfo get info_ => _i;
  static RequestSubscribeJobStatus create() => RequestSubscribeJobStatus();
  RequestSubscribeJobStatus createEmptyInstance() => create();
  static $pb.PbList<RequestSubscribeJobStatus> createRepeated() => $pb.PbList<RequestSubscribeJobStatus>();
  static RequestSubscribeJobStatus getDefault() => _defaultInstance ??= create()..freeze();
  static RequestSubscribeJobStatus _defaultInstance;

  $core.double get minInterval => $_getN(0);
  set minInterval($core.double v) { $_setDouble(0, v); }
  $core.bool hasMinInterval() => $_has(0);
  void clearMinInterval() => clearField(1);
}

class RequestSubscribeJobSync extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestSubscribeJobSync')
    ..a<$core.List<$core.int>>(1, 'jobId', $pb.PbFieldType.QY)
    ..a<$core.List<$core.int>>(2, 'syncToken', $pb.PbFieldType.OY)
    ..a<$core.bool>(3, 'compressionOk', $pb.PbFieldType.OB, true)
  ;

  RequestSubscribeJobSync() : super();
  RequestSubscribeJobSync.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestSubscribeJobSync.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestSubscribeJobSync clone() => RequestSubscribeJobSync()..mergeFromMessage(this);
  RequestSubscribeJobSync copyWith(void Function(RequestSubscribeJobSync) updates) => super.copyWith((message) => updates(message as RequestSubscribeJobSync));
  $pb.BuilderInfo get info_ => _i;
  static RequestSubscribeJobSync create() => RequestSubscribeJobSync();
  RequestSubscribeJobSync createEmptyInstance() => create();
  static $pb.PbList<RequestSubscribeJobSync> createRepeated() => $pb.PbList<RequestSubscribeJobSync>();
  static RequestSubscribeJobSync getDefault() => _defaultInstance ??= create()..freeze();
  static RequestSubscribeJobSync _defaultInstance;

  $core.List<$core.int> get jobId => $_getN(0);
  set jobId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasJobId() => $_has(0);
  void clearJobId() => clearField(1);

  $core.List<$core.int> get syncToken => $_getN(1);
  set syncToken($core.List<$core.int> v) { $_setBytes(1, v); }
  $core.bool hasSyncToken() => $_has(1);
  void clearSyncToken() => clearField(2);

  $core.bool get compressionOk => $_get(2, true);
  set compressionOk($core.bool v) { $_setBool(2, v); }
  $core.bool hasCompressionOk() => $_has(2);
  void clearCompressionOk() => clearField(3);
}

class SyncItem extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('SyncItem')
    ..a<CrawlResponse>(1, 'item', $pb.PbFieldType.QM, CrawlResponse.getDefault, CrawlResponse.create)
    ..a<$core.List<$core.int>>(2, 'token', $pb.PbFieldType.QY)
  ;

  SyncItem() : super();
  SyncItem.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  SyncItem.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  SyncItem clone() => SyncItem()..mergeFromMessage(this);
  SyncItem copyWith(void Function(SyncItem) updates) => super.copyWith((message) => updates(message as SyncItem));
  $pb.BuilderInfo get info_ => _i;
  static SyncItem create() => SyncItem();
  SyncItem createEmptyInstance() => create();
  static $pb.PbList<SyncItem> createRepeated() => $pb.PbList<SyncItem>();
  static SyncItem getDefault() => _defaultInstance ??= create()..freeze();
  static SyncItem _defaultInstance;

  CrawlResponse get item => $_getN(0);
  set item(CrawlResponse v) { setField(1, v); }
  $core.bool hasItem() => $_has(0);
  void clearItem() => clearField(1);

  $core.List<$core.int> get token => $_getN(1);
  set token($core.List<$core.int> v) { $_setBytes(1, v); }
  $core.bool hasToken() => $_has(1);
  void clearToken() => clearField(2);
}

enum ServerMessage_MessageType {
  event, 
  response, 
  notSet
}

class ServerMessage extends $pb.GeneratedMessage {
  static const $core.Map<$core.int, ServerMessage_MessageType> _ServerMessage_MessageTypeByTag = {
    1 : ServerMessage_MessageType.event,
    2 : ServerMessage_MessageType.response,
    0 : ServerMessage_MessageType.notSet
  };
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ServerMessage')
    ..a<Event>(1, 'event', $pb.PbFieldType.OM, Event.getDefault, Event.create)
    ..a<Response>(2, 'response', $pb.PbFieldType.OM, Response.getDefault, Response.create)
    ..oo(0, [1, 2])
  ;

  ServerMessage() : super();
  ServerMessage.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ServerMessage.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ServerMessage clone() => ServerMessage()..mergeFromMessage(this);
  ServerMessage copyWith(void Function(ServerMessage) updates) => super.copyWith((message) => updates(message as ServerMessage));
  $pb.BuilderInfo get info_ => _i;
  static ServerMessage create() => ServerMessage();
  ServerMessage createEmptyInstance() => create();
  static $pb.PbList<ServerMessage> createRepeated() => $pb.PbList<ServerMessage>();
  static ServerMessage getDefault() => _defaultInstance ??= create()..freeze();
  static ServerMessage _defaultInstance;

  ServerMessage_MessageType whichMessageType() => _ServerMessage_MessageTypeByTag[$_whichOneof(0)];
  void clearMessageType() => clearField($_whichOneof(0));

  Event get event => $_getN(0);
  set event(Event v) { setField(1, v); }
  $core.bool hasEvent() => $_has(0);
  void clearEvent() => clearField(1);

  Response get response => $_getN(1);
  set response(Response v) { setField(2, v); }
  $core.bool hasResponse() => $_has(1);
  void clearResponse() => clearField(2);
}

class RequestSubscribeResourceMonitor extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestSubscribeResourceMonitor')
    ..a<$core.int>(1, 'history', $pb.PbFieldType.O3, 300)
    ..hasRequiredFields = false
  ;

  RequestSubscribeResourceMonitor() : super();
  RequestSubscribeResourceMonitor.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestSubscribeResourceMonitor.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestSubscribeResourceMonitor clone() => RequestSubscribeResourceMonitor()..mergeFromMessage(this);
  RequestSubscribeResourceMonitor copyWith(void Function(RequestSubscribeResourceMonitor) updates) => super.copyWith((message) => updates(message as RequestSubscribeResourceMonitor));
  $pb.BuilderInfo get info_ => _i;
  static RequestSubscribeResourceMonitor create() => RequestSubscribeResourceMonitor();
  RequestSubscribeResourceMonitor createEmptyInstance() => create();
  static $pb.PbList<RequestSubscribeResourceMonitor> createRepeated() => $pb.PbList<RequestSubscribeResourceMonitor>();
  static RequestSubscribeResourceMonitor getDefault() => _defaultInstance ??= create()..freeze();
  static RequestSubscribeResourceMonitor _defaultInstance;

  $core.int get history => $_get(0, 300);
  set history($core.int v) { $_setSignedInt32(0, v); }
  $core.bool hasHistory() => $_has(0);
  void clearHistory() => clearField(1);
}

class RequestSubscribeTaskMonitor extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestSubscribeTaskMonitor')
    ..a<$core.double>(1, 'period', $pb.PbFieldType.OD, 3.0)
    ..a<$core.int>(2, 'topN', $pb.PbFieldType.O3, 20)
    ..hasRequiredFields = false
  ;

  RequestSubscribeTaskMonitor() : super();
  RequestSubscribeTaskMonitor.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestSubscribeTaskMonitor.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestSubscribeTaskMonitor clone() => RequestSubscribeTaskMonitor()..mergeFromMessage(this);
  RequestSubscribeTaskMonitor copyWith(void Function(RequestSubscribeTaskMonitor) updates) => super.copyWith((message) => updates(message as RequestSubscribeTaskMonitor));
  $pb.BuilderInfo get info_ => _i;
  static RequestSubscribeTaskMonitor create() => RequestSubscribeTaskMonitor();
  RequestSubscribeTaskMonitor createEmptyInstance() => create();
  static $pb.PbList<RequestSubscribeTaskMonitor> createRepeated() => $pb.PbList<RequestSubscribeTaskMonitor>();
  static RequestSubscribeTaskMonitor getDefault() => _defaultInstance ??= create()..freeze();
  static RequestSubscribeTaskMonitor _defaultInstance;

  $core.double get period => $_getN(0);
  set period($core.double v) { $_setDouble(0, v); }
  $core.bool hasPeriod() => $_has(0);
  void clearPeriod() => clearField(1);

  $core.int get topN => $_get(1, 20);
  set topN($core.int v) { $_setSignedInt32(1, v); }
  $core.bool hasTopN() => $_has(1);
  void clearTopN() => clearField(2);
}

class ResponseNewSubscription extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResponseNewSubscription')
    ..a<$core.int>(1, 'subscriptionId', $pb.PbFieldType.Q3)
  ;

  ResponseNewSubscription() : super();
  ResponseNewSubscription.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResponseNewSubscription.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResponseNewSubscription clone() => ResponseNewSubscription()..mergeFromMessage(this);
  ResponseNewSubscription copyWith(void Function(ResponseNewSubscription) updates) => super.copyWith((message) => updates(message as ResponseNewSubscription));
  $pb.BuilderInfo get info_ => _i;
  static ResponseNewSubscription create() => ResponseNewSubscription();
  ResponseNewSubscription createEmptyInstance() => create();
  static $pb.PbList<ResponseNewSubscription> createRepeated() => $pb.PbList<ResponseNewSubscription>();
  static ResponseNewSubscription getDefault() => _defaultInstance ??= create()..freeze();
  static ResponseNewSubscription _defaultInstance;

  $core.int get subscriptionId => $_get(0, 0);
  set subscriptionId($core.int v) { $_setSignedInt32(0, v); }
  $core.bool hasSubscriptionId() => $_has(0);
  void clearSubscriptionId() => clearField(1);
}

class RequestUnsubscribe extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('RequestUnsubscribe')
    ..a<$core.int>(1, 'subscriptionId', $pb.PbFieldType.Q3)
  ;

  RequestUnsubscribe() : super();
  RequestUnsubscribe.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  RequestUnsubscribe.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  RequestUnsubscribe clone() => RequestUnsubscribe()..mergeFromMessage(this);
  RequestUnsubscribe copyWith(void Function(RequestUnsubscribe) updates) => super.copyWith((message) => updates(message as RequestUnsubscribe));
  $pb.BuilderInfo get info_ => _i;
  static RequestUnsubscribe create() => RequestUnsubscribe();
  RequestUnsubscribe createEmptyInstance() => create();
  static $pb.PbList<RequestUnsubscribe> createRepeated() => $pb.PbList<RequestUnsubscribe>();
  static RequestUnsubscribe getDefault() => _defaultInstance ??= create()..freeze();
  static RequestUnsubscribe _defaultInstance;

  $core.int get subscriptionId => $_get(0, 0);
  set subscriptionId($core.int v) { $_setSignedInt32(0, v); }
  $core.bool hasSubscriptionId() => $_has(0);
  void clearSubscriptionId() => clearField(1);
}

class SubscriptionClosed extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('SubscriptionClosed')
    ..e<SubscriptionClosed_Reason>(1, 'reason', $pb.PbFieldType.QE, SubscriptionClosed_Reason.COMPLETE, SubscriptionClosed_Reason.valueOf, SubscriptionClosed_Reason.values)
    ..aOS(2, 'message')
  ;

  SubscriptionClosed() : super();
  SubscriptionClosed.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  SubscriptionClosed.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  SubscriptionClosed clone() => SubscriptionClosed()..mergeFromMessage(this);
  SubscriptionClosed copyWith(void Function(SubscriptionClosed) updates) => super.copyWith((message) => updates(message as SubscriptionClosed));
  $pb.BuilderInfo get info_ => _i;
  static SubscriptionClosed create() => SubscriptionClosed();
  SubscriptionClosed createEmptyInstance() => create();
  static $pb.PbList<SubscriptionClosed> createRepeated() => $pb.PbList<SubscriptionClosed>();
  static SubscriptionClosed getDefault() => _defaultInstance ??= create()..freeze();
  static SubscriptionClosed _defaultInstance;

  SubscriptionClosed_Reason get reason => $_getN(0);
  set reason(SubscriptionClosed_Reason v) { setField(1, v); }
  $core.bool hasReason() => $_has(0);
  void clearReason() => clearField(1);

  $core.String get message => $_getS(1, '');
  set message($core.String v) { $_setString(1, v); }
  $core.bool hasMessage() => $_has(1);
  void clearMessage() => clearField(2);
}

class ResourceFrame extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResourceFrame')
    ..aOS(1, 'timestamp')
    ..pc<ResourceFrameCpu>(2, 'cpus', $pb.PbFieldType.PM,ResourceFrameCpu.create)
    ..a<ResourceFrameMemory>(3, 'memory', $pb.PbFieldType.OM, ResourceFrameMemory.getDefault, ResourceFrameMemory.create)
    ..pc<ResourceFrameDisk>(4, 'disks', $pb.PbFieldType.PM,ResourceFrameDisk.create)
    ..pc<ResourceFrameNetwork>(5, 'networks', $pb.PbFieldType.PM,ResourceFrameNetwork.create)
    ..pc<ResourceFrameJob>(6, 'jobs', $pb.PbFieldType.PM,ResourceFrameJob.create)
    ..a<$core.int>(7, 'currentDownloads', $pb.PbFieldType.O3)
    ..a<$core.int>(8, 'maximumDownloads', $pb.PbFieldType.O3)
    ..a<$core.int>(9, 'rateLimiter', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  ResourceFrame() : super();
  ResourceFrame.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResourceFrame.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResourceFrame clone() => ResourceFrame()..mergeFromMessage(this);
  ResourceFrame copyWith(void Function(ResourceFrame) updates) => super.copyWith((message) => updates(message as ResourceFrame));
  $pb.BuilderInfo get info_ => _i;
  static ResourceFrame create() => ResourceFrame();
  ResourceFrame createEmptyInstance() => create();
  static $pb.PbList<ResourceFrame> createRepeated() => $pb.PbList<ResourceFrame>();
  static ResourceFrame getDefault() => _defaultInstance ??= create()..freeze();
  static ResourceFrame _defaultInstance;

  $core.String get timestamp => $_getS(0, '');
  set timestamp($core.String v) { $_setString(0, v); }
  $core.bool hasTimestamp() => $_has(0);
  void clearTimestamp() => clearField(1);

  $core.List<ResourceFrameCpu> get cpus => $_getList(1);

  ResourceFrameMemory get memory => $_getN(2);
  set memory(ResourceFrameMemory v) { setField(3, v); }
  $core.bool hasMemory() => $_has(2);
  void clearMemory() => clearField(3);

  $core.List<ResourceFrameDisk> get disks => $_getList(3);

  $core.List<ResourceFrameNetwork> get networks => $_getList(4);

  $core.List<ResourceFrameJob> get jobs => $_getList(5);

  $core.int get currentDownloads => $_get(6, 0);
  set currentDownloads($core.int v) { $_setSignedInt32(6, v); }
  $core.bool hasCurrentDownloads() => $_has(6);
  void clearCurrentDownloads() => clearField(7);

  $core.int get maximumDownloads => $_get(7, 0);
  set maximumDownloads($core.int v) { $_setSignedInt32(7, v); }
  $core.bool hasMaximumDownloads() => $_has(7);
  void clearMaximumDownloads() => clearField(8);

  $core.int get rateLimiter => $_get(8, 0);
  set rateLimiter($core.int v) { $_setSignedInt32(8, v); }
  $core.bool hasRateLimiter() => $_has(8);
  void clearRateLimiter() => clearField(9);
}

class ResourceFrameCpu extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResourceFrameCpu')
    ..a<$core.double>(1, 'usage', $pb.PbFieldType.OD)
    ..hasRequiredFields = false
  ;

  ResourceFrameCpu() : super();
  ResourceFrameCpu.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResourceFrameCpu.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResourceFrameCpu clone() => ResourceFrameCpu()..mergeFromMessage(this);
  ResourceFrameCpu copyWith(void Function(ResourceFrameCpu) updates) => super.copyWith((message) => updates(message as ResourceFrameCpu));
  $pb.BuilderInfo get info_ => _i;
  static ResourceFrameCpu create() => ResourceFrameCpu();
  ResourceFrameCpu createEmptyInstance() => create();
  static $pb.PbList<ResourceFrameCpu> createRepeated() => $pb.PbList<ResourceFrameCpu>();
  static ResourceFrameCpu getDefault() => _defaultInstance ??= create()..freeze();
  static ResourceFrameCpu _defaultInstance;

  $core.double get usage => $_getN(0);
  set usage($core.double v) { $_setDouble(0, v); }
  $core.bool hasUsage() => $_has(0);
  void clearUsage() => clearField(1);
}

class ResourceFrameJob extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResourceFrameJob')
    ..a<$core.List<$core.int>>(1, 'jobId', $pb.PbFieldType.OY)
    ..aOS(2, 'name')
    ..a<$core.int>(3, 'currentDownloads', $pb.PbFieldType.O3)
    ..hasRequiredFields = false
  ;

  ResourceFrameJob() : super();
  ResourceFrameJob.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResourceFrameJob.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResourceFrameJob clone() => ResourceFrameJob()..mergeFromMessage(this);
  ResourceFrameJob copyWith(void Function(ResourceFrameJob) updates) => super.copyWith((message) => updates(message as ResourceFrameJob));
  $pb.BuilderInfo get info_ => _i;
  static ResourceFrameJob create() => ResourceFrameJob();
  ResourceFrameJob createEmptyInstance() => create();
  static $pb.PbList<ResourceFrameJob> createRepeated() => $pb.PbList<ResourceFrameJob>();
  static ResourceFrameJob getDefault() => _defaultInstance ??= create()..freeze();
  static ResourceFrameJob _defaultInstance;

  $core.List<$core.int> get jobId => $_getN(0);
  set jobId($core.List<$core.int> v) { $_setBytes(0, v); }
  $core.bool hasJobId() => $_has(0);
  void clearJobId() => clearField(1);

  $core.String get name => $_getS(1, '');
  set name($core.String v) { $_setString(1, v); }
  $core.bool hasName() => $_has(1);
  void clearName() => clearField(2);

  $core.int get currentDownloads => $_get(2, 0);
  set currentDownloads($core.int v) { $_setSignedInt32(2, v); }
  $core.bool hasCurrentDownloads() => $_has(2);
  void clearCurrentDownloads() => clearField(3);
}

class ResourceFrameDisk extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResourceFrameDisk')
    ..aOS(1, 'mount')
    ..aInt64(2, 'used')
    ..aInt64(3, 'total')
    ..hasRequiredFields = false
  ;

  ResourceFrameDisk() : super();
  ResourceFrameDisk.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResourceFrameDisk.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResourceFrameDisk clone() => ResourceFrameDisk()..mergeFromMessage(this);
  ResourceFrameDisk copyWith(void Function(ResourceFrameDisk) updates) => super.copyWith((message) => updates(message as ResourceFrameDisk));
  $pb.BuilderInfo get info_ => _i;
  static ResourceFrameDisk create() => ResourceFrameDisk();
  ResourceFrameDisk createEmptyInstance() => create();
  static $pb.PbList<ResourceFrameDisk> createRepeated() => $pb.PbList<ResourceFrameDisk>();
  static ResourceFrameDisk getDefault() => _defaultInstance ??= create()..freeze();
  static ResourceFrameDisk _defaultInstance;

  $core.String get mount => $_getS(0, '');
  set mount($core.String v) { $_setString(0, v); }
  $core.bool hasMount() => $_has(0);
  void clearMount() => clearField(1);

  Int64 get used => $_getI64(1);
  set used(Int64 v) { $_setInt64(1, v); }
  $core.bool hasUsed() => $_has(1);
  void clearUsed() => clearField(2);

  Int64 get total => $_getI64(2);
  set total(Int64 v) { $_setInt64(2, v); }
  $core.bool hasTotal() => $_has(2);
  void clearTotal() => clearField(3);
}

class ResourceFrameMemory extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResourceFrameMemory')
    ..aInt64(1, 'used')
    ..aInt64(2, 'total')
    ..hasRequiredFields = false
  ;

  ResourceFrameMemory() : super();
  ResourceFrameMemory.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResourceFrameMemory.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResourceFrameMemory clone() => ResourceFrameMemory()..mergeFromMessage(this);
  ResourceFrameMemory copyWith(void Function(ResourceFrameMemory) updates) => super.copyWith((message) => updates(message as ResourceFrameMemory));
  $pb.BuilderInfo get info_ => _i;
  static ResourceFrameMemory create() => ResourceFrameMemory();
  ResourceFrameMemory createEmptyInstance() => create();
  static $pb.PbList<ResourceFrameMemory> createRepeated() => $pb.PbList<ResourceFrameMemory>();
  static ResourceFrameMemory getDefault() => _defaultInstance ??= create()..freeze();
  static ResourceFrameMemory _defaultInstance;

  Int64 get used => $_getI64(0);
  set used(Int64 v) { $_setInt64(0, v); }
  $core.bool hasUsed() => $_has(0);
  void clearUsed() => clearField(1);

  Int64 get total => $_getI64(1);
  set total(Int64 v) { $_setInt64(1, v); }
  $core.bool hasTotal() => $_has(1);
  void clearTotal() => clearField(2);
}

class ResourceFrameNetwork extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('ResourceFrameNetwork')
    ..aOS(1, 'name')
    ..aInt64(2, 'sent')
    ..aInt64(3, 'received')
    ..hasRequiredFields = false
  ;

  ResourceFrameNetwork() : super();
  ResourceFrameNetwork.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  ResourceFrameNetwork.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  ResourceFrameNetwork clone() => ResourceFrameNetwork()..mergeFromMessage(this);
  ResourceFrameNetwork copyWith(void Function(ResourceFrameNetwork) updates) => super.copyWith((message) => updates(message as ResourceFrameNetwork));
  $pb.BuilderInfo get info_ => _i;
  static ResourceFrameNetwork create() => ResourceFrameNetwork();
  ResourceFrameNetwork createEmptyInstance() => create();
  static $pb.PbList<ResourceFrameNetwork> createRepeated() => $pb.PbList<ResourceFrameNetwork>();
  static ResourceFrameNetwork getDefault() => _defaultInstance ??= create()..freeze();
  static ResourceFrameNetwork _defaultInstance;

  $core.String get name => $_getS(0, '');
  set name($core.String v) { $_setString(0, v); }
  $core.bool hasName() => $_has(0);
  void clearName() => clearField(1);

  Int64 get sent => $_getI64(1);
  set sent(Int64 v) { $_setInt64(1, v); }
  $core.bool hasSent() => $_has(1);
  void clearSent() => clearField(2);

  Int64 get received => $_getI64(2);
  set received(Int64 v) { $_setInt64(2, v); }
  $core.bool hasReceived() => $_has(2);
  void clearReceived() => clearField(3);
}

class TaskTree extends $pb.GeneratedMessage {
  static final $pb.BuilderInfo _i = $pb.BuilderInfo('TaskTree')
    ..aOS(1, 'name')
    ..pc<TaskTree>(2, 'subtasks', $pb.PbFieldType.PM,TaskTree.create)
    ..hasRequiredFields = false
  ;

  TaskTree() : super();
  TaskTree.fromBuffer($core.List<$core.int> i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromBuffer(i, r);
  TaskTree.fromJson($core.String i, [$pb.ExtensionRegistry r = $pb.ExtensionRegistry.EMPTY]) : super.fromJson(i, r);
  TaskTree clone() => TaskTree()..mergeFromMessage(this);
  TaskTree copyWith(void Function(TaskTree) updates) => super.copyWith((message) => updates(message as TaskTree));
  $pb.BuilderInfo get info_ => _i;
  static TaskTree create() => TaskTree();
  TaskTree createEmptyInstance() => create();
  static $pb.PbList<TaskTree> createRepeated() => $pb.PbList<TaskTree>();
  static TaskTree getDefault() => _defaultInstance ??= create()..freeze();
  static TaskTree _defaultInstance;

  $core.String get name => $_getS(0, '');
  set name($core.String v) { $_setString(0, v); }
  $core.bool hasName() => $_has(0);
  void clearName() => clearField(1);

  $core.List<TaskTree> get subtasks => $_getList(1);
}

