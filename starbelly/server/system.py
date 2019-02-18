import cProfile
import operator
import pstats

import trio

from . import api_handler, InvalidRequestException


@api_handler
async def performance_profile(command, response):
    ''' Run CPU profiler. '''
    profile = cProfile.Profile()
    profile.enable()
    await trio.sleep(command.duration)
    profile.disable()

    # pstats sorting only works when you use pstats printing... so we have
    # to build our own data structure in order to sort it.
    pr_stats = pstats.Stats(profile)
    stats = list()
    for key, value in pr_stats.stats.items():
        stats.append({
            'file': key[0],
            'line_number': key[1],
            'function': key[2],
            'calls': value[0],
            'non_recursive_calls': value[1],
            'total_time': value[2],
            'cumulative_time': value[3],
        })

    try:
        stats.sort(key=operator.itemgetter(command.sort_by), reverse=True)
    except KeyError:
        raise InvalidRequestException('Invalid sort key: {}'
            .format(command.sort_by))

    response.performance_profile.total_calls = pr_stats.total_calls
    response.performance_profile.total_time = pr_stats.total_tt

    for stat in stats[:command.top_n]:
        function = response.performance_profile.functions.add()
        function.file = stat['file']
        function.line_number = stat['line_number']
        function.function = stat['function']
        function.calls = stat['calls']
        function.non_recursive_calls = stat['non_recursive_calls']
        function.total_time = stat['total_time']
        function.cumulative_time = stat['cumulative_time']
