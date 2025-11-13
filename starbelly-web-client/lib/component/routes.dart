import 'package:angular_router/angular_router.dart';

import 'package:starbelly/component/captcha/detail.template.dart' as captcha_detail_template;
import 'package:starbelly/component/captcha/list.template.dart' as captcha_list_template;
import 'package:starbelly/component/credential/detail.template.dart' as credential_detail_template;
import 'package:starbelly/component/credential/list.template.dart' as credential_list_template;
import 'package:starbelly/component/dashboard.template.dart' as dashboard_template;
import 'package:starbelly/component/policy/detail.template.dart' as policy_detail_template;
import 'package:starbelly/component/policy/list.template.dart' as policy_list_template;
import 'package:starbelly/component/rate_limit.template.dart' as rate_limit_template;
import 'package:starbelly/component/result/detail.template.dart' as result_detail_template;
import 'package:starbelly/component/result/error.template.dart' as result_error_template;
import 'package:starbelly/component/result/exception.template.dart' as result_exception_template;
import 'package:starbelly/component/result/list.template.dart' as result_list_template;
import 'package:starbelly/component/result/policy.template.dart' as result_policy_template;
import 'package:starbelly/component/result/success.template.dart' as result_success_template;
import 'package:starbelly/component/schedule/jobs.template.dart' as schedule_jobs_template;
import 'package:starbelly/component/schedule/list.template.dart' as schedule_list_template;
import 'package:starbelly/component/schedule/detail.template.dart' as schedule_detail_template;
import 'package:starbelly/component/start.template.dart' as start_template;
import 'package:starbelly/component/system/profile.template.dart' as system_profile_template;
import 'package:starbelly/component/system/resources.template.dart' as system_resources_template;
import 'package:starbelly/component/system/tasks.template.dart' as system_tasks_template;

class Routes {
    static final dashboard = RouteDefinition(
        routePath: RoutePath(path: 'dashboard'),
        component: dashboard_template.DashboardViewNgFactory);

    static final captchaCreate = RouteDefinition(
        routePath: RoutePath(path: 'captcha/new'),
        component: captcha_detail_template.CaptchaDetailViewNgFactory);
    static final captchaDetail = RouteDefinition(
        routePath: RoutePath(path: 'captcha/:id'),
        component: captcha_detail_template.CaptchaDetailViewNgFactory);
    static final captchaList = RouteDefinition(
        routePath: RoutePath(path: 'captcha'),
        component: captcha_list_template.CaptchaListViewNgFactory);

    static final credentialCreate = RouteDefinition(
        routePath: RoutePath(path: 'credential/new'),
        component: credential_detail_template.CredentialDetailViewNgFactory);
    static final credentialDetail = RouteDefinition(
        routePath: RoutePath(path: 'credential/:domain'),
        component: credential_detail_template.CredentialDetailViewNgFactory);
    static final credentialList = RouteDefinition(
        routePath: RoutePath(path: 'credential'),
        component: credential_list_template.CredentialListViewNgFactory);

    static final policyCreate = RouteDefinition(
        routePath: RoutePath(path: 'policy/new'),
        component: policy_detail_template.PolicyDetailViewNgFactory);
    static final policyDetail = RouteDefinition(
        routePath: RoutePath(path: 'policy/:id'),
        component: policy_detail_template.PolicyDetailViewNgFactory);
    static final policyList = RouteDefinition(
        routePath: RoutePath(path: 'policy'),
        component: policy_list_template.PolicyListViewNgFactory);

    static final root = RouteDefinition.redirect(path: '',
        redirectTo: 'dashboard');

    static final rateLimit = RouteDefinition(
        routePath: RoutePath(path: 'rate-limit'),
        component: rate_limit_template.RateLimitViewNgFactory);

    static final resultDetail = RouteDefinition(
        routePath: RoutePath(path: 'result/:id'),
        component: result_detail_template.ResultDetailViewNgFactory);
    static final resultError = RouteDefinition(
        routePath: RoutePath(path: 'result/:id/error'),
        component: result_error_template.ResultErrorViewNgFactory);
    static final resultException = RouteDefinition(
        routePath: RoutePath(path: 'result/:id/exception'),
        component: result_exception_template.ResultExceptionViewNgFactory);
    static final resultList = RouteDefinition(
        routePath: RoutePath(path: 'result'),
        component: result_list_template.ResultListViewNgFactory);
    static final resultPolicy = RouteDefinition(
        routePath: RoutePath(path: 'result/:id/policy'),
        component: result_policy_template.ResultPolicyViewNgFactory);
    static final resultSuccess = RouteDefinition(
        routePath: RoutePath(path: 'result/:id/success'),
        component: result_success_template.ResultSuccessViewNgFactory);

    static final scheduleCreate = RouteDefinition(
        routePath: RoutePath(path: 'schedule/new'),
        component: schedule_detail_template.ScheduleDetailViewNgFactory);
    static final scheduleDetail = RouteDefinition(
        routePath: RoutePath(path: 'schedule/:id'),
        component: schedule_detail_template.ScheduleDetailViewNgFactory);
    static final scheduleJobs = RouteDefinition(
        routePath: RoutePath(path: 'schedule/:id/jobs'),
        component: schedule_jobs_template.ScheduleListJobsViewNgFactory);
    static final scheduleList = RouteDefinition(
        routePath: RoutePath(path: 'schedule'),
        component: schedule_list_template.ScheduleListViewNgFactory);

    static final start = RouteDefinition(
        routePath: RoutePath(path: 'start'),
        component: start_template.StartCrawlViewNgFactory);

    static final systemProfile = RouteDefinition(
        routePath: RoutePath(path: 'system/profile'),
        component: system_profile_template.ProfileViewNgFactory);
    static final systemResources = RouteDefinition(
        routePath: RoutePath(path: 'system/resources'),
        component: system_resources_template.ResourcesViewNgFactory);
    static final systemTasks = RouteDefinition(
        routePath: RoutePath(path: 'system/tasks'),
        component: system_tasks_template.TasksViewNgFactory);

    static final all = <RouteDefinition>[
        captchaCreate,
        captchaDetail,
        captchaList,
        credentialCreate,
        credentialDetail,
        credentialList,
        dashboard,
        policyCreate,
        policyDetail,
        policyList,
        rateLimit,
        resultDetail,
        resultError,
        resultException,
        resultList,
        resultPolicy,
        resultSuccess,
        root,
        scheduleCreate,
        scheduleDetail,
        scheduleJobs,
        scheduleList,
        start,
        systemProfile,
        systemResources,
        systemTasks,
    ];
}
