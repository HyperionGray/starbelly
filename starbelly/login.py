import asyncio
from copy import deepcopy
from operator import itemgetter
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup
import cchardet
import formasaurus
import logging
import w3lib.encoding

from .downloader import DownloadRequest
from .policy import PolicyMimeTypeRules


logger = logging.getLogger(__name__)
chardet = lambda s: cchardet.detect(s).get('encoding')


class LoginManager:
    ''' Contains logic for authenticated crawling. '''
    def __init__(self, policy, rate_limiter):
        ''' Constructor. '''
        self._loop = asyncio.get_event_loop()
        self._policy = policy.replace_mime_type_rules([
            {'match': 'MATCHES', 'pattern': '^image/.*', 'save': True},
            {'save': False},
        ])
        self._rate_limiter = rate_limiter

    async def get_login_form(self, cookie_jar, response, username, password):
        '''
        Attempt to extract login form action and form data from a response,
        substituting the provided ``username`` and ``password`` into the
        corresponding fields.
        '''
        encoding, html = w3lib.encoding.html_to_unicode(
            response.content_type,
            response.body,
            auto_detect_fun=chardet
        )

        forms = await self._loop.run_in_executor(None,
            lambda: formasaurus.extract_forms(html, proba=True))
        form, meta = self._select_login_form(forms)

        if form is None:
            raise Exception("Can't find login form")

        login_field, password_field, captcha_field = self._select_login_fields(
            meta['fields'])
        if login_field is None or password_field is None:
            raise Exception("Can't find username/password fields")

        form.fields[login_field] = username
        form.fields[password_field] = password

        if captcha_field is not None:
            if self._policy.captcha_solver is None:
                raise Exception('CAPTCHA required for login url={} but there is'
                    ' no CAPTCHA solver available'.format(response.url))

            img_el = self._get_captcha_image_element(form)
            img_src = urljoin(response.url, img_el.get('src'))
            captcha_text = await self._solve_captcha(cookie_jar, img_src)
            form.fields[captcha_field] = captcha_text

        form_action = urljoin(response.url, form.action)
        return form_action, form.method, dict(form.fields)

    async def _download_captcha_image(self, cookie_jar, img_src):
        ''' Download a CAPTCHA image and return bytes. '''
        logger.info('Downloading CAPTCHA image src=%s', img_src)

        # Bit of a hack here to work with DownloadRequest API: create a
        # queue that we only use one time.
        output_queue = asyncio.Queue()
        download_request = DownloadRequest(
            job_id='captcha_img',
            url=img_src,
            cost=0,
            policy=self._policy,
            output_queue=output_queue,
            cookie_jar=cookie_jar
        )
        await self._rate_limiter.push(download_request)
        response = await output_queue.get()

        if response.status_code == 200 and response.body is not None:
            img_data = response.body
        else:
            raise Exception('Failed to download CAPTCHA image src=%s', img_src)

        return img_data

    def _get_captcha_image_element(self, form):
        '''
        Return the <img> element in an lxml form that contains the CAPTCHA.

        NOTE: This assumes the first image in the form is the CAPTCHA image. If
        a form has multiple images, maybe use the etree .sourceline attribute to
        figure out which image is closer to the CAPTCHA input? Or crawl through
        the element tree to find the image?
        '''
        img_el = form.find('img')
        if img_el is None:
            raise Exception('Cannot locate CAPTCHA image')
        return img_el

    def _select_login_fields(self, fields):
        ''' Select field having highest probability for class ``field``. '''
        username_field = None
        username_prob = 0
        password_field = None
        password_prob = 0
        captcha_field = None
        captcha_prob = 0

        for field_name, labels in fields.items():
            for label, prob in labels.items():
                if (label == 'username' or label == 'username or email') \
                    and prob > username_prob:
                    username_field = field_name
                    username_prob = prob
                elif label == 'password' and prob > password_prob:
                    password_field = field_name
                    password_prob = prob
                elif label == 'captcha' and prob > captcha_prob:
                    captcha_field = field_name
                    captcha_prob = prob

        return username_field, password_field, captcha_field

    def _select_login_form(self, forms):
        ''' Select form having highest probability for login class. '''
        login_form = None
        login_meta = None
        login_prob = 0

        for form, meta in forms:
            for type_, prob in meta['form'].items():
                if type_ == 'login' and prob > login_prob:
                    login_form = form
                    login_meta = meta
                    login_prob = prob

        return login_form, login_meta

    async def _solve_captcha(self, cookie_jar, img_src):
        ''' Send an image CAPTCHA to an external solver. '''
        img_data = await self._download_captcha_image(cookie_jar, img_src)
        solver = self._policy.captcha_solver
        solution = None

        async with aiohttp.ClientSession() as session:
            # Send CAPTCHA task to service
            task_url = urljoin(solver.service_url, 'createTask')
            command = solver.get_command(img_data)
            async with session.post(task_url, json=command) as response:
                result = await response.json()
                if result['errorId'] != 0:
                    raise Exception('CAPTCHA API error {}'
                        .format(result['errorId']))
                task_id = result['taskId']
                logger.info('Sent image to CAPTCHA API task_id=%d', task_id)

            # Poll for task completion. (Try 6 times.)
            poll_url = urljoin(solver.service_url, 'getTaskResult')
            solution = None
            for attempt in range(6):
                await asyncio.sleep(5)
                command = {
                    'clientKey': solver.api_key,
                    'taskId': task_id,
                }
                logger.info('Polling for CAPTCHA solution task_id=%d,'
                    ' attempt=%d', task_id, attempt+1)
                async with session.post(poll_url, json=command) as response:
                    result = await response.json()
                    if result['errorId'] != 0:
                        raise Exception('CAPTCHA API error {}'
                            .format(result['errorId']))
                    elif result['status'] == 'ready':
                        solution = result['solution']['text']
                        break

        if solution is None:
            raise Exception('CAPTCHA API never completed task')

        return solution
