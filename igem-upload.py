#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import requests
import glob
import os
import sys

if sys.version_info[0] < 3:
    import ConfigParser as configparser
else:
    import configparser


def load_ini(ini_fn):
    results = {}
    if os.path.exists(ini_fn):
        try:
            cfg = configparser.SafeConfigParser()
            cfg.read(ini_fn)
            results = cfg.items("igem")
        except configparser.Error:
            print("Cannot load: {}".format(ini_fn))
    return results


class iGemUploader(object):

    api_url = "https://2017.igem.org/wiki/api.php"
    login_url = "https://igem.org/Login2"

    def __init__(self, year=None, team=None, prefix=None):
        if year is None:
            from datetime import datetime as dt
            year = dt.now().year
        self._year = year
        if isinstance(team, str):
            if not team.startswith("Team:"):
                team = "Team:{}".format(team)
        self._team = team
        self._prefix = prefix
        self._session = requests.Session()
        self._token = None
        self._dry = False

    @property
    def year(self):
        return self._year

    @property
    def team(self):
        return self._team

    @property
    def prefix(self):
        return self._prefix

    @property
    def token(self):
        return self._token

    def runs_dry(self):
        return self._dry is True

    def run_dry(self, state):
        self._dry = state is True

    def get_base_url(self):
        return "http://{}.igem.org".format(self.year)

    def get_api_url(self):
        return "https://{}.igem.org/wiki/api.php".format(self.year)

    def get_login_url(self):
        return "https://igem.org/Login2"

    def login(self, username, password):
        session = self._session
        # login to igem
        if self.runs_dry():
            self._token = "--DRY RUN -- "
        else:
            r1 = session.post(self.login_url, data={
                'return_to': '',
                'username': username,
                'password': password,
                'Login': 'Login'
            })
            if r1.status_code == 200:
                # get token
                r2 = session.get(self.api_url, params={
                    'format': 'json',
                    'action': 'query',
                    'meta': 'tokens',
                })
                self._token = r2.json()['query']['tokens']['csrftoken']
        return self._token is not None

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

    def edit(self, title, text):
        # result = False
        session = self._session
        # prefix with team
        page = self.prefix_title(title)
        print("Edit page: {}".format(page))
        if self.runs_dry():
            result = True
        else:
            r = session.post(self.api_url, data={
                'format': 'json',
                'action': 'edit',
                'assert': 'user',
                'text': text,
                'title': page,
                'token': self._token,
            })
            result = 'error' not in r.json().keys()
        return result

    def upload(self, source, destination=None):
        extension = source.rsplit(".", 1)[1]
        if extension == "html":
            self.upload_html(source, destination)
        if extension in ("js", "css"):
            self.upload_resource(source, destination)
        # images

    def upload_html(self, source, destination=None):
        result = False
        # remove any .html extension from the file
        if destination is None:
            destination = source
        name = destination
        name = name.lstrip("./")
        if name.endswith(".html"):
            name = name.replace(".html", "")
        if os.path.exists(source):
            # obtain content
            with open(source, "r") as src:
                content = "".join(src.readlines())
            # process content
            content = self.sanitize_html(content)
            print("Upload html {} to {}".format(source, name))
            # upload
            result = self.edit(name, content)
        return result

    def upload_resource(self, source, destination=None):
        result = False
        if destination is None:
            destination = source
        name = destination
        name = name.lstrip("./")
        if name.endswith(".css"):
            name = name.replace(".css", "")
        if name.endswith(".js"):
            name = name.replace(".js", "")
        if os.path.exists(source):
            with open(source, "r") as src:
                content = "".join(src.readlines())
            print("Upload resource {} to {}".format(source, name))
            # upload
            self.edit(name, content)
        return result

    def upload_files(self, pattern, base=None):
        result = True
        for source in glob.glob(pattern):
            if os.path.exists(source):
                if os.path.isdir(source):
                    # take all files from the directory
                    self.upload_files(os.path.join(source, "*"), base=base)
                if os.path.isfile(source):
                    destination = None
                    if base is not None:
                        # remove pattern from the file name
                        destination = source.replace(base, "", 1)
                    self.upload(source, destination=destination)
        return result

    def sanitize_html(self, html):
        from bs4 import BeautifulSoup
        doc = BeautifulSoup(html, "html.parser")
        # find all link href and check if we load css
        elements = doc.find_all("link", rel="stylesheet")
        for e in elements:
            self.sanitize_stylesheet(e)
        elements = doc.find_all("script")
        # elements = doc.xpath("//script")
        for e in elements:
            self.sanitize_javascript(e)
        # write to string
        result = doc.prettify()
        return result

    def sanitize_stylesheet(self, element):
        # href = element.get("href")
        href = element["href"]
        # remove extension
        uri = href.rsplit(".")[0]
        # prefix with wiki
        uri = self.prefix_url(uri)
        if not uri.endswith("?action=raw&ctype=text/css"):
            uri += "?action=raw&ctype=text/css"
        # update
        print("Changed href {} to {}".format(href, uri))
        # element.set("href", uri)
        element["href"] = uri
        return element

    def sanitize_javascript(self, element):
        # src = element.get("src")
        src = element["src"]
        uri = src.rsplit(".")[0]
        uri = self.prefix_url(uri)
        if not uri.endswith("?action=raw&ctype=text/js"):
            uri += "?action=raw&ctype=text/javascript"
        # update
        print("Changed src {} to {}".format(src, uri))
        # element.set("src", uri)
        element["src"] = uri
        return element

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Simple file upload for the iGem wiki")
    p.add_argument(
        '-n', '--dry', dest="dry", action="store_true",
        help="Do not send anything to the server"
    )
    p.add_argument(
        '--ini', help="Location of the ini file to load commonly used paramets"
    )
    p.add_argument(
        '--username', '-U', dest="username", help="Username to login with on the iGEM wiki"
    )
    p.add_argument(
        '--password', '-p', dest="password", help="Password to login with on the iGEM wiki"
    )
    p.add_argument(
        '--team', help="The name of your iGEM Team (e.q. Amsterdam).\n"
                       "When not specified you need to prefix all titles manually"
    )
    p.add_argument(
        '--year', help="Wiki Edition you want to edit (defaults to current year)"
    )
    p.add_argument(
        '--prefix', help="Prefix to add before each title"
    )
    p.add_argument(
        '--strip', action="store_true",
        help="Remove pattern from filename"
    )
    p.add_argument(
        'files', action="append", type=str,
        help="Names of the file to upload"
    )

    arguments = vars(p.parse_args())
    ini_file = arguments.get("ini")
    if isinstance(ini_file, str):
        settings = load_ini(ini_file)
        arguments.update(settings)
    team = arguments.get("team")
    year = arguments.get("year")
    prefix = arguments.get("prefix")
    u = iGemUploader(year=year, team=team, prefix=prefix)
    u.run_dry(arguments.get("dry"))
    username = arguments.get("username")
    password = arguments.get("password")
    strip = arguments.get("strip")
    if isinstance(strip, str):
        strip = strip.lower() in ("1", "true")
    result = u.login(username, password)
    if result:
        print("Login successfull. Token = {}".format(u.token))
        files = arguments.get("files")
        for fn in files:
            base = None
            if strip is True:
                base = os.path.dirname(fn)
            u.upload_files(fn, base)
    print("Done")

# test comment
