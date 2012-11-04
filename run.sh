#!/bin/bash
#
# Quickly re-convert the blog and commit to a local test instance of ikiwiki

SCRIPT_DIR=~/devel/remote/blogger2ikiwiki
BLOG_DIR=~/ikiwiki/FeedingtheCloud

cd $SCRIPT_DIR && rm -rf temp/
mkdir -p temp/
(cd temp && ../blogger2ikiwiki.py) || exit 1
cd $BLOG_DIR && git rm --quiet -r posts
mkdir -p $BLOG_DIR/posts
cp -r $SCRIPT_DIR/temp/* $BLOG_DIR/posts/
rm $BLOG_DIR/posts/apache-aliases.conf
cd $BLOG_DIR && git add posts && git commit --quiet -a -m "re-ran script" && git push
