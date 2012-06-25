#!/usr/bin/python
#
# Blogger to Ikiwiki conversion tool
# Copyright (C) 2012  Francois Marier <francois@fmarier.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import xml.dom.minidom as minidom


def get_author(entry):
    author = entry.getElementsByTagName('author').item(0)
    nametag = author.getElementsByTagName('name').item(0)
    textnode = nametag.firstChild
    return textnode.nodeValue


def get_date(entry, datename):
    datetag = entry.getElementsByTagName(datename).item(0)
    textnode = datetag.firstChild
    return textnode.nodeValue


def get_title(entry):
    titletag = entry.getElementsByTagName('title').item(0)
    textnode = titletag.firstChild
    return textnode.nodeValue


def print_post(entry, tags):
    published_date = get_date(entry, 'published')
    updated_date = get_date(entry, 'updated')
    author = get_author(entry)
    title = get_title(entry)
    permalink = 'TODO'
    print title + ' [' + ', '.join(tags) + '] by ' + author

def print_comment(entry):
    print get_author(entry)


document = minidom.parse('feedingthecloud.xml')
feed = document.getElementsByTagName('feed').item(0)

entries = feed.getElementsByTagName('entry')
for entry in entries:
    is_post = False
    is_comment = False

    tags = []

    categories = entry.getElementsByTagName('category')
    for category in categories:
        scheme = category.getAttribute('scheme')
        if scheme == 'http://schemas.google.com/g/2005#kind':
            term = category.getAttribute('term')
            if term == 'http://schemas.google.com/blogger/2008/kind#post':
                is_post = True
            elif term == 'http://schemas.google.com/blogger/2008/kind#comment':
                is_comment = True
        elif scheme == 'http://www.blogger.com/atom/ns#':
            term = category.getAttribute('term')
            tags.append(term)

    if is_post:
        print_post(entry, tags)
