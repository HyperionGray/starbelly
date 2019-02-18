import logging

from rethinkdb import RethinkDB

from starbelly.job import RunState


logger = logging.getLogger(__name__)
r = RethinkDB()



class CrawlFrontierDb:
    ''' Handles database queries for the CrawlFrontier class. '''
    def __init__(self, db_pool):
        '''
        Constructor

        :param db_pool: A RethinkDB connection pool.
        '''
        self._db_pool = db_pool

    async def any_in_flight(self, job_id):
        '''
        Check whether there are any frontier items that are "in-flight", i.e.
        somewhere in the crawling pipeline.

        :param str job_id: The ID of the job to check the frontier for.
        :returns: True if the job has in-flight items in its frontier.
        :rtype bool:
        '''
        in_flight_query = (
            r.table('frontier')
             .order_by(index='cost_index')
             .between((job_id, True, r.minval),
                      (job_id, True, r.maxval))
             .count()
        )

        async with self._db_pool.connection() as conn:
            in_flight_count = await in_flight_query.run(conn)

        return in_flight_count > 0

    async def get_frontier_batch(self, job_id, batch_size):
        '''
        Get a batch of items to crawl from the frontier.

        This returns up to ``batch_size`` items from the frontier ordered by
        cost and filtered to exclude in-flight items (items that are already
        being processed by downstream components in the crawling pipeline). Each
        of the returned items is updated in the database to indicate that it is
        is now in-flight.

        If no items are available, then the returned list will be empty.

        :param str job_id: The ID of the job for this frontier.
        :param int batch_size: The maximum number of documents to return.
        :returns: A batch of items.
        :rtype: list
        '''
        batch_query = (
            r.table('frontier')
             .order_by(index='cost_index')
             # False → only items that are not already in-flight
             .between((job_id, False, r.minval),
                      (job_id, False, r.maxval))
             .limit(batch_size)
        )

        docs = list()

        async with self._db_pool.connection() as conn:
            cursor = await batch_query.run(conn)
            async with cursor:
                async for doc in cursor:
                    docs.append(doc)
            ids = [doc['id'] for doc in docs]
            await r.table('frontier').get_all(*ids).update(
                {'in_flight': True}).run(conn)

        return docs

    async def get_frontier_size(self, job_id):
        '''
        Return the number of items in a job's frontier.

        :param str job_id: The ID of the job to check the frontier for.
        :rtype int:
        '''
        size_query =  r.table('frontier').between(
            (job_id, r.minval, r.minval),
            (job_id, r.maxval, r.maxval),
            index='cost_index'
        ).count()
        async with self._db_pool.connection() as conn:
            size = await size_query.run(conn)
        return size


class CrawlExtractorDb:
    ''' Handles database queries for the CrawlExtractor class. '''
    def __init__(self, db_pool):
        '''
        Constructor

        :param db_pool: A RethinkDB connection pool.
        '''
        self._db_pool = db_pool

    async def delete_frontier_item(self, frontier_id):
        '''
        Delete one object from the frontier.

        :param str frontier_id: The ID of the item to delete.
        '''
        delete_query = r.table('frontier').get(frontier_id).delete()
        async with self._db_pool.connection() as conn:
            await delete_query.run(conn)

    async def insert_frontier_items(self, items):
        '''
        Insert items into frontier table.

        :param list items: A list of frontier documents.
        '''
        async with self._db_pool.connection() as conn:
            await r.table('frontier').insert(items).run(conn)


