#!/usr/bin/python -u
import base64
import glob
import json
import mimetypes
from optparse import OptionParser
import os
import subprocess
import sys
import urllib
try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

if bytes == str:
    # Python 2
    def bytes(s, *args):
        return s
    def b2s(b):
        return b
else:
    # Python 3
    def b2s(b):
        return b.decode('utf-8')

    class unicode(object):
        pass

import uritemplate

API_BASE_URL = 'https://api.github.com'
ACCEPT_CONTENT_TYPE = 'application/vnd.github.v3+json'

GITHUB_USERNAME = os.environ.get('SPREEDBOX_UPLOAD_USERNAME')
GITHUB_ACCESS_TOKEN = os.environ.get('SPREEDBOX_UPLOAD_ACCESS_TOKEN')
IMAGES_ROOT = os.environ.get('SPREEDBOX_IMAGES_ROOT')

GITHUB_OWNER = 'strukturag'
GITHUB_REPOSITORY = 'spreedbox-firmware'

class MethodAwareRequest(urllib2.Request):

    def __init__(self, *args, **kw):
        self.__method = kw.pop('method', None)
        urllib2.Request.__init__(self, *args, **kw)

    def get_method(self):
        if self.__method:
            return self.__method
        return urllib2.Request.get_method(self)

def get_tags():
    cmd = subprocess.Popen([
        'git',
        'log',
        '--date-order',
        '--tags',
        '--simplify-by-decoration',
        '--pretty=format:%H %D',
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdoutdata, stderrdata) = cmd.communicate()
    assert cmd.returncode == 0, (cmd.returncode, stderrdata)

    result = []
    for line in stdoutdata.split('\n'):
        if not line:
            continue

        commit, line = line.split(' ', 1)
        parts = line.split(', ')
        for p in parts:
            if p.startswith('tag:'):
                result.append((p[4:].strip(), commit))
                break

    return result

def get_diff(ref1, ref2, filename):
    cmd = subprocess.Popen([
        'git',
        'diff',
        '%s..%s' % (ref1, ref2),
        filename,
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdoutdata, stderrdata) = cmd.communicate()
    assert cmd.returncode == 0, (cmd.returncode, stderrdata)
    return stdoutdata

def main():
    parser = OptionParser("usage: %prog [options] tagname")
    parser.add_option("-u", "--username", dest="username", default=GITHUB_USERNAME,
                  help="GitHub username to use [default: %default]", metavar="USERNAME")
    parser.add_option("-t", "--token", dest="token", default=GITHUB_ACCESS_TOKEN,
                  help="GitHub access token for given user [default: %default]")
    parser.add_option("-r", "--root", dest="root", default=IMAGES_ROOT,
                  help="Root folder containing images [default: %default]", metavar="FOLDER")
    parser.add_option("-d", "--no-draft", dest="no_draft", default=False, action="store_true",
                  help="Don't mark release as \"draft\"")
    parser.add_option("-p", "--prerelease", dest="prerelease", default=False, action="store_true",
                  help="Mark release as \"pre-release\"")
    (options, args) = parser.parse_args()

    if not options.username:
        parser.error('\nNo GitHub username given or set in SPREEDBOX_UPLOAD_USERNAME environment variable.')
    if not options.token:
        parser.error('\nNo GitHub access token given or set in SPREEDBOX_UPLOAD_ACCESS_TOKEN environment variable.\n' \
            'You can generate a new token at https://github.com/settings/tokens')
    if not options.root:
        parser.error('\nNo images root folder given or set in SPREEDBOX_IMAGES_ROOT environment variable.')
    if not args:
        parser.error('No tagname given')

    tag_name = args[0]

    # The release name should not start with a "v".
    if tag_name[:1] == 'v':
        release_name = tag_name[1:]
    else:
        release_name = tag_name

    release_folder = os.path.join(options.root, release_name)
    if not os.path.isdir(release_folder):
        parser.error('Folder %s does not exist for tag %s' % (release_folder, tag_name))

    image_filenames = glob.glob(os.path.join(release_folder, '*.img.xz'))
    if not image_filenames:
        parser.error('No images found in %s' % (release_folder))

    tags = get_tags()
    prev_tag = None
    for idx, (tag, commit) in enumerate(tags):
        if tag == tag_name:
            try: prev_tag = tags[idx+1]
            except IndexError: pass

    if not prev_tag:
        release_body = 'This is the first release.'
    else:
        release_body = 'Differences in manifest between %s and %s:\n\n' % (prev_tag[0], tag_name)
        release_body += '```diff\n' + get_diff(prev_tag[0], tag_name, 'MANIFEST.txt') + '\n```\n'

    raw_auth = "%s:%s" % (options.username, options.token)
    auth = 'Basic %s' % b2s(base64.b64encode(bytes(raw_auth, 'ascii')).strip())
    common_headers = {
        'Accept': ACCEPT_CONTENT_TYPE,
        'Authorization': auth,
    }
    base_url = API_BASE_URL + '/repos/' + GITHUB_OWNER + '/' + GITHUB_REPOSITORY
    opener = urllib2.build_opener()

    url = base_url + '/tags/' + tag_name
    req = urllib2.Request(url, headers=common_headers)
    try:
        response = opener.open(req)
    except urllib2.HTTPError as e:
        if e.code != 404:
            body = e.read()
            print >> sys.stderr, 'Could not check existing release: %s %s' % (e.code, e.msg)
            print >> sys.stderr, 'The server returned: %s' % (body)
            sys.exit(2)
    else:
        print >> sys.stderr, 'A release already exists for tag %s' % (tag_name)
        return

    url = base_url + '/releases'
    headers = {
        'Content-Type': 'application/json',
    }
    headers.update(common_headers)
    data = {
        'tag_name': tag_name,
        'name': release_name,
        'body': release_body,
        'draft': not options.no_draft,
        'prerelease': options.prerelease,
    }
    req = urllib2.Request(url, bytes(json.dumps(data), 'utf-8'), headers=headers)
    try:
        response = opener.open(req)
    except urllib2.HTTPError as e:
        body = e.read()
        print >> sys.stderr, 'Could not create release: %s %s' % (e.code, e.msg)
        print >> sys.stderr, 'The server returned: %s' % (body)
        sys.exit(2)

    body = response.read()
    headers = response.info()
    location = headers.get('Location')
    if not location:
        print >> sys.stderr, 'Release was created, but no location returned'
        print >> sys.stderr, 'The server returned: %s' % (body)
        sys.exit(3)

    try:
        try:
            body_data = json.loads(b2s(body))
            if not isinstance(body_data, dict):
                raise Exception('invalid type')
        except:
            print >> sys.stderr, 'The server returned invalid JSON: %s' % (body)
            sys.exit(2)

        upload_url = body_data.get('upload_url')
        if not upload_url:
            print >> sys.stderr, 'The server didn\'t return a \"upload_url\": %s' % (body)
            sys.exit(2)

        if isinstance(upload_url, unicode):
            upload_url = upload_url.encode('utf-8')

        for filename in image_filenames:
            print('Uploading %s' % (filename))
            url = uritemplate.expand(upload_url, {'name': os.path.basename(filename)})
            (mimetype, encoding) = mimetypes.guess_type(filename)
            if mimetype is None:
                mimetype = 'application/octet-stream'

            returncode = subprocess.call([
                'curl',
                '--progress-bar',
                '--output', '/dev/null',  # needed to make the progress bar visible
                '--data-binary', '@'+filename,
                '--user', raw_auth,
                '--header', 'Content-Type: ' + mimetype,
                url,
            ])
            assert returncode == 0, returncode
    except:
        print('Error while uploading files to the release, removing incomplete release')
        import traceback
        traceback.print_exc()

        req = MethodAwareRequest(location, headers=common_headers, method='DELETE')
        try:
            response = opener.open(req)
        except urllib2.HTTPError as e:
            body = e.read()
            print >> sys.stderr, 'Could not remove incomplete release: %s %s' % (e.code, e.msg)
            print >> sys.stderr, 'The server returned: %s' % (body)

if __name__ == '__main__':
    main()
