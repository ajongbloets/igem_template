"""Simple python script to interact with the iGem Wiki API

API Documentation from:
https://www.mediawiki.org/wiki/Special:MyLanguage/API:Action_API

Copyright under MIT License, see LICENSE.
"""

from __future__ import print_function
from datetime import datetime as dt
import requests
import logging
import os
import sys

if sys.version_info[0] < 3:
    input = raw_input
    import ConfigParser as configparser
else:
    import configparser

__author__ = "Joeri Jongbloets <joeri@jongbloets.net>"


def ask_confirm(question, max_attempts=1):
    result = False
    attempt = 0
    if not question.endswith(" [Y/n]"):
        question += " [Y/n]"
    while attempt < max_attempts:
        response = input(question)
        if response.lower() in ("y", "yes"):
            result = True
            break
        if response.lower() in ("n", "no"):
            break
        attempt += 1
    if attempt == max_attempts:
        print("Did not receive a valid answer, taking NO as answer")
    return result


class IGemLogFormatter(logging.Formatter):

    LOG_FORMAT = '%(name)s [%(levelname)s]: %(message)s'
    LOG_DT_FORMAT = None
    _converter = dt.fromtimestamp

    def __init__(self, fmt=LOG_FORMAT, datefmt=LOG_DT_FORMAT):
        logging.Formatter.__init__(self, fmt=fmt, datefmt=datefmt)

    def formatTime(self, record, fmt=None):
        """A function to format time"""
        ct = self._converter(record.created)
        if fmt:
            s = ct.strftime(fmt)
        else:
            s = ct.strftime("%H:%M:%S")
        return s


class IGemStreamHandler(logging.StreamHandler):

    def __init__(self, stream=None, formatter=None, level=logging.NOTSET):
        super(IGemStreamHandler, self).__init__(stream=stream)
        if formatter is None:
            formatter = IGemLogFormatter()
        self.setFormatter(formatter)
        self.setLevel(level)


