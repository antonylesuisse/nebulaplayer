# -*- coding: utf-8 -*-

import ast
import base64
import csv
import glob
import itertools
import logging
import operator
import datetime
import hashlib
import os
import re
import simplejson
import time
import urllib2
import xmlrpclib
import zlib
from xml.etree import ElementTree

import werkzeug.wrappers

import http

#----------------------------------------------------------
# helpers
#----------------------------------------------------------

def rjsmin(script):
    """ Minify js with a clever regex.
    Taken from http://opensource.perlig.de/rjsmin
    Apache License, Version 2.0 """
    def subber(match):
        """ Substitution callback """
        groups = match.groups()
        return (
            groups[0] or
            groups[1] or
            groups[2] or
            groups[3] or
            (groups[4] and '\n') or
            (groups[5] and ' ') or
            (groups[6] and ' ') or
            (groups[7] and ' ') or
            ''
        )

    result = re.sub(
        r'([^\047"/\000-\040]+)|((?:(?:\047[^\047\\\r\n]*(?:\\(?:[^\r\n]|\r?'
        r'\n|\r)[^\047\\\r\n]*)*\047)|(?:"[^"\\\r\n]*(?:\\(?:[^\r\n]|\r?\n|'
        r'\r)[^"\\\r\n]*)*"))[^\047"/\000-\040]*)|(?:(?<=[(,=:\[!&|?{};\r\n]'
        r')(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/'
        r'))*((?:/(?![\r\n/*])[^/\\\[\r\n]*(?:(?:\\[^\r\n]|(?:\[[^\\\]\r\n]*'
        r'(?:\\[^\r\n][^\\\]\r\n]*)*\]))[^/\\\[\r\n]*)*/)[^\047"/\000-\040]*'
        r'))|(?:(?<=[\000-#%-,./:-@\[-^`{-~-]return)(?:[\000-\011\013\014\01'
        r'6-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*((?:/(?![\r\n/*])[^/'
        r'\\\[\r\n]*(?:(?:\\[^\r\n]|(?:\[[^\\\]\r\n]*(?:\\[^\r\n][^\\\]\r\n]'
        r'*)*\]))[^/\\\[\r\n]*)*/)[^\047"/\000-\040]*))|(?<=[^\000-!#%&(*,./'
        r':-@\[\\^`{|~])(?:[\000-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/'
        r'*][^*]*\*+)*/))*(?:((?:(?://[^\r\n]*)?[\r\n]))(?:[\000-\011\013\01'
        r'4\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))*)+(?=[^\000-\040"#'
        r'%-\047)*,./:-@\\-^`|-~])|(?<=[^\000-#%-,./:-@\[-^`{-~-])((?:[\000-'
        r'\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)))+(?=[^'
        r'\000-#%-,./:-@\[-^`{-~-])|(?<=\+)((?:[\000-\011\013\014\016-\040]|'
        r'(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)))+(?=\+)|(?<=-)((?:[\000-\011\0'
        r'13\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/)))+(?=-)|(?:[\0'
        r'00-\011\013\014\016-\040]|(?:/\*[^*]*\*+(?:[^/*][^*]*\*+)*/))+|(?:'
        r'(?:(?://[^\r\n]*)?[\r\n])(?:[\000-\011\013\014\016-\040]|(?:/\*[^*'
        r']*\*+(?:[^/*][^*]*\*+)*/))*)+', subber, '\n%s\n' % script
    ).strip()
    return result

def sass2scss(src):
    # Validated by diff -u of sass2scss against:
    # sass-convert -F sass -T scss openerp.sass openerp.scss
    block = []
    sass = ('', block)
    reComment = re.compile(r'//.*$')
    reIndent = re.compile(r'^\s+')
    reIgnore = re.compile(r'^\s*(//.*)?$')
    reFixes = { re.compile(r'\(\((.*)\)\)') : r'(\1)', }
    lastLevel = 0
    prevBlocks = {}
    for l in src.split('\n'):
        l = l.rstrip()
        if reIgnore.search(l): continue
        l = reComment.sub('', l)
        l = l.rstrip()
        indent = reIndent.match(l)
        level = indent.end() if indent else 0
        l = l[level:]
        if level>lastLevel:
            prevBlocks[lastLevel] = block
            newBlock = []
            block[-1] = (block[-1], newBlock)
            block = newBlock
        elif level<lastLevel:
            block = prevBlocks[level]
        lastLevel = level
        if not l: continue
        # Fixes
        for ereg, repl in reFixes.items():
            l = ereg.sub(repl if type(repl)==str else repl(), l)
        block.append(l)

    def write(sass, level=-1):
        out = ""
        indent = '  '*level
        if type(sass)==tuple:
            if level>=0:
                out += indent+sass[0]+" {\n"
            for e in sass[1]:
                out += write(e, level+1)
            if level>=0:
                out = out.rstrip(" \n")
                out += ' }\n'
            if level==0:
                out += "\n"
        else:
            out += indent+sass+";\n"
        return out
    return write(sass)

