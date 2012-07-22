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

from hashlib import md5
import os
import sys
from urlparse import urlparse
import xml.dom.minidom as minidom

from html2text import html2text


# Change this to point to the name of your Blogger export file
ATOM_BACKUP_FILENAME = '../feedingthecloud.xml'

LICENSE_LINK = '[Creative Commons Attribution-Share Alike 3.0 New Zealand License](http://creativecommons.org/licenses/by-sa/3.0/nz/)'

AUTHOR_URL_REPLACEMENTS = {'http://www.blogger.com/profile/15799633745688818389': 'http://fmarier.org'}


def get_author_name(entry):
    author = entry.getElementsByTagName('author').item(0)
    nametag = author.getElementsByTagName('name').item(0)
    textnode = nametag.firstChild
    return textnode.nodeValue


def get_author_uri(entry):
    author = entry.getElementsByTagName('author').item(0)
    uritags = author.getElementsByTagName('uri')
    if uritags:
        textnode = uritags.item(0).firstChild
        url = textnode.nodeValue
        if url in AUTHOR_URL_REPLACEMENTS:
            return AUTHOR_URL_REPLACEMENTS[url]
        else:
            return url
    return None


def get_date(entry, datename):
    datetag = entry.getElementsByTagName(datename).item(0)
    textnode = datetag.firstChild
    return textnode.nodeValue


def get_title(entry):
    titletag = entry.getElementsByTagName('title').item(0)
    textnode = titletag.firstChild
    return textnode.nodeValue


def get_permalink(entry):
    links = entry.getElementsByTagName('link')
    for link in links:
        schemeattr = link.getAttribute('rel')
        typeattr = link.getAttribute('type')
        if schemeattr == 'alternate' and typeattr == 'text/html':
            href = link.getAttribute('href').split('?')
            return href[0]

def escape_most_tags(line):
    line = line.replace('<i>', 'OPEN_BRACKET_I_CLOSE_BRACKET')
    line = line.replace('</i>', 'OPEN_BRACKET_SLASH_I_CLOSE_BRACKET')
    line = line.replace('<b>', 'OPEN_BRACKET_B_CLOSE_BRACKET')
    line = line.replace('</b>', 'OPEN_BRACKET_SLASH_B_CLOSE_BRACKET')

    line = line.replace('<', '&lt;')
    line = line.replace('>', '&gt;')

    line = line.replace('OPEN_BRACKET_I_CLOSE_BRACKET', '<i>')
    line = line.replace('OPEN_BRACKET_SLASH_I_CLOSE_BRACKET', '</i>')
    line = line.replace('OPEN_BRACKET_B_CLOSE_BRACKET', '<b>')
    line = line.replace('OPEN_BRACKET_SLASH_B_CLOSE_BRACKET', '</b>')
    return line

def post_process_pre(text):
    out = []

    lines = text.split("\n")
    in_pre = False
    pre_lines = []
    for line in lines:
        if "<!-- START PRE -->" == line:
            in_pre = True
            pre_lines = []
        elif "<!-- END PRE WITHOUT TAGS -->" == line:
            in_pre = False
            out.append('')
            out += pre_lines
            out.append('')
        elif "<!-- END PRE WITH TAGS -->" == line:
            in_pre = False
            out.append('<pre>')
            # remove the indentation and add <pre> and </pre> tags
            for l in pre_lines:
                out.append(escape_most_tags(l[4:]))
            out.append('</pre>')
        elif in_pre:
            pre_lines.append(line)
        else:
            out.append(line)

    return "\n".join(out)


def get_content(entry):
    contenttag = entry.getElementsByTagName('content').item(0)
    textnode = contenttag.firstChild
    html = textnode.nodeValue

    # Fixups for bad interactions later
    html = html.replace('<blockquote><pre>', '<pre>').replace('</pre></blockquote>', '</pre>')
    html = html.replace('<blockquote><code>', '<pre>').replace('</code></blockquote>', '</pre>')
    html = html.replace('<tt><b>', '<b><tt>').replace('</b></tt>', '</tt></b>')
    html = html.replace('<code></code>', '').replace('<tt></tt>', '')
    html = html.replace('<br /></li><li>', '</li><li>')
    text = html2text(html)
    return post_process_pre(text)


def extract_filename(permalink):
    components = urlparse(permalink)
    paths = components.path.split('/')
    filename = paths[-1]
    return filename.split('.html')[0] + '.mdwn'


def print_post(entry, tags):
    published_date = get_date(entry, 'published')
    updated_date = get_date(entry, 'updated')

    author = get_author_name(entry)
    title = get_title(entry).replace('"', '&quot;')
    permalink = get_permalink(entry)
    filename = extract_filename(permalink)
    content = get_content(entry)

    s = '[[!meta title="' + title + '"]]' + "\n"
    s += '[[!meta date="' + published_date + '"]]' + "\n"
    s += '[[!meta license="' + LICENSE_LINK + '"]]' + "\n"
    s += content + "\n"
    for tag in tags:
        s += "[[!tag " + tag + "]] "
    return (filename, s)


def print_comment(entry):
    published_date = get_date(entry, 'published')
    updated_date = get_date(entry, 'updated')

    author_name = get_author_name(entry)
    author_uri = get_author_uri(entry)

    permalink = get_permalink(entry)
    filename = extract_filename(permalink)
    content = get_content(entry)

    s = '[[!comment format=mdwn' + "\n"
    if author_uri:
        s += ' username="' + author_uri + '"' + "\n"
        s += ' nickname="' + author_name + '"' + "\n"
    else:
        s += ' claimedauthor="' + author_name + '"' + "\n"
    s += ' subject=""' + "\n"
    s += ' date="' + published_date + '"' + "\n"
    s += ' content="""' + "\n"
    s += content + "\n"
    s += '"""]]' + "\n"

    return (filename, s)


numbers = {}
def comment_number(post_filename):
    if post_filename not in numbers:
        numbers[post_filename] = 0

    numbers[post_filename] += 1
    return str(numbers[post_filename])


def save_file(filename, contents):
    with open(filename, 'w') as f:
        f.write(contents.encode('utf8'))
    f.close()


def save_comment(post_filename, contents):
    directory = post_filename.split('.mdwn')[0]
    if not os.path.isdir(directory):
        os.mkdir(directory)

    comment_guid = md5(contents.encode('utf8')).hexdigest()
    filename = 'comment_' + comment_number(post_filename) + '_' + comment_guid + '._comment'

    return save_file(directory + '/' + filename, contents)


document = minidom.parse(ATOM_BACKUP_FILENAME)
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
        (filename, post) = print_post(entry, tags)
        save_file(filename, post)
    elif is_comment:
        (filename, comment) = print_comment(entry)
        save_comment(filename, comment)
