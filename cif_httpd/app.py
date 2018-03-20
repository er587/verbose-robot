#!/usr/bin/env python

import logging
import os
import traceback
import textwrap
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from flask import Flask, request, _request_ctx_stack
from flask_cors import CORS
from flask_compress import Compress
from flask_restplus import Api
from werkzeug.contrib.fixers import ProxyFix

# from cif.constants import ROUTER_ADDR, RUNTIME_PATH
# from cifsdk.utils import get_argument_parser, setup_logging, setup_signals, setup_runtime_path

from .common import pull_token
from .utils import get_argument_parser, setup_logging, setup_runtime_path
from .constants import HTTP_LISTEN, HTTP_LISTEN_PORT, TRACE, PIDFILE, SECRET_KEY

from .indicators import api as indicators_api
from .ping import api as ping_api
from .tokens import api as tokens_api
from .health import api as health_api

# from .stats import api as stats_api

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)

CORS(app, resources={r"/*": {"origins": "*"}})
Compress(app)

authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization'
    }
}

# http://flask-restplus.readthedocs.io/en/stable/swagger.html#documenting-authorizations
api = Api(app, version='4.0', title='CIFv4 API', description='The CIFv4 REST API', authorizations=authorizations,
          security='apikey')

APIS = [
    ping_api,
    indicators_api,
    tokens_api,
    health_api
]

for A in APIS:
    api.add_namespace(A)

ns = api.namespace('cif', description='CIF operations')

app.secret_key = SECRET_KEY

log_level = logging.WARN
if TRACE == '1':
    log_level = logging.DEBUG
    logging.getLogger('flask_cors').level = logging.DEBUG

console = logging.StreamHandler()
logging.getLogger('gunicorn.error').setLevel(log_level)
logging.getLogger('gunicorn.error').addHandler(console)
logger = logging.getLogger('gunicorn.error')


@app.before_request
def before_request():
    """
    Grab the API token from headers

    :return: 401 if no token is present
    """

    if request.method == 'GET' and \
            request.endpoint in ['/', 'doc', 'help', 'health', 'restplus_doc.static', 'specs', 'swaggerui']:
        return

    if request.method == 'GET' and request.endpoint in ['favicon']:
        return api.abort(404)

    method = request.form.get('_method', '').upper()
    if method:
        request.environ['REQUEST_METHOD'] = method
        ctx = _request_ctx_stack.top
        ctx.url_adapter.default_method = method
        assert request.method == method

    t = pull_token()
    if HTTP_LISTEN == '127.0.0.1':
        return

    if not t or t == 'None':
        return api.abort(401)


def main():
    p = get_argument_parser()
    p = ArgumentParser(
        description=textwrap.dedent('''\
        example usage:
            $ cif-httpd -d
        '''),
        formatter_class=RawDescriptionHelpFormatter,
        prog='cif-httpd',
        parents=[p]
    )

    p.add_argument('--fdebug', action='store_true')

    args = p.parse_args()
    setup_logging(args)

    logger.info('loglevel is: {}'.format(logging.getLevelName(logger.getEffectiveLevel())))

    setup_runtime_path(args.runtime_path)

    if not args.fdebug:
        # http://stackoverflow.com/a/789383/7205341
        pid = str(os.getpid())
        logger.debug("pid: %s" % pid)

        if os.path.isfile(PIDFILE):
            logger.critical("%s already exists, exiting" % PIDFILE)
            raise SystemExit

        try:
            pidfile = open(PIDFILE, 'w')
            pidfile.write(pid)
            pidfile.close()
        except PermissionError as e:
            logger.error('unable to create pid %s' % PIDFILE)

    try:
        logger.info('pinging router...')
        logger.info('starting up...')
        app.run(host=HTTP_LISTEN, port=HTTP_LISTEN_PORT, debug=args.fdebug, threaded=True)

    except KeyboardInterrupt:
        logger.info('shutting down...')

    except Exception as e:
        logger.critical(e)
        traceback.print_exc()

    if os.path.isfile(PIDFILE):
        os.unlink(PIDFILE)


if __name__ == "__main__":
    main()
