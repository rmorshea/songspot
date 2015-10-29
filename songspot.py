import os
import re
import ast
import sys
import json
import time
import tweepy
import getopt
import urllib2
import requests
import numpy as np
import random as rand
from warnings import warn
from apiclient.discovery import build
from apiclient.errors import HttpError
try:
    # python 2 import
    from urllib import FancyURLopener, urlretrieve
except ImportError:
    # python 3 import
    from urllib.requests import FancyURLopener, urlretrieve

sys.stdout.flush()

class RedditWarning(Warning):
    pass

class RedditError(Exception):
    pass

class SpotifyError(Exception):
    pass

class TwitterError(Exception):
    pass

class YouTubeError(Exception):
    pass


class SongSpotter(object):

    APP_INFO = {'language': 'python',
                 'name': 'songspot',
                 'version': 0.1}

    _header_pattern = r'(.*) (-|--) (.*) \[(.*)\].*'

    _reddit_field_defaults = {'item_limit': 75,
                              'agent_template': '%s:%s:%d (by /u/%s)',
                              'host': 'https://www.reddit.com/r/',
                              'username': os.environ.get('REDDIT_USERNAME'),
                              }
    _spotify_field_defaults = {'item_limit': 10,
                               'host': 'https://api.spotify.com/v1/',
                               'artist_keys': ['followers', 'id', 'name', 'popularity'],
                               'song_keys': ['name', 'popularity', 'external_urls', 'id']}

    def __init__(self, **kwargs):
        sys.stdout.flush()
        self.reddit_fields = self._reddit_field_defaults
        self.reddit_fields.update(kwargs.get('reddit_fields', {}))

        self.spotify_fields = self._spotify_field_defaults
        self.spotify_fields.update(kwargs.get('spotify_fields', {}))

        self.header_pattern = kwargs.get('header_pattern', self._header_pattern)

    def _reddit_user_agent(self):
        info = self.APP_INFO
        agent_name = self.reddit_fields['username']
        version_info_values = (info['language'], info['name'], info['version'], agent_name)
        version = self.reddit_fields['agent_template'] % version_info_values
        return type(agent_name.upper(), (FancyURLopener, object), {'version': version})()

    def reddit_data_pull(self, subreddit):
        sys.stdout.flush()
        host = self.reddit_fields['host']
        item_limit = self.reddit_fields['item_limit']
        url = host + subreddit + '/.json?limit=%d' % item_limit

        retrieve = self._reddit_user_agent().retrieve
        filepath, response = retrieve(url)

        with open(filepath, 'r') as f:
            raw = json.load(f)

        if 'error' in raw:
            if raw['error'] == 429:
                m = 'invalid User-Agent - limited data rates apply'
                warn(RetrieveWarning(m))
            else:
                m = 'error ' + str(raw['error']) + ' at '
                raise RedditError(m + url)

        return self._filter_reddit_results(raw)

    def _filter_reddit_results(self, raw_data):
        results = list()
        pattern = self.header_pattern
        regex = re.compile(pattern) if pattern else pattern
        children = raw_data['data']['children']
        for c in children:
            t = c['data']['title']
            match = regex.match(t)
            if not regex or match:
                groups = match.groups()
                artist, title = groups[0], groups[2]
                if 'remix' not in title.lower():
                    score = c['data']['score']
                    results.append((artist, title, score))
        return results

    def _base_spotify_query(self, query):
        # spotify client credentials authorization api
        client_id = os.environ.get('SPOTIFY_CLIENT_ID')
        client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
        auth = (client_id, client_secret)
        body_params = {'grant_type': 'client_credentials'}

        # make request for client token
        url = 'https://accounts.spotify.com/api/token'
        response = requests.post(url, data=body_params, auth=auth)
        content = ast.literal_eval(response.content)
        
        try:
            host = self.spotify_fields['host']
            item_limit = self.spotify_fields['item_limit']
            url = host + 'search?q=%s&limit=%d' % (query, item_limit)
            # make authorized request to spotify
            req = urllib2.request(url)
            token = content['access_token']
            token_type = content['token_type']
            req.add_header('Authorization', token_type+' '+token)
            filepath, response = urllib2.urlopen(req)

            with open(filepath, 'r') as f:
                raw = json.load(f)
        except:
            raw = {}

        if 'error' in raw:
            m = 'error ' + str(raw['error']) + ' at '
            raise SpotifyError(m + url)

        return raw

    def _spotify_query(self, artist, song):
        artist_query = artist.replace(' ','+') + '&type=artist'
        pull = self._base_spotify_query(artist_query)
        if pull:
            song_query = song.replace(' ','+') + '&type=track'
            pull.update(self._base_spotify_query(song_query))
            return pull

    def spotify_data_pull(self, artist, song):
        sys.stdout.flush()
        song = song.lower()
        artist = artist.lower()
        pull = self._spotify_query(artist, song)
        if pull and pull.get('artists') and pull.get('tracks'):
            for a in pull['artists']['items']:
                for s in pull['tracks']['items']:
                    if a['name'].lower() == artist:
                        if s['name'].lower() == song:
                            if artist in [e['name'].lower() for e in s['artists']]:
                                data = {'artist': {},
                                        'song': {}}
                                for k in self.spotify_fields['artist_keys']:
                                    data['artist'][k] = a[k]
                                for k in self.spotify_fields['song_keys']:
                                    data['song'][k] = s[k]
                                return data

    def cross_generate_results(self, *subreddits):
        found = list()
        sub_data = dict()
        for sr in subreddits:
            reddit_data = self.reddit_data_pull(sr)
            for artist, song, score in reddit_data:
                data = self.spotify_data_pull(artist, song)
                if data:
                    data['reddit-score'] = score
                    data['artist']['name'] = data['artist']['name'].title()
                    data['song']['name'] = data['song']['name'].title()
                    found.append(data)
        return ranked(found)