class CrawlManagerDb:
    ''' Handles database queries for the CrawlManager class. '''
    def __init__(self, db_pool):
        '''
        Constructor

        :param db_pool: A RethinkDB connection pool.
        '''
        self._db_pool = db_pool

    async def clear_frontier(self, job_id):
        '''
        Clear the frontier for a given job.

        :param str job_id: The ID of the job for which the frontier needs to be
            cleared.
        '''
        frontier_query = (
            r.table('frontier')
             .between((job_id, r.minval, r.minval),
                      (job_id, r.maxval, r.maxval),
                      index='cost_index')
             .delete()
        )

        async with self._db_pool.connection() as conn:
            await frontier_query.run(conn)

    async def create_job(self, job_doc):
        '''
        Create a new job document in the database. Add the job's seed URLs to
        the crawl frontier.

        :param dict job_doc: The job document to insert.
        :returns: The new job ID.
        :rtype: str
        '''
        async with self._db_pool.connection() as conn:
            result = await r.table('job').insert(job_doc).run(conn)
            job_id = result['generated_keys'][0]
            frontier = [{'cost': 0, 'job_id': job_id, 'url': s}
                for s in job_doc['seeds']]
            await r.table('frontier').insert(frontier).run(conn)

        return job_id


    async def finish_job(self, job_id, run_state, completed_at):
        '''
        Set a job as finished, i.e. either cancelled or completed.

        :param str job_id: The ID of the job to finish.
        :param starbelly.job.RunState run_state:
        :param datetime completed_at: The datetime that the job was completed.
        '''
        job_query = (
            r.table('job')
             .get(job_id)
             .update({
                'run_state': run_state,
                'completed_at': completed_at,
                'duration': completed_at - r.row['started_at'],
             })
        )
        async with self._db_pool.connection() as conn:
            await job_query.run(conn)

    async def get_job_schedule_id(self, job_id):
        '''
        Get the schedule ID from a given job.

        :returns: Schedule ID
        :rtype: str
        '''
        schedule_query = r.table('job').get(job_id).pluck('schedule_id')

        async with self._db_pool.connection() as conn:
            doc = await schedule_query.run(conn)

        return doc['schedule_id']

    async def get_max_sequence(self):
        '''
        Get the maximum sequence number from the database.

        :returns: Sequence number.
        :rtype: int
        '''
        sequence_query = (
            r.table('response')
             .max(index='sequence')
             .pluck('sequence')
        )

        async with self._db_pool.connection() as conn:
            try:
                doc = await sequence_query.run(conn)
                max_sequence = doc['sequence']
            except r.ReqlQueryLogicError:
                max_sequence = 0

        return max_sequence

    async def get_policy(self, policy_id):
        '''
        Get a policy document from the database.

        :param str policy_id: The ID of the policy to get.
        :returns: A database document.
        :rtype: dict
        '''
        policy_query = r.table('policy').get(policy_id)

        async with self._db_pool.connection() as conn:
            policy_doc = await policy_query.run(conn)
            captcha_solver_id = policy_doc.pop('captcha_solver_id', None)
            if captcha_solver_id is not None:
                policy_doc['captcha_solver'] = await (
                    r.table('captcha_solver')
                     .get(captcha_solver_id)
                     .run(conn)
                )

        return policy_doc

    async def pause_job(self, job_id, old_urls):
        '''
        Set a job as paused.

        :param str job_id: The ID of the job to pause.
        :param bytes old_urls: A pickled set of URLs that have been seen so far
            in the crawl.
        '''
        job_query = (
            r.table('job')
             .get(job_id)
             .update({
                'run_state': RunState.PAUSED,
                'old_urls': old_urls,
             })
        )

        async with self._db_pool.connection() as conn:
            await job_query.run(conn)

    async def resume_job(self, job_id):
        '''
        Set a job as resumed, i.e. paused → running..

        :param str job_id: The ID of the job to pause.
        :returns: A job database document.
        :rtype: dict
        '''
        job_query = r.table('job').get(job_id).update(
            {'run_state': RunState.RUNNING}, return_changes=True)
        import logging
        async with self._db_pool.connection() as conn:
            result = await job_query.run(conn)
            job_doc = result['changes'][0]['new_val']
            policy_doc = job_doc['policy']
            captcha_solver_id = policy_doc.pop('captcha_solver_id', None)
            logging.debug('catpcha %s', captcha_solver_id)
            if captcha_solver_id:
                policy_doc['captcha_solver'] = await (
                    r.table('captcha_solver')
                     .get(captcha_solver_id)
                     .run(conn)
                )

        return job_doc

    async def run_job(self, job_id):
        '''
        Mark a job as running.

        :param str job_id: The ID of the job to run.
        '''
        query = r.table('job').get(job_id).update(
            {'run_state': RunState.RUNNING})
        async with self._db_pool.connection() as conn:
            await query.run(conn)