def module_topological_sort(modules):
    """ Return a list of module names sorted so that their dependencies of the
    modules are listed before the module itself

    modules is a dict of {module_name: dependencies}

    :param modules: modules to sort
    :type modules: dict
    :returns: list(str)
    """

    dependencies = set(itertools.chain.from_iterable(modules.itervalues()))
    # incoming edge: dependency on other module (if a depends on b, a has an
    # incoming edge from b, aka there's an edge from b to a)
    # outgoing edge: other module depending on this one

    # [Tarjan 1976], http://en.wikipedia.org/wiki/Topological_sorting#Algorithms
    #L ← Empty list that will contain the sorted nodes
    L = []
    #S ← Set of all nodes with no outgoing edges (modules on which no other
    #    module depends)
    S = set(module for module in modules if module not in dependencies)

    visited = set()
    #function visit(node n)
    def visit(n):
        #if n has not been visited yet then
        if n not in visited:
            #mark n as visited
            visited.add(n)
            #change: n not web module, can not be resolved, ignore
            if n not in modules: return
            #for each node m with an edge from m to n do (dependencies of n)
            for m in modules[n]:
                #visit(m)
                visit(m)
            #add n to L
            L.append(n)
    #for each node n in S do
    for n in S:
        #visit(n)
        visit(n)
    return L

def module_installed(req):
    # Candidates module the current heuristic is the /static dir
    loadable = http.addons_manifest.keys()
    modules = {}
    sorted_modules = module_topological_sort(modules)
    return sorted_modules

def concat_xml(file_list):
    """Concatenate xml files

    :param list(str) file_list: list of files to check
    :returns: (concatenation_result, checksum)
    :rtype: (str, str)
    """
    checksum = hashlib.new('sha1')
    if not file_list:
        return '', checksum.hexdigest()

    root = None
    for fname in file_list:
        with open(fname, 'rb') as fp:
            contents = fp.read()
            checksum.update(contents)
            fp.seek(0)
            xml = ElementTree.parse(fp).getroot()

        if root is None:
            root = ElementTree.Element(xml.tag)
        #elif root.tag != xml.tag:
        #    raise ValueError("Root tags missmatch: %r != %r" % (root.tag, xml.tag))

        for child in xml.getchildren():
            root.append(child)
    return ElementTree.tostring(root, 'utf-8'), checksum.hexdigest()

def concat_files(file_list, reader=None, intersperse=""):
    """ Concatenates contents of all provided files

    :param list(str) file_list: list of files to check
    :param function reader: reading procedure for each file
    :param str intersperse: string to intersperse between file contents
    :returns: (concatenation_result, checksum)
    :rtype: (str, str)
    """
    checksum = hashlib.new('sha1')
    if not file_list:
        return '', checksum.hexdigest()

    if reader is None:
        def reader(f):
            with open(f, 'rb') as fp:
                return fp.read()

    files_content = []
    for fname in file_list:
        contents = reader(fname)
        checksum.update(contents)
        files_content.append(contents)

    files_concat = intersperse.join(files_content)
    return files_concat, checksum.hexdigest()

def concat_js(file_list):
    content, checksum = concat_files(file_list, intersperse=';')
    content = rjsmin(content)
    return content, checksum 

def manifest_glob(req, addons, key):
    if addons is None:
        addons = module_installed(req)
    else:
        addons = addons.split(',')
    r = []
    for addon in addons:
        manifest = http.addons_manifest.get(addon, None)
        if not manifest:
            continue
        # ensure does not ends with /
        addons_path = os.path.join(manifest['addons_path'], '')[:-1]
        globlist = manifest.get(key, [])
        for pattern in globlist:
            for path in glob.glob(os.path.normpath(os.path.join(addons_path, addon, pattern))):
                r.append((path, path[len(addons_path):]))
    return r

def manifest_list(req, mods, extension):
    if not req.debug:
        path = '/web/webclient/' + extension
        if mods is not None:
            path += '?mods=' + mods
        return [path]
    files = manifest_glob(req, mods, extension)
    i_am_diabetic = req.httprequest.environ["QUERY_STRING"].count("no_sugar") >= 1 or \
                    req.httprequest.environ.get('HTTP_REFERER', '').count("no_sugar") >= 1
    if i_am_diabetic:
        return [wp for _fp, wp in files]
    else:
        return ['%s?debug=%s' % (wp, os.path.getmtime(fp)) for fp, wp in files]

def get_last_modified(files):
    """ Returns the modification time of the most recently modified
    file provided

    :param list(str) files: names of files to check
    :return: most recent modification time amongst the fileset
    :rtype: datetime.datetime
    """
    files = list(files)
    if files:
        return max(datetime.datetime.fromtimestamp(os.path.getmtime(f))
                   for f in files)
    return datetime.datetime(1970, 1, 1)