def ranked(entries):
    max_reddit_score = 0
    for e in entries:
        if e['reddit-score'] > max_reddit_score:
            max_reddit_score = e['reddit-score']
        e['reddit-scorecap'] = max_reddit_score
    return sorted(entries, key=lambda e: _rank(e), reverse=True)

def _rank(entry):
    a = entry['artist']['popularity']
    s = entry['song']['popularity']
    spotify_score = abs(float(a-s)/(a+s))
    
    r = entry['reddit-score']
    reddit_score = float(r)/entry['reddit-scorecap']
    del entry['reddit-scorecap']
    
    f = entry['artist']['followers']['total']
    follower_offset = np.exp(-f/10000)
    entry['songspot-score'] = spotify_score*10 + reddit_score + follower_offset

    return entry['songspot-score']


class TwitterBot(tweepy.OAuthHandler):

    _api_keys_and_tokens = '.api_keys_and_tokens.json'

    def __init__(self, callback=None):
        sys.stdout.flush()
        # gather credentials from environment variables
        consumer_key = os.environ.get('TWITTER_CONSUMER_KEY')
        consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET')
        super(TwitterBot, self).__init__(consumer_key, consumer_secret, callback)
        access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
        access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
        self.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(self)

    def tweet(self, status):
        self.api.update_status(status=status)

def youtube_search(query, max_results=5):
    sys.stdout.flush()
    api_key = os.environ.get('GOOGLE_API_KEY')
    service_name = os.environ.get('GOOGLE_SERVICE')
    service_version = os.environ.get('GOOGLE_SERVICE_VERSION')
    if service_name and service_version and api_key:
        youtube = build(service_name, service_version, developerKey=api_key)
    else:
        raise YouTubeError("No api credentials found "
                           " - setup with `init.sh`")

    search_response = youtube.search().list(q=query,
        part="id", maxResults = max_results).execute()

    videos = list()
    for result in search_response.get("items", []):
        if result["id"]["kind"] == "youtube#video":
          videos.append(result["id"]["videoId"])

    return videos