class CrawlStorageDb:
    ''' Handles database queries for the CrawlStorage class. '''
    def __init__(self, db_pool):
        '''
        Constructor

        :param db_pool: A RethinkDB connection pool.
        '''
        self._db_pool = db_pool

    async def save_response(self, response_doc, response_body_doc):
        '''
        Save a response and its associated body, if the body does not already
        exist in the database.

        :param dict response_doc: The response as a database document.
        :param dict response_body_doc: The response body as a database document,
            or ``None`` if there is no response body.
        '''
        async with self._db_pool.connection() as conn:
            await r.table('response').insert(response_doc).run(conn)
            if response_body_doc:
                try:
                    await (
                        r.table('response_body')
                         .insert(response_body_doc, conflict='error')
                         .run(conn)
                    )
                except r.RuntimeError:
                    # This response body already exists in the DB.
                    pass

    async def update_job_stats(self, job_id, response):
        '''
        Update job stats with a download response.

        This function should make an atomic change to the database, e.g. no
        concurrent query should cause a partial read or partial write.

        :param starbelly.downloader.DownloadResponse response:
        '''
        status = str(response.status_code)
        status_first_digit = status[0]
        new_data = {'item_count': r.row['item_count'] + 1}

        if response.exception is None:
            if 'http_status_counts' not in new_data:
                new_data['http_status_counts'] = {}

            # Increment count for status. (Assume zero if it doesn't exist yet).
            new_data['http_status_counts'][status] = (
                1 + r.branch(
                    r.row['http_status_counts'].has_fields(status),
                    r.row['http_status_counts'][status],
                    0
                )
            )

            if status_first_digit == '2':
                new_data['http_success_count'] = r.row['http_success_count'] + 1
            else:
                new_data['http_error_count'] = r.row['http_error_count'] + 1
        else:
            new_data['exception_count'] = r.row['exception_count'] + 1

        query = r.table('job').get(job_id).update(new_data)
        async with self._db_pool.connection() as conn:
            await query.run(conn)


class LoginDb:
    ''' Handles database queries for the LoginManager class. '''
    def __init__(self, db_pool):
        '''
        Constructor

        :param db_pool: A RethinkDB connection pool.
        '''
        self._db_pool = db_pool

    async def get_login(self, domain):
        '''
        Get the login for the given domain.

        :param str domain:
        :returns: A database document.
        :rtype: dict
        '''
        async with self._db_pool.connection() as conn:
            login = await r.table('domain_login').get(domain).run(conn)
        return login


class ScheduleDb:
    ''' Handles database queries for the Scheduler class. '''
    def __init__(self, db_pool):
        '''
        Constructor

        :param db_pool: A RethinkDB connection pool.
        '''
        self._db_pool = db_pool

    async def get_schedule_docs(self):
        ''' Yield schedule database documents. '''
        def latest_job(sched):
            return {'latest_job':
                r.table('job')
                 .order_by(index='schedule')
                 .between((sched['id'], r.minval), (sched['id'], r.maxval))
                 .pluck(['name', 'run_state', 'started_at', 'completed_at'])
                 .nth(-1)
                 .default(None)
            }

        async with self._db_pool.connection() as conn:
            cursor = await r.table('schedule').merge(latest_job).run(conn)
            async with cursor:
                async for schedule_doc in cursor:
                    yield schedule_doc

    async def update_job_count(self, schedule_id, job_count):
        '''
        Update the job count for a given schedule.

        :param str schedule_id: The ID of the schedule to update.
        :param int job_count: The new job count to store.
        '''
        update_query = r.table('schedule').get(schedule_id).update({
            'job_count': job_count})
        async with self._db_pool.connection() as conn:
            await update_query.run(conn)


