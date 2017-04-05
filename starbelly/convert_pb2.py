'''
Helper functions for converting database documents into protobuf structures.
'''

# from uuid import UUID
#
#
# def job_status(pb_list, job):
#     '''
#     Convert `job_status` to protobuf `JobStatus` and append to `pb_list`.
#     '''
#     job_status = pb_list.add()
#     job_status.job_id = UUID(job_id).bytes
#     cond_set(job_data, job_status, 'name')
#     cond_set(job_data, job_status, 'item_count')
#     cond_set(job_data, job_status, 'http_success_count')
#     cond_set(job_data, job_status, 'http_error_count')
#     cond_set(job_data, job_status, 'exception_count')
#     if 'run_state' in job_data:
#         run_state = job_data['run_state'].upper()
#         job_status.run_state = JobRunState.Value(run_state)
#     http_status_counts = job_data.get('http_status_counts', {})
#     for status_code, count in http_status_counts.items():
#         job_status.http_status_counts[int(status_code)] = count
#
#
# def _conditional_set(src, tgt, attr):
#     '''
#     A helper function for mapping fields in database documents to attributes in
#     protobuf structures.
#     '''
#     if attr in src:
#         setattr(tgt, attr, src[attr])
