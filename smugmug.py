#!/usr/bin/python

##########
# Requirements: Python 2.6 or
#               simplejson from http://pypi.python.org/pypi/simplejson
##########

import smugsettings

EMAIL=smugsettings.EMAIL
PASSWORD=smugsettings.PASSWORD

##########
APIKEY=smugsettings.APIKEY
API_VERSION='1.2.0'
API_URL='https://api.smugmug.com/hack/json/1.2.0/'
UPLOAD_URL='http://upload.smugmug.com/photos/xmlrawadd.mg'

import sys, re, urllib, urllib2, urlparse, hashlib, traceback, os
try    : import json
except : import simplejson as json

if len(sys.argv) < 3 :
    print 'Usage:'
    print '  upload.py  album  picture1  [picture2  [...]]'
    print
    print '  --auto for album reads the album name from'
    print '    the first line of the .smugmug file.'
    print '  --missing-files for picture1 uploads all files'
    print '    not already in the album.'
    sys.exit(0)

album_name = sys.argv[1]
su_cookie  = None

def safe_geturl(request) :
    global su_cookie

    # Try up to three times
    for x in range(5) :
        result = {}
        response = None
        try :
            response_obj = urllib2.urlopen(request)
            response = response_obj.read()
            result = json.loads(response)

            # Test for presence of _su cookie and consume it
            meta_info = response_obj.info()
            if meta_info.has_key('set-cookie') :
                match = re.search('(_su=\S+);', meta_info['set-cookie'])
                if match and match.group(1) != "_su=deleted" :
                    su_cookie = match.group(1)
            if result['stat'] != 'ok' : raise Exception('Bad result code')
            return result
        except :
            if x < 4 and ('code' not in result or result['code'] != 64):
                print "  ... failed, retrying"
            else :
                print "  ... failed, giving up"
                print "  Request was:"
                print "  " + request.get_full_url()
                try :
                    print "  Response was:"
                    print response
                except :
                    pass
                traceback.print_exc()
                #sys.stdin.readline()
                #sys.exit(1)
                return result

def smugmug_request(method, params) :
    global su_cookie

    paramstrings = [urllib.quote(key)+'='+urllib.quote(params[key]) for key in params]
    paramstrings += ['method=' + method]
    url = urlparse.urljoin(API_URL, '?' + '&'.join(paramstrings))
    request = urllib2.Request(url)
    if su_cookie :
        request.add_header('Cookie', su_cookie)
    return safe_geturl(request)


def get_album_filenames(album_id, album_key):
    result = smugmug_request('smugmug.images.get',
                             {'SessionID' : session,
                              'AlbumID' : str(album_id),
                              'AlbumKey' : album_key,
                              'Heavy' : 'true'})
    try:
        filenames = map(lambda x: x['FileName'], result['Images'])
    except KeyError:
        filenames = []
    return filenames


def get_missing_files(album_filenames):
    album_filenames_set = set(album_filenames)
    local_filenames_set = set(os.listdir('.'))
    missing_filenames_set = local_filenames_set - album_filenames_set
    missing_filenames_set = filter(lambda x: not x.startswith('.'), missing_filenames_set)
    return sorted(missing_filenames_set)


# for now the config file is a single line containing the album name
def read_config_file():
    with open('.smugmug', 'r') as f:
        configlines = f.read().splitlines()
        return configlines[0]


result = smugmug_request('smugmug.login.withPassword',
                         {'APIKey'       : APIKEY,
                          'EmailAddress' : EMAIL,
                          'Password'     : PASSWORD})
session = result['Login']['Session']['id']

if album_name == '--auto':
    album_name = read_config_file()

result = smugmug_request('smugmug.albums.get', {'SessionID' : session})
album_id = None
for album in result['Albums'] :
    if album['Title'] == album_name :
        album_id = album['id']
        album_key = album['Key']
        break
if album_id is None :
    print 'That album does not exist'
    sys.exit(1)


if sys.argv[2] == '--list-files':
    filenames = get_album_filenames(album_id, album_key)
    for filename in filenames:
        print filename
    sys.exit(0)
elif sys.argv[2] == '--missing-files' or sys.argv[2] == '--print-missing-files':
    filenames = get_album_filenames(album_id, album_key)
    filenames = get_missing_files(filenames)
    if sys.argv[2] == '--print-missing-files':
        for filename in filenames:
            print filename
        sys.exit(0)
elif sys.argv[2].startswith("--file-list="):
    filelist_filename = sys.argv[2].split('=')[1]
    with open(filelist_filename, 'r') as f:
        filenames = f.read().splitlines()
else:
    filenames = sys.argv[2:]

for filename in filenames :
    data = open(filename, 'rb').read()
    print 'Uploading ' + filename
    upload_request = urllib2.Request(UPLOAD_URL,
                                     data,
                                     {'Content-Length'  : len(data),
                                      'Content-MD5'     : hashlib.md5(data).hexdigest(),
                                      'Content-Type'    : 'none',
                                      'X-Smug-SessionID': session,
                                      'X-Smug-Version'  : API_VERSION,
                                      'X-Smug-ResponseType' : 'JSON',
                                      'X-Smug-AlbumID'  : album_id,
                                      'X-Smug-FileName' : os.path.basename(filename) })
    result = safe_geturl(upload_request)
    if result['stat'] == 'ok' :
        print "  ... successful"

print 'Done'
# sys.stdin.readline()
