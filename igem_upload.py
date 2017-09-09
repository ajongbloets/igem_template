#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simple Script to upload multiple HTML, CSS or JS files to the iGEM Wiki.

Copyright under MIT License, see LICENSE.
"""
from __future__ import print_function
from igem_manager import IGemWikiManager
import glob
import os
import sys

if sys.version_info[0] < 3:
    from urlparse import urlparse, urlunparse
else:
    from urllib.parse import urlparse, urlunparse

__author__ = "Joeri Jongbloets <joeri@jongbloets.net>"


class IGemUploader(IGemWikiManager):

    def __init__(self, team=None, year=None):
        super(IGemUploader, self).__init__(team=team, year=year)
        self._strip_paths = False

    def do_strip(self):
        return self._strip_paths is True

    def set_strip(self, state):
        self._strip_paths = state is True

    def execute(self, action):
        if action == "upload":
            if self.login():
                uploads = self.upload()
                self.get_logger().info("Uploaded {} files".format(uploads))

    def upload(self, files=None, strip=None):
        if files is None:
            files = self._files
        if strip is None:
            strip = self.do_strip()
        results = 0
        for fn in files:
            base = None
            if strip is True:
                base = os.path.dirname(fn)
            result = self.upload_files(fn, base)
            results += result
        return results

    def upload_files(self, pattern, base=None):
        results = 0
        for source in glob.glob(pattern):
            if os.path.exists(source):
                if os.path.isdir(source):
                    # take all files from the directory
                    results += self.upload_files(os.path.join(source, "*"), base=base)
                if os.path.isfile(source):
                    destination = None
                    if base is not None:
                        # remove pattern from the file name
                        destination = source.replace(base, "", 1)
                    result = self.upload_file(source, destination=destination)
                    # count number
                    if result:
                        results += 1
        return results

    def upload_file(self, source, destination=None):
        result = False
        extension = source.rsplit(".", 1)[1]
        if extension == "html":
            # html
            result = self.upload_html(source, destination)
        if extension in ("js", "css"):
            # js and css
            result = self.upload_resource(source, destination)
        else:
            # images
            result = self.upload_attachment(source, destination)
        return result

    def upload_html(self, source, destination=None):
        """Upload Sanitized HTMl Files"""
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
            self.get_logger().info("Upload html {} to {}".format(source, name))
            # upload
            result = self.edit(name, content)
        return result

    def upload_resource(self, source, destination=None):
        """Upload CSS and JavaScript resources"""
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
            self.get_logger().info("Upload resource {} to {}".format(source, name))
            # upload
            result = self.edit(name, content)
        return result

    def upload_attachment(self, source, destination=None):
        """Upload attachments like Images, PDFs etc."""
        pass

    def sanitize_html(self, html):
        from bs4 import BeautifulSoup
        doc = BeautifulSoup(html, "html.parser")
        # fix all stylesheet imports
        elements = doc.find_all("link", rel="stylesheet")
        for e in elements:
            href = e["href"]
            uri = self.sanitize_stylesheet(href)
            self.get_logger().debug("Changed link href {} to {}".format(href, uri))
            e["href"] = uri
        elements = doc.find_all("script")
        # fix all javascript imports
        for e in elements:
            src = e["src"]
            uri = self.sanitize_javascript(src)
            self.get_logger().debug("Changed script src {} to {}".format(src, uri))
            e["src"] = uri
        # fix all links
        elements = doc.find_all("a")
        for e in elements:
            href = e["href"]
            uri = self.sanitize_link(href)
            self.get_logger().debug("Changed a href {} to {}".format(href, uri))
            e["href"] = uri
        # fix all image links
        elements = doc.find_all("img")
        for e in elements:
            src = e["src"]
            uri = self.sanitize_link(src)
            self.get_logger().debug("Changed img src {} to {}".format(src, uri))
            e["src"] = uri
        # write to string
        result = doc.prettify()
        return result

    def sanitize_stylesheet(self, href):
        # remove extension
        uri = href.rsplit(".")[0]
        # prefix with wiki
        uri = self.prefix_url(uri)
        if not uri.endswith("?action=raw&ctype=text/css"):
            uri += "?action=raw&ctype=text/css"
        return uri

    def sanitize_javascript(self, src):
        uri = src.rsplit(".")[0]
        uri = self.prefix_url(uri)
        if not uri.endswith("?action=raw&ctype=text/js"):
            uri += "?action=raw&ctype=text/javascript"
        return src

    def sanitize_link(self, href):
        url = href
        # we have to be careful, we only want to change the uri not any params or internal links
        parts = list(urlparse(href))
        # get a clean base url
        base_url = self.get_base_url()
        base_url = base_url.replace("https://", "")
        base_url = base_url.replace("http://", "")
        # extract local path
        path = str(parts[2]) #.strip("/")
        if path != "" and parts[1] in ("", base_url):
            target = ""
            pieces = path.rsplit("#", 1)
            path = pieces[0]
            if len(pieces) > 1:
                target = pieces[-1]
            target = target.strip("/")
            path = path.rsplit(".", 1)[0]
            if path == "/":
                path = "index"
            # we will set the parts["netloc"] to the right server
            # so we do not worry about that part
            path = self.prefix_title(path)
            # reassemble
            parts[0] = "http"
            parts[1] = base_url
            parts[2] = path + target
            url = urlunparse(parts)
        return url

    @classmethod
    def create_parser(cls, parser=None):
        parser = super(IGemUploader, cls).create_parser(parser)
        parser.description = "Simple file upload script for the iGEM wiki"
        parser.add_argument(
            '--strip', action="store_true",
            help="Remove pattern from filename"
        )
        return parser

    def parse_arguments(self, arguments):
        super(IGemUploader, self).parse_arguments(arguments)
        strip = arguments.get("strip")
        if isinstance(strip, int):
            strip = strip == 1
        if isinstance(strip, str):
            strip = strip.lower() in ("1", "true")
        if isinstance(strip, bool):
            self.set_strip(strip)


if __name__ == "__main__":
    IGemUploader.run()
