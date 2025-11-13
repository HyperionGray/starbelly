import asyncio
from functools import partial
import logging
import random

import aiohttp
import cchardet
import formasaurus
import trio
import trio_asyncio
import w3lib.encoding
from yarl import URL

from .downloader import DownloadRequest


logger = logging.getLogger(__name__)
chardet = lambda s: cchardet.detect(s).get("encoding")


def get_captcha_image_element(form):
    """
    Return the <img> element in an lxml form that contains the CAPTCHA.

    NOTE: This assumes the first image in the form is the CAPTCHA image. If
    a form has multiple images, maybe use the etree .sourceline attribute to
    figure out which image is closer to the CAPTCHA input? Or crawl through
    the element tree to find the image?

    :param form: An lxml form element.
    :returns: An lxml image element.
    """
    img_el = form.find(".//img")
    if img_el is None:
        raise Exception("Cannot locate CAPTCHA image")
    return img_el


def select_login_fields(fields):
    """
    Select field having highest probability for class ``field``.

    :param dict fields: Nested dictionary containing label probabilities
        for each form element.
    :returns: (username field, password field, captcha field)
    :rtype: tuple
    """
    username_field = None
    username_prob = 0
    password_field = None
    password_prob = 0
    captcha_field = None
    captcha_prob = 0

    for field_name, labels in fields.items():
        for label, prob in labels.items():
            if label in ("username", "username or email") and prob > username_prob:
                username_field = field_name
                username_prob = prob
            elif label == "password" and prob > password_prob:
                password_field = field_name
                password_prob = prob
            elif label == "captcha" and prob > captcha_prob:
                captcha_field = field_name
                captcha_prob = prob

    return username_field, password_field, captcha_field


def select_login_form(forms):
    """
    Select form having highest probability for login class.

    :param dict forms: Nested dict containing label probabilities for each
        form.
    :returns: (login form, login meta)
    :rtype: tuple
    """
    login_form = None
    login_meta = None
    login_prob = 0

    for form, meta in forms:
        for type_, prob in meta["form"].items():
            if type_ == "login" and prob > login_prob:
                login_form = form
                login_meta = meta
                login_prob = prob

    return login_form, login_meta