class ServerDb:
    ''' Handles database queries for the Server class. '''
    def __init__(self, db_pool):
        '''
        Constructor

        :param db_pool: A RethinkDB connection pool.
        '''
        self._db_pool = db_pool

    async def delete_captcha_solver(self, solver_id):
        '''
        Delete a CAPTCHA solver.

        This checks if any policies are depending on the CAPTCHA solver. If so
        it raises ValueError.

        :param str solver_id:
        '''
        async with self._db_pool.connection() as conn:
            use_count = await (
                r.table('policy')
                 .filter({'captcha_solver_id': solver_id})
                 .count()
                 .run(conn)
            )
            if use_count > 0:
                raise ValueError('Cannot delete CAPTCHA solver'
                    ' because it is being used by a policy.')
            await (
                r.table('captcha_solver')
                 .get(solver_id)
                 .delete()
                 .run(conn)
            )

    async def get_captcha_solver(self, solver_id):
        '''
        Get a CAPTCHA solver.

        :param str solver_id:
        :returns: A database document.
        :rtype: dict
        '''
        async with self._db_pool.connection() as conn:
            doc = await r.table('captcha_solver').get(solver_id).run(conn)
        return doc

    async def list_captcha_solvers(self, limit, offset):
        '''
        Get a list of CAPTCHA solvers sorted by name.

        :param int limit:
        :param int offset:
        :returns: Total count of documents and list of current page.
        :rtype: tuple(int, list)
        '''
        async with self._db_pool.connection() as conn:
            count = await r.table('captcha_solver').count().run(conn)
            docs = await (
                r.table('captcha_solver')
                 .order_by('name')
                 .skip(offset)
                 .limit(limit)
                 .run(conn)
            )
        return count, docs

    async def set_captcha_solver(self, doc, now):
        '''
        Insert/update CAPTCHA solver. Populate created_at/updated_at fields.

        :param dict doc: A database document.
        :param datetime now: The datetime to place in updated (and possibly
            created) fields.
        :returns: ID of new CAPTCHA document, if any.
        :rtype: str
        '''
        doc['updated_at'] = now

        async with self._db_pool.connection() as conn:
            if 'id' in doc:
                await r.table('captcha_solver').update(doc).run(conn)
                solver_id = None
            else:
                doc['created_at'] = now
                result = await r.table('captcha_solver').insert(doc).run(conn)
                solver_id = result['generated_keys'][0]

        return solver_id

    async def delete_domain_login(self, domain):
        '''
        Delete the login for a given domain.

        :param str domain:
        '''
        async with self._db_pool.connection() as conn:
            await (
                r.table('domain_login')
                 .get(domain)
                 .delete()
                 .run(conn)
            )

    async def get_domain_login(self, domain):
        '''
        Get the login for a given domain.

        :param str domain:
        :returns: A database document.
        :rtype: dict
        '''
        async with self._db_pool.connection() as conn:
            count = await r.table('domain_login').count().run(conn)
            domain_login = await (
                r.table('domain_login')
                 .get(domain)
                 .run(conn)
            )
        return domain_login

    async def list_domain_logins(self, limit, offset):
        '''
        Get a list of domain logins sorted by domain.

        :param int limit:
        :param int offset:
        :returns: Total count of documents and list of current page.
        :rtype: tuple(int, list)
        '''
        docs = list()
        async with self._db_pool.connection() as conn:
            count = await r.table('domain_login').count().run(conn)
            cursor = await (
                r.table('domain_login')
                 .order_by(index='domain')
                 .skip(offset)
                 .limit(limit)
                 .run(conn)
            )
            async with cursor:
                async for doc in cursor:
                    docs.append(doc)
        return count, docs

    async def set_domain_login(self, doc):
        '''
        Insert/update a domain login.

        :param dict doc: A database document.
        '''
        async with self._db_pool.connection() as conn:
            await (
                r.table('domain_login')
                 .insert(doc, conflict='update')
                 .run(conn)
            )

    async def delete_policy(self, policy_id):
        '''
        Delete the specified policy.

        :param str policy_id:
        '''
        async with self._db_pool.connection() as conn:
            await r.table('policy').get(policy_id).delete().run(conn)

    async def get_policy(self, policy_id):
        '''
        Get a policy.

        :param str policy_id:
        :returns: A database document.
        :rtype: dict
        '''
        async with self._db_pool.connection() as conn:
            policy_doc = await r.table('policy').get(policy_id).run(conn)
        return policy_doc

    async def list_policies(self, limit, offset):
        '''
        Get a list of policies sorted by name.

        :param int limit:
        :param int offset:
        :returns: Total count of documents and list of current page.
        :rtype: tuple(int, list)
        '''
        policies = list()
        policy_table = r.table('policy')
        query = policy_table.order_by(index='name').skip(offset).limit(limit)

        async with self._db_pool.connection() as conn:
            count = await policy_table.count().run(conn)
            cursor = await query.run(conn)
            async with cursor:
                async for policy in cursor:
                    policies.append(policy)

        return count, policies

    async def set_policy(self, doc, now):
        '''
        Insert/update a policy.

        :param dict doc: A database document.
        :param datetime now: The datetime to place in updated (and possibly
            created) fields.
        :returns: ID of new CAPTCHA document, if any.
        :rtype: str
        '''
        async with self._db_pool.connection() as conn:
            if 'id' in doc:
                doc['updated_at'] = now
                await r.table('policy').get(doc['id']).update(doc).run(conn)
                policy_id = None
            else:
                doc['created_at'] = now
                doc['updated_at'] = now
                result = await r.table('policy').insert(doc).run(conn)
                policy_id = result['generated_keys'][0]

        return policy_id