class IGemWikiManager(object):

    api_url = "https://2017.igem.org/wiki/api.php"
    login_url = "https://igem.org/Login2"

    def __init__(self, team=None, year=None):
        if year is None:
            from datetime import datetime as dt
            year = dt.now().year
        self._year = year
        if isinstance(team, str):
            if not team.startswith("Team:"):
                team = "Team:{}".format(team)
        self._team = team
        self._username = None
        self._password = None
        self._prefix = None
        self._files = []
        self._session = requests.Session()
        self._token = None
        self._dry = False
        self._quiet = False

    @classmethod
    def get_logger(cls):
        return logging.getLogger(cls.__name__)

    @property
    def year(self):
        return self._year

    @property
    def team(self):
        return self._team

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, u):
        if isinstance(u, (unicode, str)):
            self._username = u

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, p):
        if isinstance(p, (unicode, str)):
            self._password = p

    @property
    def prefix(self):
        return self._prefix

    @prefix.setter
    def prefix(self, value):
        self._prefix = value

    @property
    def token(self):
        return self._token

    def runs_dry(self):
        return self._dry is True

    def run_dry(self, state):
        self._dry = state is True

    def is_quiet(self):
        return self._quiet is True

    def set_quiet(self, state):
        self._quiet = state is True

    def get_base_url(self):
        return "http://{}.igem.org".format(self.year)

    def get_api_url(self):
        return "https://{}.igem.org/wiki/api.php".format(self.year)

    def get_login_url(self):
        return "https://igem.org/Login2"

    def get_login_confirmed_url(self):
        return "https://igem.org/Login_Confirmed"

    def prefix_title(self, title):
        team = ""
        if isinstance(self.team, str) and self.team != "":
            team = self.team.rstrip("/")
        uri = team
        prefix = ""
        if isinstance(self.prefix, str) and self.prefix != "":
            prefix = self.prefix.rstrip("/")
        if "" not in (prefix, uri):
            uri = "{}/{}".format(uri, prefix)
        else:
            uri = "{}{}".format(uri, prefix)
        # append whole prefix to title
        if not title.startswith(uri):
            uri = uri.strip("/")
            title = title.strip("/")
            if "" not in (uri, title):
                title = "{}/{}".format(uri, title)
            else:
                title = "{}{}".format(uri, title)
        return title

    def prefix_url(self, title):
        url = self.get_base_url()
        title = self.prefix_title(title)
        if not url.endswith("/"):
            url += "/"
        return "{}{}".format(url, title)

    def login(self, username=None, password=None):
        """Login to the iGEM Wiki and obtain token"""
        session = self._session
        if username is not None:
            self.username = username
        if password is not None:
            self.password = password
        if None not in (self.username, self.password):
            # login to igem
            if self.runs_dry():
                self._token = "--DRY RUN --"
            else:
                r1 = session.post(self.login_url, data={
                    'return_to': '',
                    'username': self.username,
                    'password': self.password,
                    'Login': 'Login'
                })
                self.get_logger().debug("Response to Login:\n{}".format(r1.url))
                if r1.url.endswith("Login_Confirmed"):
                    # get token
                    r2 = session.get(self.api_url, params={
                        'format': 'json',
                        'action': 'query',
                        'meta': 'tokens',
                    })
                    self.get_logger().debug("Response to Query Token:\n{}".format(r2.json()))
                    self._token = r2.json()['query']['tokens']['csrftoken']
        self.get_logger().info("Obtained Edit Token: {}".format(self.token))
        return self.token is not None

    def edit(self, title, text):
        """Edit a page (replaces content with provided text)"""
        session = self._session
        # create correct page title
        page = self.prefix_title(title)
        if self.runs_dry():
            result = True
        else:
            r = session.post(self.api_url, data={
                'format': 'json',
                'action': 'edit',
                'assert': 'user',
                'text': text,
                'title': page,
                'token': self.token,
            })
            self.get_logger().debug("Response to Edit:\n{}".format(r.json()))
            result = 'error' not in r.json().keys()
        self.get_logger().info("Edit Page {} => {}: {}".format(title, page, result))
        return result

    def page_search(self, prefix):
        """Searches for all pages with the given prefix"""
        pass

    def delete(self, title, reason=None):
        """Deletes a title"""
        result = False
        session = self._session
        # generate page name
        page = self.prefix_title(title)
        # generate POST data
        data = {
            'format': 'json',
            'action': 'delete',
            'title': page,
            'token': self.token
        }
        response = True
        if not self.is_quiet():
            response = ask_confirm("Do you really want to DELETE page {} => {}?".format(title, page))
        if response:
            if isinstance(reason, str) and reason != "":
                data["reason"] = reason
            if self.runs_dry():
                result = True
            else:
                r = session.post(self.api_url, data=data)
                self.get_logger().debug("Response to Delete:\n{}".format(r.json()))
                result = "error" not in r.json().keys()
        self.get_logger().info("Delete Page {} => {}: {}".format(title, page, result))
        return result

    @classmethod
    def run(cls):
        parser = cls.create_parser()
        arguments = vars(parser.parse_args())
        verbosity = arguments.get("verbose")
        if verbosity > 0:
            level = 60 - (verbosity * 10)
            if level < 0:
                level = 0
            root_log = logging.getLogger()
            root_log.setLevel(level)
            hdlr = IGemStreamHandler(level=level)
            root_log.addHandler(hdlr)
        if "ini" in arguments.keys():
            ini_file = arguments.get("ini")
            settings = cls.load_ini(ini_file)
            arguments.update(settings)
        # build object
        team = arguments.get("team")
        year = arguments.get("year")
        result = cls(team=team, year=year)
        # now we parse them
        result.parse_arguments(arguments)
        # get what should be done
        action = arguments.get("action")
        result.execute(action)
        return result

    def execute(self, action):
        pass

    @classmethod
    def create_parser(cls, parser=None):
        import argparse
        if parser is None:
            parser = argparse.ArgumentParser()
        parser.add_argument(
            'action', help="What should be done?"
        )
        parser.add_argument(
            'files', action="append", type=str,
            help="Names of the file to upload"
        )
        parser.add_argument(
            '-q', '--quiet', dest="quiet", action="store_true",
            help="Quietly accept all questions."
        )
        parser.add_argument(
            '-n', '--dry', dest="dry", action="store_true",
            help="Do not send anything to the server."
        )
        parser.add_argument(
            '-v', dest="verbose", action="count",
            help="Print log messages to the console, use multiple to increase detail."
        )
        parser.add_argument(
            '--ini', help="Location of the ini file to load commonly used paramets"
        )
        parser.add_argument(
            '--username', '-U', dest="username", help="Username to login with on the iGEM wiki"
        )
        parser.add_argument(
            '--password', '-p', dest="password", help="Password to login with on the iGEM wiki"
        )
        parser.add_argument(
            '--team', help="The name of your iGEM Team (e.q. Amsterdam).\n"
                           "When not specified you need to prefix all titles manually"
        )
        parser.add_argument(
            '--year', help="Wiki Edition you want to edit (defaults to current year)"
        )
        parser.add_argument(
            '--prefix', help="Prefix to add before each title"
        )
        return parser

    def parse_arguments(self, arguments):
        is_quiet = arguments.get("quiet")
        if is_quiet is not None:
            self.set_quiet(self.parse_bool(is_quiet))
        run_dry = arguments.get("dry")
        if run_dry is not None:
            self.run_dry(self.parse_bool(run_dry))
        if self.runs_dry():
            self.get_logger().info("Executing in DRY RUN Mode")
        username = arguments.get("username")
        if username is not None:
            self.username = username
        password = arguments.get("password")
        if password is not None:
            self.password = password
        prefix = arguments.get("prefix")
        if prefix is not None:
            self.prefix = prefix
        files = arguments.get("files")
        if not isinstance(files, (tuple, list)):
            files = [files]
        self._files = files

    def parse_bool(self, value, default=False):
        result = default
        if isinstance(value, int):
            result = value == 1
        if isinstance(value, str):
            result = value.lower() in ("1", "true")
        return result is True

    @staticmethod
    def load_ini(location):
        results = {}
        if os.path.exists(location):
            try:
                cfg = configparser.SafeConfigParser()
                cfg.read(location)
                results = cfg.items("igem")
            except configparser.Error as e:
                print("Cannot load {}:\n{}".format(location, e))
        return results

if __name__ == "__main__":
    pass