def make_conditional(req, response, last_modified=None, etag=None):
    """ Makes the provided response conditional based upon the request,
    and mandates revalidation from clients

    Uses Werkzeug's own :meth:`ETagResponseMixin.make_conditional`, after
    setting ``last_modified`` and ``etag`` correctly on the response object

    :param req: OpenERP request
    :type req: web.common.http.WebRequest
    :param response: Werkzeug response
    :type response: werkzeug.wrappers.Response
    :param datetime.datetime last_modified: last modification date of the response content
    :param str etag: some sort of checksum of the content (deep etag)
    :return: the response object provided
    :rtype: werkzeug.wrappers.Response
    """
    response.cache_control.must_revalidate = True
    response.cache_control.max_age = 0
    if last_modified:
        response.last_modified = last_modified
    if etag:
        response.set_etag(etag)
    return response.make_conditional(req.httprequest)

#----------------------------------------------------------
# Controllers
#----------------------------------------------------------

html_template = """<!DOCTYPE html>
<html style="height: 100%%">
    <head>
        <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1"/>
        <meta http-equiv="content-type" content="text/html; charset=utf-8" />
        <title>NebulaPlayer</title>
        <link rel="shortcut icon" href="/web/static/src/img/favicon.ico" type="image/x-icon"/>
        <link rel="stylesheet" href="/web/static/src/css/full.css" />
        %(css)s
        %(js)s
        <script type="text/javascript">
            $(function() {
                var s = new openerp.init(%(modules)s);
                %(init)s
            });
        </script>
    </head>
    <body></body>
</html>
"""

class Home(http.Controller):
    _cp_path = '/'

    @http.httprequest
    def index(self, req, s_action=None, **kw):
        js = "\n        ".join('<script type="text/javascript" src="%s"></script>' % i for i in manifest_list(req, None, 'js'))
        css = "\n        ".join('<link rel="stylesheet" href="%s">' % i for i in manifest_list(req, None, 'css'))

        r = html_template % {
            'js': js,
            'css': css,
            'modules': simplejson.dumps(module_installed(req)),
            'init': 'var wc = new s.web.WebClient();wc.appendTo($(document.body));'
        }
        return r

    @http.httprequest
    def login(self, req, db, login, key):
        return login_and_redirect(req, db, login, key)

class Nebula(http.Controller):
    _cp_path = "/nebula"

    @http.jsonrequest
    def csslist(self, req, mods=None):
        return manifest_list(req, mods, 'css')

    @http.jsonrequest
    def jslist(self, req, mods=None):
        return manifest_list(req, mods, 'js')

    @http.jsonrequest
    def qweblist(self, req, mods=None):
        return manifest_list(req, mods, 'qweb')

    @http.httprequest
    def css(self, req, mods=None):
        files = list(manifest_glob(req, mods, 'css'))
        last_modified = get_last_modified(f[0] for f in files)
        if req.httprequest.if_modified_since and req.httprequest.if_modified_since >= last_modified:
            return werkzeug.wrappers.Response(status=304)

        file_map = dict(files)

        rx_import = re.compile(r"""@import\s+('|")(?!'|"|/|https?://)""", re.U)
        rx_url = re.compile(r"""url\s*\(\s*('|"|)(?!'|"|/|https?://|data:)""", re.U)

        def reader(f):
            """read the a css file and absolutify all relative uris"""
            with open(f, 'rb') as fp:
                data = fp.read().decode('utf-8')

            path = file_map[f]
            # convert FS path into web path
            web_dir = '/'.join(os.path.dirname(path).split(os.path.sep))

            data = re.sub(
                rx_import,
                r"""@import \1%s/""" % (web_dir,),
                data,
            )

            data = re.sub(
                rx_url,
                r"""url(\1%s/""" % (web_dir,),
                data,
            )
            return data.encode('utf-8')

        content, checksum = concat_files((f[0] for f in files), reader)

        return make_conditional(
            req, req.make_response(content, [('Content-Type', 'text/css')]),
            last_modified, checksum)

    @http.httprequest
    def js(self, req, mods=None):
        files = [f[0] for f in manifest_glob(req, mods, 'js')]
        last_modified = get_last_modified(files)
        if req.httprequest.if_modified_since and req.httprequest.if_modified_since >= last_modified:
            return werkzeug.wrappers.Response(status=304)

        content, checksum = concat_js(files)

        return make_conditional(
            req, req.make_response(content, [('Content-Type', 'application/javascript')]),
            last_modified, checksum)

    @http.httprequest
    def qweb(self, req, mods=None):
        files = [f[0] for f in manifest_glob(req, mods, 'qweb')]
        last_modified = get_last_modified(files)
        if req.httprequest.if_modified_since and req.httprequest.if_modified_since >= last_modified:
            return werkzeug.wrappers.Response(status=304)

        content, checksum = concat_xml(files)

        return make_conditional(
            req, req.make_response(content, [('Content-Type', 'text/xml')]),
            last_modified, checksum)

    @http.jsonrequest
    def modules(self, req):
        # return all installed modules. Web client is smart enough to not load a module twice
        return module_installed(req)

    @http.jsonrequest
    def load(self, req, path):
        """ Proxies an HTTP request through a JSON request.

        It is strongly recommended to not request binary files through this,
        as the result will be a binary data blob as well.

        :param req: OpenERP request
        :param path: actual request path
        :return: file content
        """
        from werkzeug.test import Client
        from werkzeug.wrappers import BaseResponse

        return Client(req.httprequest.app, BaseResponse).get(path).data


# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
