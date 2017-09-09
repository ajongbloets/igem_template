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
            result = self.upload_html(source, destination)
        if extension in ("js", "css"):
            result = self.upload_resource(source, destination)
        # images
        return result

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
            self.get_logger().info("Upload html {} to {}".format(source, name))
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
            self.get_logger().info("Upload resource {} to {}".format(source, name))
            # upload
            result = self.edit(name, content)
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
        self.get_logger().debug("Changed href {} to {}".format(href, uri))
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
        self.get_logger().debug("Changed src {} to {}".format(src, uri))
        # element.set("src", uri)
        element["src"] = uri
        return element

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