class LoginManager:
    def __init__(self, job_id, db, policy, downloader):
        """
        Constructor

        :param starbelly.db.LoginDb: A database layer.
        """
        self._job_id = job_id
        self._db = db
        self._policy = policy
        self._downloader = downloader

    async def login(self, domain):
        """
        Attempt a login for the given domain.

        :param str domain: The domain to log into.
        """
        domain_login = await self._db.get_login(domain)
        if domain_login is None:
            return

        # Ensure login has users
        if not domain_login.get("users", []):
            logger.warning("No users for login: %s", domain_login)
            return

        # Select random user from domain_login
        user = random.choice(domain_login["users"])
        masked_pass = user["password"][:2] + "******"
        logger.info(
            "Attempting login: domain=%s with user=%s password=%s",
            domain,
            user["username"],
            masked_pass,
        )
        request = DownloadRequest(
            frontier_id=None,
            job_id=self._job_id,
            method="GET",
            url=domain_login["login_url"],
            form_data=None,
            cost=1.0,
        )
        response = await self._downloader.download(request)
        if not response.is_success:
            logger.error("Login aborted: cannot fetch %s", response.url)
            return
        try:
            action, method, data = await self._get_login_form(
                response, user["username"], user["password"]
            )
        except Exception as e:
            logger.exception("Cannot parse login form: %s", e)
            return
        logger.info("Login action=%s method=%s data=%r", action, method, data)
        request = DownloadRequest(
            frontier_id=None,
            job_id=self._job_id,
            method=method,
            url=action,
            form_data=data,
            cost=1.0,
        )
        response = await self._downloader.download(request)
        if not response.is_success:
            logger.error(
                "Login failed action=%s (see downloader log for" " details)", action
            )

    async def _download_captcha_image(self, img_src):
        """
        Download and return a CAPTCHA image.

        :param str img_src: The URL to download the image from.
        :rtype bytes:
        """
        logger.info("Downloading CAPTCHA image src=%s", img_src)
        request = DownloadRequest(
            frontier_id=None,
            job_id=None,
            method="GET",
            url=img_src,
            form_data=None,
            cost=0,
        )
        response = await self._downloader.download(request)

        if response.status_code == 200 and response.body is not None:
            img_data = response.body
        else:
            raise Exception("Failed to download CAPTCHA image src={}".format(img_src))

        return img_data

    async def _get_login_form(self, response, username, password):
        """
        Attempt to extract login form action and form data from a response,
        substituting the provided ``username`` and ``password`` into the
        corresponding fields. Returns the data needed to POST a login request.

        :param starbelly.downloader.DownloadResponse response:
        :param str username: The username to log in with.
        :param str password: The password to log in with.
        :returns: (action, method, fields)
        :rtype: tuple
        """
        _, html = w3lib.encoding.html_to_unicode(
            response.content_type, response.body, auto_detect_fun=chardet
        )

        forms = await trio.to_thread.run_sync(
            partial(formasaurus.extract_forms, html, proba=True)
        )
        form, meta = select_login_form(forms)

        if form is None:
            raise Exception("Can't find login form")

        login_field, password_field, captcha_field = select_login_fields(meta["fields"])
        if login_field is None or password_field is None:
            raise Exception("Can't find username/password fields")

        form.fields[login_field] = username
        form.fields[password_field] = password

        if captcha_field is not None:
            if self._policy.captcha_solver is None:
                raise Exception(
                    "CAPTCHA required for login url={} but there is"
                    " no CAPTCHA solver available".format(response.url)
                )

            img_el = get_captcha_image_element(form)
            img_src = str(URL(response.url).join(URL(img_el.get("src"))))
            img_data = await self._download_captcha_image(img_src)
            captcha_text = await self._solve_captcha_asyncio(img_data)
            form.fields[captcha_field] = captcha_text

        form_action = URL(response.url).join(URL(form.action))
        return form_action, form.method, dict(form.fields)

    @trio_asyncio.aio_as_trio
    async def _solve_captcha_asyncio(self, img_data):
        """
        Send an image CAPTCHA to an external solver and return the solution.
        This function uses aiohttp and therefore must run on the asyncio loop.

        :param bytes img_data: The CAPTCHA image.
        :rtype: str
        """
        solver = self._policy.captcha_solver
        solution = None
        task_url = str(URL(solver.service_url).join(URL("createTask")))
        poll_url = str(URL(solver.service_url).join(URL("getTaskResult")))

        # This doesn't use the downloader object because this is a third party
        # and is not the subject of our crawl.
        async with aiohttp.ClientSession() as session:
            # Send CAPTCHA task to service
            command = solver.get_command(img_data)
            async with session.post(task_url, json=command) as response:
                result = await response.json()
                if result["errorId"] != 0:
                    raise Exception("CAPTCHA API error {}".format(result["errorId"]))
                task_id = result["taskId"]
                logger.info("Sent image to CAPTCHA API task_id=%d", task_id)

            # Poll for task completion. (Try 6 times.)
            solution = None
            for attempt in range(6):
                await asyncio.sleep(5)
                command = {
                    "clientKey": solver.api_key,
                    "taskId": task_id,
                }
                logger.info(
                    "Polling for CAPTCHA solution task_id=%d," " attempt=%d",
                    task_id,
                    attempt + 1,
                )
                async with session.post(poll_url, json=command) as response:
                    result = await response.json()
                    if result["errorId"] != 0:
                        raise Exception(
                            "CAPTCHA API error {}".format(result["errorId"])
                        )
                    solution = result["solution"]["text"]
                    break

        if solution is None:
            raise Exception("CAPTCHA API never completed task")

        return solution
