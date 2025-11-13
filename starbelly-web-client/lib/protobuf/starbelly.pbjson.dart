///
//  Generated code. Do not modify.
//  source: starbelly.proto
///
// ignore_for_file: camel_case_types,non_constant_identifier_names,library_prefixes,unused_import,unused_shown_name

const CaptchaSolverAntigateCharacters$json = const {
  '1': 'CaptchaSolverAntigateCharacters',
  '2': const [
    const {'1': 'ALPHANUMERIC', '2': 1},
    const {'1': 'NUMBERS_ONLY', '2': 2},
    const {'1': 'ALPHA_ONLY', '2': 3},
  ],
};

const JobRunState$json = const {
  '1': 'JobRunState',
  '2': const [
    const {'1': 'CANCELLED', '2': 1},
    const {'1': 'COMPLETED', '2': 2},
    const {'1': 'PAUSED', '2': 3},
    const {'1': 'PENDING', '2': 4},
    const {'1': 'RUNNING', '2': 5},
    const {'1': 'DELETED', '2': 6},
  ],
};

const ScheduleTimeUnit$json = const {
  '1': 'ScheduleTimeUnit',
  '2': const [
    const {'1': 'MINUTES', '2': 1},
    const {'1': 'HOURS', '2': 2},
    const {'1': 'DAYS', '2': 3},
    const {'1': 'WEEKS', '2': 4},
    const {'1': 'MONTHS', '2': 5},
    const {'1': 'YEARS', '2': 6},
  ],
};

const ScheduleTiming$json = const {
  '1': 'ScheduleTiming',
  '2': const [
    const {'1': 'AFTER_PREVIOUS_JOB_FINISHED', '2': 1},
    const {'1': 'REGULAR_INTERVAL', '2': 2},
  ],
};

const PatternMatch$json = const {
  '1': 'PatternMatch',
  '2': const [
    const {'1': 'MATCHES', '2': 1},
    const {'1': 'DOES_NOT_MATCH', '2': 2},
  ],
};

const CaptchaSolver$json = const {
  '1': 'CaptchaSolver',
  '2': const [
    const {'1': 'solver_id', '3': 1, '4': 1, '5': 12, '10': 'solverId'},
    const {'1': 'name', '3': 2, '4': 1, '5': 9, '10': 'name'},
    const {'1': 'created_at', '3': 3, '4': 1, '5': 9, '10': 'createdAt'},
    const {'1': 'updated_at', '3': 4, '4': 1, '5': 9, '10': 'updatedAt'},
    const {'1': 'antigate', '3': 5, '4': 1, '5': 11, '6': '.CaptchaSolverAntigate', '9': 0, '10': 'antigate'},
  ],
  '8': const [
    const {'1': 'SolverType'},
  ],
};

const CaptchaSolverAntigate$json = const {
  '1': 'CaptchaSolverAntigate',
  '2': const [
    const {'1': 'service_url', '3': 1, '4': 1, '5': 9, '10': 'serviceUrl'},
    const {'1': 'api_key', '3': 2, '4': 1, '5': 9, '10': 'apiKey'},
    const {'1': 'require_phrase', '3': 3, '4': 1, '5': 8, '10': 'requirePhrase'},
    const {'1': 'case_sensitive', '3': 4, '4': 1, '5': 8, '10': 'caseSensitive'},
    const {'1': 'characters', '3': 5, '4': 1, '5': 14, '6': '.CaptchaSolverAntigateCharacters', '10': 'characters'},
    const {'1': 'require_math', '3': 6, '4': 1, '5': 8, '10': 'requireMath'},
    const {'1': 'min_length', '3': 7, '4': 1, '5': 5, '10': 'minLength'},
    const {'1': 'max_length', '3': 8, '4': 1, '5': 5, '10': 'maxLength'},
  ],
};

const CrawlResponse$json = const {
  '1': 'CrawlResponse',
  '2': const [
    const {'1': 'body', '3': 1, '4': 1, '5': 12, '10': 'body'},
    const {'1': 'completed_at', '3': 2, '4': 1, '5': 9, '10': 'completedAt'},
    const {'1': 'content_type', '3': 3, '4': 1, '5': 9, '10': 'contentType'},
    const {'1': 'cost', '3': 4, '4': 1, '5': 1, '10': 'cost'},
    const {'1': 'duration', '3': 5, '4': 1, '5': 1, '10': 'duration'},
    const {'1': 'exception', '3': 6, '4': 1, '5': 9, '10': 'exception'},
    const {'1': 'headers', '3': 7, '4': 3, '5': 11, '6': '.Header', '10': 'headers'},
    const {'1': 'is_compressed', '3': 8, '4': 1, '5': 8, '10': 'isCompressed'},
    const {'1': 'is_success', '3': 9, '4': 1, '5': 8, '10': 'isSuccess'},
    const {'1': 'job_id', '3': 10, '4': 1, '5': 12, '10': 'jobId'},
    const {'1': 'started_at', '3': 11, '4': 1, '5': 9, '10': 'startedAt'},
    const {'1': 'status_code', '3': 12, '4': 1, '5': 5, '10': 'statusCode'},
    const {'1': 'url', '3': 13, '4': 1, '5': 9, '10': 'url'},
    const {'1': 'url_can', '3': 14, '4': 1, '5': 9, '10': 'urlCan'},
  ],
};

