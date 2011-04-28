"""
Tools for digest auth

"""

import hmac
from hashlib import sha1
import base64
import logging
import urllib
import cgi

from flask import request

from spotcloudopenstack.app import app

logger = logging.getLogger('spotcloudopenstack')


class WrongAuth(Exception):
    "Raise if any issue with SpotCloud digest auth"
    pass

    
def _check_auth_post(login, passwd):
    "Check digest for POST and PUT"
    logger.debug('method POST or PUT with %s', request.form)
    if request.form.get('ecp_username') != login:
        logger.warning("Wrong ecp_username is used")
        raise WrongAuth("Wrong ecp_username is used")
    if request.form.get('ecp_auth_digest'
                        ) != get_digest(passwd, request.form):
        logger.warning(
            "Wrong auth digest, waiting for %s, but got %s",
            get_digest(passwd, request.form),
            request.form.get('ecp_auth_digest'))
        raise WrongAuth("Wrong auth digest")


def _check_auth_get(login, passwd):
    "Check diget auth for args from GET or DELETE"
    url = urllib.unquote(request.url)
    if '?' in url:
        query = url.split('?')[1]
    else:
        logger.warning('No query string provided')
        raise WrongAuth(
            "No query string provided")
    query_dict = cgi.parse_qs(query)
    if 'ecp_username' not in query_dict or \
            'ecp_auth_digest' not in query_dict:
        logger.warning(
            "No ecp_username or ecp_auth_digest are provided")
        raise WrongAuth(
            "ecp_username for ecp_auth_digest was not provided")
    if query_dict['ecp_username'][0] != login:
        logger.warning('%s is a wrong user name' % (
                query_dict['ecp_username'][0],))
        raise WrongAuth(
            "Wrong user name is used")
    ecp_auth_digest = query_dict['ecp_auth_digest'][0].replace(
        '%253D', '=')
    if ecp_auth_digest != get_digest(passwd, {'ecp_username':login}):
        logger.debug(
            "Wrong digest provided, got %s but waiting for %s",
            ecp_auth_digest,
            get_digest(passwd, {'ecp_username':login}))
        raise WrongAuth(
            "Wrong digest provided")
        

def check_auth():
    """Test request args for digest auth.
    Raise WrongAuth if any issue
    """
    logger.debug('checking auth')
    login = app.config['SPOTCLOUD_USER']
    passwd = app.config['SPOTCLOUD_PASSWD']

    if request.method in ['POST', 'PUT']:
        _check_auth_post(login, passwd)
    else:
        _check_auth_get(login, passwd)


def to_bytestring(s, encoding='utf-8', errors='strict'):
    "Fix possible bloody UnicodeEncode error if any"
    if not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    else:
        return s


def get_digest(password, args):
    "Create sha1 digest from args"
    args = dict(args.items())
    if 'ecp_auth_digest' in args:
        del args['ecp_auth_digest']
    sorted_keys = sorted(
        args.keys(), key=lambda k: k.lower())
    data = ''.join(
        key + to_bytestring(args[key]) for key in sorted_keys)
    secret = hmac.new(
        'ECPSuperSecretHashKey', password, sha1).hexdigest()
    digest = hmac.new(secret, data, sha1).digest()
    return  base64.b64encode(digest)

