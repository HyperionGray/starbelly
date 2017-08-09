import cchardet
import formasaurus
import logging
import lxml.etree
from operator import itemgetter
from urllib.parse import urljoin
import w3lib.encoding


logger = logging.getLogger(__name__)
chardet = lambda s: cchardet.detect(s).get('encoding')


def get_login_form(response, username, password):
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
    forms = formasaurus.extract_forms(html, proba=True)
    form, meta = _select_login_form(forms)

    if form is None:
        raise Exception("Can't find login form")

    login_field, password_field = _select_login_fields(meta['fields'])
    if login_field is None or password_field is None:
        raise Exception("Can't find username/password fields")

    form.fields[login_field] = username
    form.fields[password_field] = password
    return urljoin(response.url, form.action), form.method, dict(form.fields)


def _select_login_fields(fields):
    ''' Select field having highest probability for class ``field``. '''
    username_field = None
    username_prob = 0
    password_field = None
    password_prob = 0

    for field_name, labels in fields.items():
        for label, prob in labels.items():
            if (label == 'username' or label == 'username or email') \
                and prob > username_prob:
                username_field = field_name
                username_prob = prob
            elif label == 'password' and prob > password_prob:
                password_field = field_name
                password_prob = prob

    return username_field, password_field


def _select_login_form(forms):
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