def _make_stale(post):
    with open(_cache_path+'stale.json', 'r') as f:
        cache = json.load(f)
    cache['stale'].append(post)
    if len(cache['stale'])>cache['item-limit']:
        cache['stale'] = sorted(cache['stale'], lambda p: p['post-time'])
        cache['stale'].pop(0)
    with open(_cache_path+'stale.json', 'w') as f:
        json.dump(cache, f, indent=4)

def _is_stale(post):
    with open(_cache_path+'stale.json', 'r') as f:
        cache = json.load(f)
    stale = sorted(cache['stale'], key=lambda p: p['post-time'], reverse=True)
    for i in range(len(stale)):
        if stale[i]['artist']['id'] == post['artist']['id']:
            if i < cache['item-limit']/4:
                return True
            if stale[i]['song']['id'] == post['song']['id']:
                return True
    return False

def _is_pending(post):
    with open(_cache_path+'pending.json', 'r') as f:
        cache = json.load(f)
        pending = cache['pending']
    for p in pending:
        if p['artist']['id'] == post['artist']['id']:
            if p['song']['id'] == post['song']['id']:
                return True
    return False

def _attempt_pend(post):
    with open(_cache_path+'pending.json', 'r') as f:
        cache = json.load(f)
    cache['pending'].append(post)
    cache['pending'] = sorted(cache['pending'], key=lambda e: e['songspot-score'])
    if len(cache['pending'])>cache['item-limit']:
        cache['pending'].pop(-1)
    with open(_cache_path+'pending.json', 'w') as f:
        json.dump(cache, f, indent=4)

def _gaussian_select(entries, sig_frac):
    sigma = int(len(entries)/sig_frac) or 1
    index = int(abs(rand.gauss(0, sigma or 1)))
    index = index if index < len(entries) else -1
    return entries[index]

def status_update(*subreddits, **kwargs):
    sigma_fraction = kwargs.get('sigma_fraction', 10)

    s = SongSpotter()
    results = s.cross_generate_results(*subreddits)

    with open(_cache_path+'pending.json', 'r') as f:
        cache = json.load(f)
        pending = cache['pending']

    select_from = sorted(results+pending, key=lambda e: e['songspot-score'])

    to_post = _gaussian_select(select_from, sigma_fraction)
    while _is_stale(to_post):
        to_post = _gaussian_select(select_from, sigma_fraction)
    try:
        i = pending.index(to_post)
        pending.pop(i)
        with open(_cache_path+'pending.json', 'w') as f:
            json.dump(cache, f, indent=4)
    except ValueError:
        i = results.index(to_post)
        results.pop(i)

    youtube_query = (to_post['artist']['name']+'+'+to_post['song']['name']).replace(' ','+')
    youtube_result = youtube_search(youtube_query)
    if len(youtube_result)==0:
        song_url = to_post['song']['external_urls']['spotify']
    else:
        song_url = 'https://www.youtube.com/v/' + youtube_result[0]
        to_post['song']['external_urls']['youtube'] = song_url

    post_title = to_post['artist']['name']+' - '+to_post['song']['name']
    artist_hashtag = '#' + to_post['artist']['name'].replace(' ','').lower()
    song_hashtag = '#' + to_post['song']['name'].replace(' ','').lower()
    status = post_title + '\n' + song_url
    if len(status) + len('\n'+artist_hashtag)<=140:
        status += '\n'+artist_hashtag
    if len(status)+len(' '+song_hashtag)<=140:
        status += ' '+song_hashtag
    if len(status) + len(' #lifeismusic')<=140:
        status += ' #lifeismusic'

    tbot = TwitterBot()
    to_post['post-time'] = time.time()
    tbot.tweet(status)
    _make_stale(to_post)
    sys.stdout.flush()

    for p in results[:len(results)/sigma_fraction or 1]:
        if not _is_pending(p):
            _attempt_pend(p)

    return to_post, select_from