const Header$json = const {
  '1': 'Header',
  '2': const [
    const {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    const {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
};

const DomainLogin$json = const {
  '1': 'DomainLogin',
  '2': const [
    const {'1': 'domain', '3': 1, '4': 1, '5': 9, '10': 'domain'},
    const {'1': 'login_url', '3': 2, '4': 1, '5': 9, '10': 'loginUrl'},
    const {'1': 'login_test', '3': 3, '4': 1, '5': 9, '10': 'loginTest'},
    const {'1': 'users', '3': 5, '4': 3, '5': 11, '6': '.DomainLoginUser', '10': 'users'},
  ],
};

const DomainLoginUser$json = const {
  '1': 'DomainLoginUser',
  '2': const [
    const {'1': 'username', '3': 1, '4': 1, '5': 9, '10': 'username'},
    const {'1': 'password', '3': 2, '4': 1, '5': 9, '10': 'password'},
    const {'1': 'working', '3': 3, '4': 1, '5': 8, '10': 'working'},
  ],
};

const Event$json = const {
  '1': 'Event',
  '2': const [
    const {'1': 'subscription_id', '3': 1, '4': 2, '5': 5, '10': 'subscriptionId'},
    const {'1': 'job_list', '3': 2, '4': 1, '5': 11, '6': '.JobList', '9': 0, '10': 'jobList'},
    const {'1': 'schedule_list', '3': 7, '4': 1, '5': 11, '6': '.ScheduleList', '9': 0, '10': 'scheduleList'},
    const {'1': 'resource_frame', '3': 3, '4': 1, '5': 11, '6': '.ResourceFrame', '9': 0, '10': 'resourceFrame'},
    const {'1': 'subscription_closed', '3': 4, '4': 1, '5': 11, '6': '.SubscriptionClosed', '9': 0, '10': 'subscriptionClosed'},
    const {'1': 'sync_item', '3': 5, '4': 1, '5': 11, '6': '.SyncItem', '9': 0, '10': 'syncItem'},
    const {'1': 'task_tree', '3': 6, '4': 1, '5': 11, '6': '.TaskTree', '9': 0, '10': 'taskTree'},
  ],
  '8': const [
    const {'1': 'Body'},
  ],
};

const Job$json = const {
  '1': 'Job',
  '2': const [
    const {'1': 'job_id', '3': 1, '4': 2, '5': 12, '10': 'jobId'},
    const {'1': 'seeds', '3': 2, '4': 3, '5': 9, '10': 'seeds'},
    const {'1': 'policy', '3': 3, '4': 1, '5': 11, '6': '.Policy', '10': 'policy'},
    const {'1': 'name', '3': 4, '4': 1, '5': 9, '10': 'name'},
    const {'1': 'tags', '3': 5, '4': 3, '5': 9, '10': 'tags'},
    const {'1': 'run_state', '3': 6, '4': 1, '5': 14, '6': '.JobRunState', '10': 'runState'},
    const {'1': 'started_at', '3': 7, '4': 1, '5': 9, '10': 'startedAt'},
    const {'1': 'completed_at', '3': 8, '4': 1, '5': 9, '10': 'completedAt'},
    const {'1': 'item_count', '3': 9, '4': 1, '5': 5, '7': '-1', '10': 'itemCount'},
    const {'1': 'http_success_count', '3': 10, '4': 1, '5': 5, '7': '-1', '10': 'httpSuccessCount'},
    const {'1': 'http_error_count', '3': 11, '4': 1, '5': 5, '7': '-1', '10': 'httpErrorCount'},
    const {'1': 'exception_count', '3': 12, '4': 1, '5': 5, '7': '-1', '10': 'exceptionCount'},
    const {'1': 'http_status_counts', '3': 13, '4': 3, '5': 11, '6': '.Job.HttpStatusCountsEntry', '10': 'httpStatusCounts'},
  ],
  '3': const [Job_HttpStatusCountsEntry$json],
};

const Job_HttpStatusCountsEntry$json = const {
  '1': 'HttpStatusCountsEntry',
  '2': const [
    const {'1': 'key', '3': 1, '4': 1, '5': 5, '10': 'key'},
    const {'1': 'value', '3': 2, '4': 1, '5': 5, '10': 'value'},
  ],
  '7': const {'7': true},
};

const JobList$json = const {
  '1': 'JobList',
  '2': const [
    const {'1': 'jobs', '3': 1, '4': 3, '5': 11, '6': '.Job', '10': 'jobs'},
  ],
};

const Schedule$json = const {
  '1': 'Schedule',
  '2': const [
    const {'1': 'schedule_id', '3': 1, '4': 1, '5': 12, '10': 'scheduleId'},
    const {'1': 'created_at', '3': 2, '4': 1, '5': 9, '10': 'createdAt'},
    const {'1': 'updated_at', '3': 3, '4': 1, '5': 9, '10': 'updatedAt'},
    const {'1': 'enabled', '3': 4, '4': 1, '5': 8, '10': 'enabled'},
    const {'1': 'time_unit', '3': 5, '4': 1, '5': 14, '6': '.ScheduleTimeUnit', '10': 'timeUnit'},
    const {'1': 'num_units', '3': 6, '4': 1, '5': 5, '10': 'numUnits'},
    const {'1': 'timing', '3': 7, '4': 1, '5': 14, '6': '.ScheduleTiming', '10': 'timing'},
    const {'1': 'schedule_name', '3': 8, '4': 1, '5': 9, '10': 'scheduleName'},
    const {'1': 'job_name', '3': 9, '4': 1, '5': 9, '10': 'jobName'},
    const {'1': 'seeds', '3': 10, '4': 3, '5': 9, '10': 'seeds'},
    const {'1': 'policy_id', '3': 11, '4': 1, '5': 12, '10': 'policyId'},
    const {'1': 'tags', '3': 12, '4': 3, '5': 9, '10': 'tags'},
    const {'1': 'job_count', '3': 13, '4': 1, '5': 5, '10': 'jobCount'},
  ],
};

const ScheduleList$json = const {
  '1': 'ScheduleList',
  '2': const [
    const {'1': 'schedules', '3': 1, '4': 3, '5': 11, '6': '.Schedule', '10': 'schedules'},
  ],
};

const Page$json = const {
  '1': 'Page',
  '2': const [
    const {'1': 'limit', '3': 1, '4': 1, '5': 5, '7': '10', '10': 'limit'},
    const {'1': 'offset', '3': 2, '4': 1, '5': 5, '10': 'offset'},
  ],
};

const Policy$json = const {
  '1': 'Policy',
  '2': const [
    const {'1': 'policy_id', '3': 1, '4': 1, '5': 12, '10': 'policyId'},
    const {'1': 'name', '3': 2, '4': 1, '5': 9, '10': 'name'},
    const {'1': 'created_at', '3': 3, '4': 1, '5': 9, '10': 'createdAt'},
    const {'1': 'updated_at', '3': 4, '4': 1, '5': 9, '10': 'updatedAt'},
    const {'1': 'captcha_solver_id', '3': 14, '4': 1, '5': 12, '10': 'captchaSolverId'},
    const {'1': 'authentication', '3': 6, '4': 1, '5': 11, '6': '.PolicyAuthentication', '10': 'authentication'},
    const {'1': 'limits', '3': 7, '4': 1, '5': 11, '6': '.PolicyLimits', '10': 'limits'},
    const {'1': 'proxy_rules', '3': 8, '4': 3, '5': 11, '6': '.PolicyProxyRule', '10': 'proxyRules'},
    const {'1': 'mime_type_rules', '3': 9, '4': 3, '5': 11, '6': '.PolicyMimeTypeRule', '10': 'mimeTypeRules'},
    const {'1': 'robots_txt', '3': 10, '4': 1, '5': 11, '6': '.PolicyRobotsTxt', '10': 'robotsTxt'},
    const {'1': 'url_normalization', '3': 13, '4': 1, '5': 11, '6': '.PolicyUrlNormalization', '10': 'urlNormalization'},
    const {'1': 'url_rules', '3': 11, '4': 3, '5': 11, '6': '.PolicyUrlRule', '10': 'urlRules'},
    const {'1': 'user_agents', '3': 12, '4': 3, '5': 11, '6': '.PolicyUserAgent', '10': 'userAgents'},
  ],
};

const PolicyAuthentication$json = const {
  '1': 'PolicyAuthentication',
  '2': const [
    const {'1': 'enabled', '3': 1, '4': 1, '5': 8, '10': 'enabled'},
  ],
};

const PolicyLimits$json = const {
  '1': 'PolicyLimits',
  '2': const [
    const {'1': 'max_cost', '3': 1, '4': 1, '5': 1, '10': 'maxCost'},
    const {'1': 'max_duration', '3': 2, '4': 1, '5': 1, '10': 'maxDuration'},
    const {'1': 'max_items', '3': 3, '4': 1, '5': 5, '10': 'maxItems'},
  ],
};

const PolicyMimeTypeRule$json = const {
  '1': 'PolicyMimeTypeRule',
  '2': const [
    const {'1': 'pattern', '3': 1, '4': 1, '5': 9, '10': 'pattern'},
    const {'1': 'match', '3': 2, '4': 1, '5': 14, '6': '.PatternMatch', '10': 'match'},
    const {'1': 'save', '3': 3, '4': 1, '5': 8, '10': 'save'},
  ],
};

const PolicyProxyRule$json = const {
  '1': 'PolicyProxyRule',
  '2': const [
    const {'1': 'pattern', '3': 1, '4': 1, '5': 9, '10': 'pattern'},
    const {'1': 'match', '3': 2, '4': 1, '5': 14, '6': '.PatternMatch', '10': 'match'},
    const {'1': 'proxy_url', '3': 3, '4': 1, '5': 9, '10': 'proxyUrl'},
  ],
};

const PolicyRobotsTxt$json = const {
  '1': 'PolicyRobotsTxt',
  '2': const [
    const {'1': 'usage', '3': 1, '4': 2, '5': 14, '6': '.PolicyRobotsTxt.Usage', '10': 'usage'},
  ],
  '4': const [PolicyRobotsTxt_Usage$json],
};

const PolicyRobotsTxt_Usage$json = const {
  '1': 'Usage',
  '2': const [
    const {'1': 'OBEY', '2': 1},
    const {'1': 'INVERT', '2': 2},
    const {'1': 'IGNORE', '2': 3},
  ],
};

const PolicyUrlNormalization$json = const {
  '1': 'PolicyUrlNormalization',
  '2': const [
    const {'1': 'enabled', '3': 1, '4': 1, '5': 8, '10': 'enabled'},
    const {'1': 'strip_parameters', '3': 2, '4': 3, '5': 9, '10': 'stripParameters'},
  ],
};

const PolicyUrlRule$json = const {
  '1': 'PolicyUrlRule',
  '2': const [
    const {'1': 'pattern', '3': 1, '4': 1, '5': 9, '10': 'pattern'},
    const {'1': 'match', '3': 2, '4': 1, '5': 14, '6': '.PatternMatch', '10': 'match'},
    const {'1': 'action', '3': 3, '4': 1, '5': 14, '6': '.PolicyUrlRule.Action', '10': 'action'},
    const {'1': 'amount', '3': 4, '4': 1, '5': 1, '10': 'amount'},
  ],
  '4': const [PolicyUrlRule_Action$json],
};

const PolicyUrlRule_Action$json = const {
  '1': 'Action',
  '2': const [
    const {'1': 'ADD', '2': 1},
    const {'1': 'MULTIPLY', '2': 2},
  ],
};

const PolicyUserAgent$json = const {
  '1': 'PolicyUserAgent',
  '2': const [
    const {'1': 'name', '3': 1, '4': 2, '5': 9, '10': 'name'},
  ],
};

const Request$json = const {
  '1': 'Request',
  '2': const [
    const {'1': 'request_id', '3': 1, '4': 2, '5': 5, '10': 'requestId'},
    const {'1': 'delete_captcha_solver', '3': 31, '4': 1, '5': 11, '6': '.RequestDeleteCaptchaSolver', '9': 0, '10': 'deleteCaptchaSolver'},
    const {'1': 'get_captcha_solver', '3': 28, '4': 1, '5': 11, '6': '.RequestGetCaptchaSolver', '9': 0, '10': 'getCaptchaSolver'},
    const {'1': 'list_captcha_solvers', '3': 29, '4': 1, '5': 11, '6': '.RequestListCaptchaSolvers', '9': 0, '10': 'listCaptchaSolvers'},
    const {'1': 'set_captcha_solver', '3': 30, '4': 1, '5': 11, '6': '.RequestSetCaptchaSolver', '9': 0, '10': 'setCaptchaSolver'},
    const {'1': 'delete_job', '3': 3, '4': 1, '5': 11, '6': '.RequestDeleteJob', '9': 0, '10': 'deleteJob'},
    const {'1': 'get_job', '3': 6, '4': 1, '5': 11, '6': '.RequestGetJob', '9': 0, '10': 'getJob'},
    const {'1': 'get_job_items', '3': 7, '4': 1, '5': 11, '6': '.RequestGetJobItems', '9': 0, '10': 'getJobItems'},
    const {'1': 'list_jobs', '3': 11, '4': 1, '5': 11, '6': '.RequestListJobs', '9': 0, '10': 'listJobs'},
    const {'1': 'set_job', '3': 16, '4': 1, '5': 11, '6': '.RequestSetJob', '9': 0, '10': 'setJob'},
    const {'1': 'delete_schedule', '3': 24, '4': 1, '5': 11, '6': '.RequestDeleteSchedule', '9': 0, '10': 'deleteSchedule'},
    const {'1': 'get_schedule', '3': 25, '4': 1, '5': 11, '6': '.RequestGetSchedule', '9': 0, '10': 'getSchedule'},
    const {'1': 'list_schedules', '3': 26, '4': 1, '5': 11, '6': '.RequestListSchedules', '9': 0, '10': 'listSchedules'},
    const {'1': 'list_schedule_jobs', '3': 32, '4': 1, '5': 11, '6': '.RequestListScheduleJobs', '9': 0, '10': 'listScheduleJobs'},
    const {'1': 'set_schedule', '3': 27, '4': 1, '5': 11, '6': '.RequestSetSchedule', '9': 0, '10': 'setSchedule'},
    const {'1': 'delete_policy', '3': 4, '4': 1, '5': 11, '6': '.RequestDeletePolicy', '9': 0, '10': 'deletePolicy'},
    const {'1': 'get_policy', '3': 8, '4': 1, '5': 11, '6': '.RequestGetPolicy', '9': 0, '10': 'getPolicy'},
    const {'1': 'list_policies', '3': 12, '4': 1, '5': 11, '6': '.RequestListPolicies', '9': 0, '10': 'listPolicies'},
    const {'1': 'set_policy', '3': 17, '4': 1, '5': 11, '6': '.RequestSetPolicy', '9': 0, '10': 'setPolicy'},
    const {'1': 'delete_domain_login', '3': 2, '4': 1, '5': 11, '6': '.RequestDeleteDomainLogin', '9': 0, '10': 'deleteDomainLogin'},
    const {'1': 'get_domain_login', '3': 5, '4': 1, '5': 11, '6': '.RequestGetDomainLogin', '9': 0, '10': 'getDomainLogin'},
    const {'1': 'list_domain_logins', '3': 10, '4': 1, '5': 11, '6': '.RequestListDomainLogins', '9': 0, '10': 'listDomainLogins'},
    const {'1': 'set_domain_login', '3': 15, '4': 1, '5': 11, '6': '.RequestSetDomainLogin', '9': 0, '10': 'setDomainLogin'},
    const {'1': 'list_rate_limits', '3': 9, '4': 1, '5': 11, '6': '.RequestListRateLimits', '9': 0, '10': 'listRateLimits'},
    const {'1': 'set_rate_limit', '3': 18, '4': 1, '5': 11, '6': '.RequestSetRateLimit', '9': 0, '10': 'setRateLimit'},
    const {'1': 'performance_profile', '3': 13, '4': 1, '5': 11, '6': '.RequestPerformanceProfile', '9': 0, '10': 'performanceProfile'},
    const {'1': 'subscribe_job_status', '3': 19, '4': 1, '5': 11, '6': '.RequestSubscribeJobStatus', '9': 0, '10': 'subscribeJobStatus'},
    const {'1': 'subscribe_job_sync', '3': 20, '4': 1, '5': 11, '6': '.RequestSubscribeJobSync', '9': 0, '10': 'subscribeJobSync'},
    const {'1': 'subscribe_resource_monitor', '3': 21, '4': 1, '5': 11, '6': '.RequestSubscribeResourceMonitor', '9': 0, '10': 'subscribeResourceMonitor'},
    const {'1': 'subscribe_task_monitor', '3': 22, '4': 1, '5': 11, '6': '.RequestSubscribeTaskMonitor', '9': 0, '10': 'subscribeTaskMonitor'},
    const {'1': 'unsubscribe', '3': 23, '4': 1, '5': 11, '6': '.RequestUnsubscribe', '9': 0, '10': 'unsubscribe'},
  ],
  '8': const [
    const {'1': 'Command'},
  ],
};

const Response$json = const {
  '1': 'Response',
  '2': const [
    const {'1': 'request_id', '3': 1, '4': 2, '5': 5, '10': 'requestId'},
    const {'1': 'is_success', '3': 2, '4': 2, '5': 8, '10': 'isSuccess'},
    const {'1': 'error_message', '3': 3, '4': 1, '5': 9, '10': 'errorMessage'},
    const {'1': 'solver', '3': 22, '4': 1, '5': 11, '6': '.CaptchaSolver', '9': 0, '10': 'solver'},
    const {'1': 'new_solver', '3': 24, '4': 1, '5': 11, '6': '.ResponseNewCaptchaSolver', '9': 0, '10': 'newSolver'},
    const {'1': 'list_captcha_solvers', '3': 23, '4': 1, '5': 11, '6': '.ResponseListCaptchaSolvers', '9': 0, '10': 'listCaptchaSolvers'},
    const {'1': 'domain_login', '3': 5, '4': 1, '5': 11, '6': '.DomainLogin', '9': 0, '10': 'domainLogin'},
    const {'1': 'domain_login_user', '3': 6, '4': 1, '5': 11, '6': '.DomainLoginUser', '9': 0, '10': 'domainLoginUser'},
    const {'1': 'list_domain_logins', '3': 9, '4': 1, '5': 11, '6': '.ResponseListDomainLogins', '9': 0, '10': 'listDomainLogins'},
    const {'1': 'job', '3': 7, '4': 1, '5': 11, '6': '.Job', '9': 0, '10': 'job'},
    const {'1': 'new_job', '3': 14, '4': 1, '5': 11, '6': '.ResponseNewJob', '9': 0, '10': 'newJob'},
    const {'1': 'list_items', '3': 10, '4': 1, '5': 11, '6': '.ResponseListItems', '9': 0, '10': 'listItems'},
    const {'1': 'list_jobs', '3': 11, '4': 1, '5': 11, '6': '.ResponseListJobs', '9': 0, '10': 'listJobs'},
    const {'1': 'schedule', '3': 19, '4': 1, '5': 11, '6': '.Schedule', '9': 0, '10': 'schedule'},
    const {'1': 'new_schedule', '3': 21, '4': 1, '5': 11, '6': '.ResponseNewSchedule', '9': 0, '10': 'newSchedule'},
    const {'1': 'list_schedules', '3': 20, '4': 1, '5': 11, '6': '.ResponseListSchedules', '9': 0, '10': 'listSchedules'},
    const {'1': 'list_schedule_jobs', '3': 25, '4': 1, '5': 11, '6': '.ResponseListScheduleJobs', '9': 0, '10': 'listScheduleJobs'},
    const {'1': 'policy', '3': 8, '4': 1, '5': 11, '6': '.Policy', '9': 0, '10': 'policy'},
    const {'1': 'new_policy', '3': 15, '4': 1, '5': 11, '6': '.ResponseNewPolicy', '9': 0, '10': 'newPolicy'},
    const {'1': 'list_policies', '3': 12, '4': 1, '5': 11, '6': '.ResponseListPolicies', '9': 0, '10': 'listPolicies'},
    const {'1': 'list_rate_limits', '3': 13, '4': 1, '5': 11, '6': '.ResponseListRateLimits', '9': 0, '10': 'listRateLimits'},
    const {'1': 'new_subscription', '3': 16, '4': 1, '5': 11, '6': '.ResponseNewSubscription', '9': 0, '10': 'newSubscription'},
    const {'1': 'performance_profile', '3': 17, '4': 1, '5': 11, '6': '.ResponsePerformanceProfile', '9': 0, '10': 'performanceProfile'},
  ],
  '8': const [
    const {'1': 'Body'},
  ],
};

const RequestDeleteCaptchaSolver$json = const {
  '1': 'RequestDeleteCaptchaSolver',
  '2': const [
    const {'1': 'solver_id', '3': 1, '4': 1, '5': 12, '10': 'solverId'},
  ],
};

const RequestGetCaptchaSolver$json = const {
  '1': 'RequestGetCaptchaSolver',
  '2': const [
    const {'1': 'solver_id', '3': 1, '4': 2, '5': 12, '10': 'solverId'},
  ],
};

const RequestListCaptchaSolvers$json = const {
  '1': 'RequestListCaptchaSolvers',
  '2': const [
    const {'1': 'page', '3': 1, '4': 1, '5': 11, '6': '.Page', '10': 'page'},
  ],
};

const ResponseListCaptchaSolvers$json = const {
  '1': 'ResponseListCaptchaSolvers',
  '2': const [
    const {'1': 'solvers', '3': 1, '4': 3, '5': 11, '6': '.CaptchaSolver', '10': 'solvers'},
    const {'1': 'total', '3': 2, '4': 1, '5': 5, '10': 'total'},
  ],
};

const RequestSetCaptchaSolver$json = const {
  '1': 'RequestSetCaptchaSolver',
  '2': const [
    const {'1': 'solver', '3': 1, '4': 1, '5': 11, '6': '.CaptchaSolver', '10': 'solver'},
  ],
};

const ResponseNewCaptchaSolver$json = const {
  '1': 'ResponseNewCaptchaSolver',
  '2': const [
    const {'1': 'solver_id', '3': 1, '4': 2, '5': 12, '10': 'solverId'},
  ],
};

const RequestDeleteDomainLogin$json = const {
  '1': 'RequestDeleteDomainLogin',
  '2': const [
    const {'1': 'domain', '3': 1, '4': 1, '5': 9, '10': 'domain'},
  ],
};

const RequestGetDomainLogin$json = const {
  '1': 'RequestGetDomainLogin',
  '2': const [
    const {'1': 'domain', '3': 1, '4': 2, '5': 9, '10': 'domain'},
  ],
};

const RequestListDomainLogins$json = const {
  '1': 'RequestListDomainLogins',
  '2': const [
    const {'1': 'page', '3': 1, '4': 1, '5': 11, '6': '.Page', '10': 'page'},
  ],
};

const ResponseListDomainLogins$json = const {
  '1': 'ResponseListDomainLogins',
  '2': const [
    const {'1': 'logins', '3': 1, '4': 3, '5': 11, '6': '.DomainLogin', '10': 'logins'},
    const {'1': 'total', '3': 2, '4': 1, '5': 5, '10': 'total'},
  ],
};

const RequestSetDomainLogin$json = const {
  '1': 'RequestSetDomainLogin',
  '2': const [
    const {'1': 'login', '3': 1, '4': 1, '5': 11, '6': '.DomainLogin', '10': 'login'},
  ],
};

const RequestDeleteJob$json = const {
  '1': 'RequestDeleteJob',
  '2': const [
    const {'1': 'job_id', '3': 1, '4': 2, '5': 12, '10': 'jobId'},
  ],
};

const RequestGetJob$json = const {
  '1': 'RequestGetJob',
  '2': const [
    const {'1': 'job_id', '3': 1, '4': 2, '5': 12, '10': 'jobId'},
  ],
};

const RequestListJobs$json = const {
  '1': 'RequestListJobs',
  '2': const [
    const {'1': 'page', '3': 1, '4': 1, '5': 11, '6': '.Page', '10': 'page'},
    const {'1': 'started_after', '3': 2, '4': 1, '5': 9, '10': 'startedAfter'},
    const {'1': 'tag', '3': 3, '4': 1, '5': 9, '10': 'tag'},
    const {'1': 'schedule_id', '3': 4, '4': 1, '5': 12, '10': 'scheduleId'},
  ],
};

const ResponseListJobs$json = const {
  '1': 'ResponseListJobs',
  '2': const [
    const {'1': 'jobs', '3': 1, '4': 3, '5': 11, '6': '.Job', '10': 'jobs'},
    const {'1': 'total', '3': 2, '4': 1, '5': 5, '10': 'total'},
  ],
};

const RequestSetJob$json = const {
  '1': 'RequestSetJob',
  '2': const [
    const {'1': 'job_id', '3': 1, '4': 1, '5': 12, '10': 'jobId'},
    const {'1': 'run_state', '3': 2, '4': 1, '5': 14, '6': '.JobRunState', '10': 'runState'},
    const {'1': 'policy_id', '3': 3, '4': 1, '5': 12, '10': 'policyId'},
    const {'1': 'seeds', '3': 4, '4': 3, '5': 9, '10': 'seeds'},
    const {'1': 'name', '3': 5, '4': 1, '5': 9, '10': 'name'},
    const {'1': 'tags', '3': 6, '4': 3, '5': 9, '10': 'tags'},
  ],
};

const ResponseNewJob$json = const {
  '1': 'ResponseNewJob',
  '2': const [
    const {'1': 'job_id', '3': 1, '4': 2, '5': 12, '10': 'jobId'},
  ],
};

const RequestGetJobItems$json = const {
  '1': 'RequestGetJobItems',
  '2': const [
    const {'1': 'job_id', '3': 1, '4': 2, '5': 12, '10': 'jobId'},
    const {'1': 'include_success', '3': 2, '4': 1, '5': 8, '10': 'includeSuccess'},
    const {'1': 'include_error', '3': 3, '4': 1, '5': 8, '10': 'includeError'},
    const {'1': 'include_exception', '3': 4, '4': 1, '5': 8, '10': 'includeException'},
    const {'1': 'compression_ok', '3': 5, '4': 1, '5': 8, '7': 'true', '10': 'compressionOk'},
    const {'1': 'page', '3': 6, '4': 1, '5': 11, '6': '.Page', '10': 'page'},
  ],
};

const ResponseListItems$json = const {
  '1': 'ResponseListItems',
  '2': const [
    const {'1': 'items', '3': 1, '4': 3, '5': 11, '6': '.CrawlResponse', '10': 'items'},
    const {'1': 'total', '3': 2, '4': 1, '5': 5, '10': 'total'},
  ],
};

const RequestDeleteSchedule$json = const {
  '1': 'RequestDeleteSchedule',
  '2': const [
    const {'1': 'schedule_id', '3': 1, '4': 2, '5': 12, '10': 'scheduleId'},
  ],
};

const RequestGetSchedule$json = const {
  '1': 'RequestGetSchedule',
  '2': const [
    const {'1': 'schedule_id', '3': 1, '4': 2, '5': 12, '10': 'scheduleId'},
  ],
};

const RequestListSchedules$json = const {
  '1': 'RequestListSchedules',
  '2': const [
    const {'1': 'page', '3': 1, '4': 1, '5': 11, '6': '.Page', '10': 'page'},
  ],
};

const ResponseListSchedules$json = const {
  '1': 'ResponseListSchedules',
  '2': const [
    const {'1': 'schedules', '3': 1, '4': 3, '5': 11, '6': '.Schedule', '10': 'schedules'},
    const {'1': 'total', '3': 2, '4': 1, '5': 5, '10': 'total'},
  ],
};

const RequestListScheduleJobs$json = const {
  '1': 'RequestListScheduleJobs',
  '2': const [
    const {'1': 'schedule_id', '3': 1, '4': 2, '5': 12, '10': 'scheduleId'},
    const {'1': 'page', '3': 2, '4': 1, '5': 11, '6': '.Page', '10': 'page'},
  ],
};

const ResponseListScheduleJobs$json = const {
  '1': 'ResponseListScheduleJobs',
  '2': const [
    const {'1': 'jobs', '3': 1, '4': 3, '5': 11, '6': '.Job', '10': 'jobs'},
    const {'1': 'total', '3': 2, '4': 1, '5': 5, '10': 'total'},
  ],
};

const RequestSetSchedule$json = const {
  '1': 'RequestSetSchedule',
  '2': const [
    const {'1': 'schedule', '3': 1, '4': 1, '5': 11, '6': '.Schedule', '10': 'schedule'},
  ],
};

const ResponseNewSchedule$json = const {
  '1': 'ResponseNewSchedule',
  '2': const [
    const {'1': 'schedule_id', '3': 1, '4': 2, '5': 12, '10': 'scheduleId'},
  ],
};

const RequestDeletePolicy$json = const {
  '1': 'RequestDeletePolicy',
  '2': const [
    const {'1': 'policy_id', '3': 1, '4': 2, '5': 12, '10': 'policyId'},
  ],
};

const RequestGetPolicy$json = const {
  '1': 'RequestGetPolicy',
  '2': const [
    const {'1': 'policy_id', '3': 1, '4': 2, '5': 12, '10': 'policyId'},
  ],
};

const RequestListPolicies$json = const {
  '1': 'RequestListPolicies',
  '2': const [
    const {'1': 'page', '3': 1, '4': 1, '5': 11, '6': '.Page', '10': 'page'},
  ],
};

const ResponseListPolicies$json = const {
  '1': 'ResponseListPolicies',
  '2': const [
    const {'1': 'policies', '3': 1, '4': 3, '5': 11, '6': '.Policy', '10': 'policies'},
    const {'1': 'total', '3': 2, '4': 1, '5': 5, '10': 'total'},
  ],
};

const RequestSetPolicy$json = const {
  '1': 'RequestSetPolicy',
  '2': const [
    const {'1': 'policy', '3': 1, '4': 2, '5': 11, '6': '.Policy', '10': 'policy'},
  ],
};

const ResponseNewPolicy$json = const {
  '1': 'ResponseNewPolicy',
  '2': const [
    const {'1': 'policy_id', '3': 1, '4': 2, '5': 12, '10': 'policyId'},
  ],
};

const RateLimit$json = const {
  '1': 'RateLimit',
  '2': const [
    const {'1': 'name', '3': 1, '4': 1, '5': 9, '10': 'name'},
    const {'1': 'delay', '3': 2, '4': 1, '5': 2, '10': 'delay'},
    const {'1': 'token', '3': 3, '4': 1, '5': 12, '10': 'token'},
    const {'1': 'domain', '3': 4, '4': 1, '5': 9, '10': 'domain'},
  ],
};

const RequestListRateLimits$json = const {
  '1': 'RequestListRateLimits',
  '2': const [
    const {'1': 'page', '3': 1, '4': 1, '5': 11, '6': '.Page', '10': 'page'},
  ],
};

const ResponseListRateLimits$json = const {
  '1': 'ResponseListRateLimits',
  '2': const [
    const {'1': 'rate_limits', '3': 1, '4': 3, '5': 11, '6': '.RateLimit', '10': 'rateLimits'},
    const {'1': 'total', '3': 2, '4': 1, '5': 5, '10': 'total'},
  ],
};

const RequestSetRateLimit$json = const {
  '1': 'RequestSetRateLimit',
  '2': const [
    const {'1': 'domain', '3': 1, '4': 1, '5': 9, '10': 'domain'},
    const {'1': 'delay', '3': 2, '4': 1, '5': 2, '10': 'delay'},
  ],
};

const RequestPerformanceProfile$json = const {
  '1': 'RequestPerformanceProfile',
  '2': const [
    const {'1': 'duration', '3': 1, '4': 1, '5': 1, '7': '5', '10': 'duration'},
    const {'1': 'sort_by', '3': 2, '4': 1, '5': 9, '7': 'total_time', '10': 'sortBy'},
    const {'1': 'top_n', '3': 3, '4': 1, '5': 5, '10': 'topN'},
  ],
};

const PerformanceProfileFunction$json = const {
  '1': 'PerformanceProfileFunction',
  '2': const [
    const {'1': 'file', '3': 1, '4': 1, '5': 9, '10': 'file'},
    const {'1': 'line_number', '3': 2, '4': 1, '5': 5, '10': 'lineNumber'},
    const {'1': 'function', '3': 3, '4': 1, '5': 9, '10': 'function'},
    const {'1': 'calls', '3': 4, '4': 1, '5': 5, '10': 'calls'},
    const {'1': 'non_recursive_calls', '3': 5, '4': 1, '5': 5, '10': 'nonRecursiveCalls'},
    const {'1': 'total_time', '3': 6, '4': 1, '5': 1, '10': 'totalTime'},
    const {'1': 'cumulative_time', '3': 7, '4': 1, '5': 1, '10': 'cumulativeTime'},
  ],
};

const ResponsePerformanceProfile$json = const {
  '1': 'ResponsePerformanceProfile',
  '2': const [
    const {'1': 'total_calls', '3': 1, '4': 1, '5': 5, '10': 'totalCalls'},
    const {'1': 'total_time', '3': 2, '4': 1, '5': 1, '10': 'totalTime'},
    const {'1': 'functions', '3': 3, '4': 3, '5': 11, '6': '.PerformanceProfileFunction', '10': 'functions'},
  ],
};

const RequestSubscribeJobStatus$json = const {
  '1': 'RequestSubscribeJobStatus',
  '2': const [
    const {'1': 'min_interval', '3': 1, '4': 1, '5': 1, '7': '1', '10': 'minInterval'},
  ],
};

const RequestSubscribeJobSync$json = const {
  '1': 'RequestSubscribeJobSync',
  '2': const [
    const {'1': 'job_id', '3': 1, '4': 2, '5': 12, '10': 'jobId'},
    const {'1': 'sync_token', '3': 2, '4': 1, '5': 12, '10': 'syncToken'},
    const {'1': 'compression_ok', '3': 3, '4': 1, '5': 8, '7': 'true', '10': 'compressionOk'},
  ],
};

const SyncItem$json = const {
  '1': 'SyncItem',
  '2': const [
    const {'1': 'item', '3': 1, '4': 2, '5': 11, '6': '.CrawlResponse', '10': 'item'},
    const {'1': 'token', '3': 2, '4': 2, '5': 12, '10': 'token'},
  ],
};

const ServerMessage$json = const {
  '1': 'ServerMessage',
  '2': const [
    const {'1': 'event', '3': 1, '4': 1, '5': 11, '6': '.Event', '9': 0, '10': 'event'},
    const {'1': 'response', '3': 2, '4': 1, '5': 11, '6': '.Response', '9': 0, '10': 'response'},
  ],
  '8': const [
    const {'1': 'MessageType'},
  ],
};

const RequestSubscribeResourceMonitor$json = const {
  '1': 'RequestSubscribeResourceMonitor',
  '2': const [
    const {'1': 'history', '3': 1, '4': 1, '5': 5, '7': '300', '10': 'history'},
  ],
};

const RequestSubscribeTaskMonitor$json = const {
  '1': 'RequestSubscribeTaskMonitor',
  '2': const [
    const {'1': 'period', '3': 1, '4': 1, '5': 1, '7': '3', '10': 'period'},
    const {'1': 'top_n', '3': 2, '4': 1, '5': 5, '7': '20', '10': 'topN'},
  ],
};

const ResponseNewSubscription$json = const {
  '1': 'ResponseNewSubscription',
  '2': const [
    const {'1': 'subscription_id', '3': 1, '4': 2, '5': 5, '10': 'subscriptionId'},
  ],
};

const RequestUnsubscribe$json = const {
  '1': 'RequestUnsubscribe',
  '2': const [
    const {'1': 'subscription_id', '3': 1, '4': 2, '5': 5, '10': 'subscriptionId'},
  ],
};

const SubscriptionClosed$json = const {
  '1': 'SubscriptionClosed',
  '2': const [
    const {'1': 'reason', '3': 1, '4': 2, '5': 14, '6': '.SubscriptionClosed.Reason', '10': 'reason'},
    const {'1': 'message', '3': 2, '4': 1, '5': 9, '10': 'message'},
  ],
  '4': const [SubscriptionClosed_Reason$json],
};

const SubscriptionClosed_Reason$json = const {
  '1': 'Reason',
  '2': const [
    const {'1': 'COMPLETE', '2': 1},
    const {'1': 'ERROR', '2': 2},
  ],
};

const ResourceFrame$json = const {
  '1': 'ResourceFrame',
  '2': const [
    const {'1': 'timestamp', '3': 1, '4': 1, '5': 9, '10': 'timestamp'},
    const {'1': 'cpus', '3': 2, '4': 3, '5': 11, '6': '.ResourceFrameCpu', '10': 'cpus'},
    const {'1': 'memory', '3': 3, '4': 1, '5': 11, '6': '.ResourceFrameMemory', '10': 'memory'},
    const {'1': 'disks', '3': 4, '4': 3, '5': 11, '6': '.ResourceFrameDisk', '10': 'disks'},
    const {'1': 'networks', '3': 5, '4': 3, '5': 11, '6': '.ResourceFrameNetwork', '10': 'networks'},
    const {'1': 'jobs', '3': 6, '4': 3, '5': 11, '6': '.ResourceFrameJob', '10': 'jobs'},
    const {'1': 'current_downloads', '3': 7, '4': 1, '5': 5, '10': 'currentDownloads'},
    const {'1': 'maximum_downloads', '3': 8, '4': 1, '5': 5, '10': 'maximumDownloads'},
    const {'1': 'rate_limiter', '3': 9, '4': 1, '5': 5, '10': 'rateLimiter'},
  ],
};

const ResourceFrameCpu$json = const {
  '1': 'ResourceFrameCpu',
  '2': const [
    const {'1': 'usage', '3': 1, '4': 1, '5': 1, '10': 'usage'},
  ],
};

const ResourceFrameJob$json = const {
  '1': 'ResourceFrameJob',
  '2': const [
    const {'1': 'job_id', '3': 1, '4': 1, '5': 12, '10': 'jobId'},
    const {'1': 'name', '3': 2, '4': 1, '5': 9, '10': 'name'},
    const {'1': 'current_downloads', '3': 3, '4': 1, '5': 5, '10': 'currentDownloads'},
  ],
};

const ResourceFrameDisk$json = const {
  '1': 'ResourceFrameDisk',
  '2': const [
    const {'1': 'mount', '3': 1, '4': 1, '5': 9, '10': 'mount'},
    const {'1': 'used', '3': 2, '4': 1, '5': 3, '10': 'used'},
    const {'1': 'total', '3': 3, '4': 1, '5': 3, '10': 'total'},
  ],
};

const ResourceFrameMemory$json = const {
  '1': 'ResourceFrameMemory',
  '2': const [
    const {'1': 'used', '3': 1, '4': 1, '5': 3, '10': 'used'},
    const {'1': 'total', '3': 2, '4': 1, '5': 3, '10': 'total'},
  ],
};

const ResourceFrameNetwork$json = const {
  '1': 'ResourceFrameNetwork',
  '2': const [
    const {'1': 'name', '3': 1, '4': 1, '5': 9, '10': 'name'},
    const {'1': 'sent', '3': 2, '4': 1, '5': 3, '10': 'sent'},
    const {'1': 'received', '3': 3, '4': 1, '5': 3, '10': 'received'},
  ],
};

const TaskTree$json = const {
  '1': 'TaskTree',
  '2': const [
    const {'1': 'name', '3': 1, '4': 1, '5': 9, '10': 'name'},
    const {'1': 'subtasks', '3': 2, '4': 3, '5': 11, '6': '.TaskTree', '10': 'subtasks'},
  ],
};

