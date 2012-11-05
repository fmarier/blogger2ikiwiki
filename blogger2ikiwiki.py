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
import re
import sys
import urllib2
from urlparse import urlparse
import xml.dom.minidom as minidom

from html2text import html2text


# Change this to point to the name of your Blogger export file
ATOM_BACKUP_FILENAME = '../feedingthecloud.xml'

LICENSE_LINK = '[Creative Commons Attribution-Share Alike 3.0 New Zealand License](http://creativecommons.org/licenses/by-sa/3.0/nz/)'

AUTHOR_URL_REPLACEMENTS = {'http://www.blogger.com/profile/15799633745688818389': 'http://fmarier.org'}

# Must include the trailing slash!
BLOG_URL = 'http://feeding.cloud.geek.nz/'

TAGGED_FEEDS = ['debian', 'mozilla', 'nzoss', 'ubuntu', 'postgres', 'sysadmin', 'django', 'python', 'nodejs']


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


def post_process_tt_code(text):
    out = []

    lines = text.split("\n")
    in_pre = False
    pre_lines = []
    for line in lines:
        if "<!-- START TT -->" in line:
            if "<!-- END TT WITHOUT TAGS -->" in line:
                out.append(line.replace('<!-- START TT -->', '`').replace('<!-- END TT WITHOUT TAGS -->', '`'))
            elif "<!-- END TT WITH TAGS -->" in line:
                out.append(line.replace('<!-- START TT -->', '<tt>').replace('<!-- END TT WITH TAGS -->', '</tt>'))
        elif "<!-- START CODE -->" in line:
            if "<!-- END CODE WITHOUT TAGS -->" in line:
                out.append(line.replace('<!-- START CODE -->', '`').replace('<!-- END CODE WITHOUT TAGS -->', '`'))
            elif "<!-- END CODE WITH TAGS -->" in line:
                out.append(line.replace('<!-- START CODE -->', '<code>').replace('<!-- END CODE WITH TAGS -->', '</code>'))
        else:
            out.append(line)

    return "\n".join(out)


image_regexp = re.compile('\[!\[\]\([^)]+\)\]\(([^)]+)\)')
htmlimage_regexp = re.compile('(\(http://([^.]+.){2}blogspot.com/[^()]+/)s1600-h/')
filename_regexp = re.compile('.*/([^/]+\.(jpg|png))')
def post_process_images(text, image_directory):
    local_images = {}

    # Fix image links going to HTML pages
    text = htmlimage_regexp.sub(r'\1s1600/', text)

    # Find full-size Blogger-hosted images
    images = image_regexp.finditer(text)
    for image in images:
        image_url = image.group(1)
        m = filename_regexp.match(image_url)
        if m:
             fh = urllib2.urlopen(image_url)
             contents = fh.read()

             # Save to disk
             filename = m.group(1)
             with open("%s/%s" % (image_directory, filename), 'w') as f:
                 f.write(contents)

             local_images[image_url] = filename
        else:
            print 'ERROR: unsupported Blogger image URL'

    # Output the final image tag
    text = image_regexp.sub(r'![](\1)', text)

    # Convert the Blogger-hosted URLs to the local filenames
    for blogger_url in local_images:
        text = text.replace(blogger_url, local_images[blogger_url])

    return text


def post_process(text, post_filename, is_comment):
    text = post_process_pre(text)
    text = post_process_tt_code(text)

    if not is_comment:
        image_directory = post_filename.split('.mdwn')[0]
        if not os.path.isdir(image_directory):
            os.mkdir(image_directory)
        text = post_process_images(text, image_directory)

    return text


def get_content(entry, post_filename, is_comment):
    contenttag = entry.getElementsByTagName('content').item(0)
    textnode = contenttag.firstChild
    html = textnode.nodeValue

    # Fixups for bad interactions later
    html = html.replace('<blockquote><pre>', '<pre>').replace('</pre></blockquote>', '</pre>')
    html = html.replace('<blockquote><code>', '<pre>').replace('</code></blockquote>', '</pre>')
    html = html.replace('<blockquote><tt>', '<pre>').replace('</tt></blockquote>', '</pre>')
    html = html.replace('</tt><br /></blockquote>', '</pre>')
    html = html.replace('<pre><blockquote>', '<pre>').replace('</blockquote></pre>', '</pre>')
    html = html.replace('<tt><b>', '<b><tt>').replace('</b></tt>', '</tt></b>')
    html = html.replace('<tt><a ', '<a ').replace('</a></tt>', '</a>')
    html = html.replace('<code></code>', '').replace('<tt></tt>', '')
    html = html.replace('<br /></li><li>', '</li><li>')

    if is_comment:
        # Hacks specific to misinterpreted codes in the original plaintext
        html = html.replace('<BR/>#',  '<br />\#')
        html = html.replace('<BR/>*',  '<br />\*')
        html = html.replace('<br />#',  '<br />\#')
        html = html.replace('<br />-- <br />',  '<br />')

    text = html2text(html)
    return post_process(text, post_filename, is_comment)


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
    content = get_content(entry, filename, False)

    s = '[[!meta title="' + title + '"]]' + "\n"
    s += '[[!meta date="' + published_date + '"]]' + "\n"
    s += '[[!meta license="' + LICENSE_LINK + '"]]' + "\n"
    s += content + "\n"
    for tag in tags:
        s += "[[!tag " + tag + "]] "
    return (filename, s, permalink)


def print_comment(entry):
    published_date = get_date(entry, 'published')
    updated_date = get_date(entry, 'updated')

    author_name = get_author_name(entry)
    author_uri = get_author_uri(entry)

    permalink = get_permalink(entry)
    filename = extract_filename(permalink)
    content = get_content(entry, filename, True)

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


def old_and_new_urls(permalink):
    components = urlparse(permalink)
    paths = components.path.split('/')
    filename = paths[-1]
    new_url = BLOG_URL + 'posts/' + filename.split('.html')[0] +  '/'
    return (components.path, new_url)


def save_rewrite_rules(filename, rewrite_rules):
    with open(filename, 'w') as f:
        f.write("# These rules require that mod_alias be enabled\n\n")

        if TAGGED_FEEDS:
            f.write("# Tagged feeds\n")
            for tag in TAGGED_FEEDS:
                old_tag_path = '/feeds/posts/default/-/%s' % tag
                new_tag_url = BLOG_URL + 'tags/%s/index.rss' % tag
                f.write("Redirect permanent %s %s\n" % (old_tag_path, new_tag_url))

                old_tag_path = '/search/label/%s' % tag
                new_tag_url = BLOG_URL + 'tags/%s' % tag
                f.write("Redirect permanent %s %s\n" % (old_tag_path, new_tag_url))
            f.write("\n")

        f.write("# Articles\n")
        for rule in rewrite_rules:
            f.write("Redirect permanent %s %s\n" % (rule[0], rule[1]))
    f.close()


document = minidom.parse(ATOM_BACKUP_FILENAME)
feed = document.getElementsByTagName('feed').item(0)

rewrite_rules = []
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
        (filename, post, permalink) = print_post(entry, tags)
        save_file(filename, post)
        rewrite_rules.append(old_and_new_urls(permalink))
    elif is_comment:
        (filename, comment) = print_comment(entry)
        save_comment(filename, comment)

save_rewrite_rules("apache-aliases.conf", rewrite_rules)