def mod_status_update(artist, song):
    youtube_query = artist.title()+'+'+song.title()
    youtube_result = youtube_search(youtube_query)
    if len(youtube_result)==0:
        raise YouTubeError('No video found for: %s' % youtube_query)
    else:
        song_url = 'https://www.youtube.com/v/'+youtube_result[0]
    post_title = artist.title()+' - '+song.title()
    artist_hashtag = '#' + artist.replace(' ','').lower()
    song_hashtag = '#' + song.replace(' ','').lower()
    status = '[mod] ' + post_title + '\n' + song_url
    if len(status) + len('\n'+artist_hashtag)<=140:
        status += '\n'+artist_hashtag
    if len(status)+len(' '+song_hashtag)<=140:
        status += ' '+song_hashtag
    if len(status) + len(' #lifeismusic')<=140:
        status += ' #lifeismusic'
    return status

def usage():
    u = {'--help        ': 'list accepted command line flags',
         '--main=dict ': 'pass kwargs into `main` - given in the form "{key1: val1, key2: val2, ...}"',
         '--setup=dict  ': 'pass kwargs into `setup` - given in the form "{key1: val1, key2: val2, ...}"'}
    msg = ('setup',
           '-----',
           'cache_path : a series of subreddits the songspotter will pull from (default="cache/")',
           'cache_limit : the maximum number of post objects that can be cached (default=50)',
           'api_json : path to json containing required api security keys and tokens(default="api.json"',
           '',
           'main',
           '----',
           'subreddits : a tuple of subreddits that will be drawn from (default="listentothis")')

    for k, v in u.items():
        print(k, ':', v)
    print('')
    for l in msg:
        print(l)

def argmenter(opts, args, delimiters=(':','@')):
    arg_type = {'--': [], '-': [], None: []}
    kwarg_type = dict([('--', {})]+[(d, {}) for d in delimiters])
    for a in args:
        for d in delimiters:
            if d in a:
                key, value = a.split(d)
                kwarg_type[d][key] = value
                break
        else:
            arg_type[None].append(a)
    for a in opts:
        if a.startswith('--'):
            if '=' in a:
                key, value = a[2:].split('=')
                kwarg_type['--'][key] = value
            else:
                arg_type['--'].append(a[2:])
        elif a.startswith('-'):
            arg_type['-'].append(a[1:])
    return arg_type, kwarg_type

def setup_globals(**kwargs):
    new_globals = {}
    _cache_path = kwargs.pop('cache_path', './tmp/cache/')
    _setup_caching_folder(_cache_path, 50)
    new_globals['_cache_path'] = _cache_path
    return new_globals

def _setup_caching_folder(cache_path, item_limit):
    # setup caching folder
    if not os.path.exists(cache_path):
        os.makedirs(cache_path)

    # setup cache for posted material
    used = cache_path+'stale.json'
    if not os.path.isfile(used):
        with open(used, 'w') as f:
            json.dump({'stale': [], 'item-limit': item_limit}, f, indent=4)

    # setup cache for unused material
    unused = cache_path+'pending.json'
    if not os.path.isfile(unused):
        with open(unused, 'w') as f:
            json.dump({'pending': [], 'item-limit': item_limit}, f, indent=4)

    return cache_path

if __name__ == '__main__':
    # process sys args
    argv = sys.argv[1:]
    try:
        longs = ['help', 'subreddits=', 'cache_path=', 'api_json=']
        opts, args = getopt.getopt(argv, 'h', longs)
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    else:
        if '--help' in opts:
            usage()
            sys.exit(2)
    arg_types, kwarg_types = argmenter(args, opts)
    for k, v in setup_globals(**kwarg_types['--']).items():
        globals()[k] = v

    one_hour = 60*60 # seconds
    half_hour = one_hour/2
    five_hours = one_hour*5

    while True:
        if int(time.time())%(five_hours)<one_hour:
            status_update('listentothis')
        time.sleep(one_hour)
