# Python Version: 3.x
# -*- coding: utf-8 -*-
import json
import pathlib
import re
import requests  # https://pypi.python.org/pypi/requests
import sys


def get_data_pair(user, cache_dir):
    if not re.match('^[0-9A-Za-z]+$', user):
        raise ValueError()

    # read cache
    cache_path = pathlib.Path(cache_dir) / (user + '.json')
    if cache_path.exists():
        with cache_path.open() as fh:
            old_data = json.loads(fh.read())
    else:
        old_data = []

    # use the API
    url = 'http://kenkoooo.com/atcoder/atcoder-api/results?user=' + user
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()

    # write cache
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open('w') as fh:
        fh.write(json.dumps(data))

    return { 'new': data, 'old': old_data }


def get_accepted_delta(new, old):
    accepted = set()
    for row in new:
        accepted.add(row['problem_id'])
    for row in old:
        if row['problem_id'] in accepted:
            accepted.remove(row['problem_id'])
    return list(sorted(accepted))

def get_info_contests():
    url = 'http://kenkoooo.com/atcoder/atcoder-api/info/contests'
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    f = {}
    for row in data:
        f[row['id']] = row
    return f

def get_info_merged_problems():
    url = 'http://kenkoooo.com/atcoder/atcoder-api/info/merged-problems'
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    f = {}
    for row in data:
        f[row['id']] = row
    return f


appname = 'shoujin-slack-notifier'
default_config = {
    'users': [ 'kimiyuki', 'tourist' ],
    'webhook-url': 'https://hooks.slack.com/services/?????????/?????????/????????????????????????',
    'cache-dir': str(pathlib.Path('~/.cache/{}'.format(appname)).expanduser()),
}

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('users', nargs='*')
    parser.add_argument('--webhook-url')
    parser.add_argument('--config-file', type=pathlib.Path, default=pathlib.Path('~/.config/{}/config.json'.format(appname)).expanduser())
    parser.add_argument('--cache-dir')
    args = parser.parse_args()

    # load the config
    if not args.config_file.exists():
        args.config_file.parent.mkdir(parents=True, exist_ok=True)
        with args.config_file.open('w') as fh:
            fh.write(json.dumps(default_config))
    with args.config_file.open() as fh:
        args.config = json.loads(fh.read())

    # load default values
    if args.webhook_url is None:
        args.webhook_url = args.config['webhook-url']
    if len(args.users) == 0:
        args.users = args.config['users']
    if args.cache_dir is None:
        args.cache_dir = args.config['cache-dir']

    # notify
    info_contests = get_info_contests()
    info_problems = get_info_merged_problems()
    data = []
    for user in args.users:
        accepted = get_data_pair(user, cache_dir=args.cache_dir)
        delta = get_accepted_delta(new=accepted['new'], old=accepted['old'])
        if (len(delta) == 0):
            continue
        s = ''
        s += '_{}_ solved *{}* problems!\n'.format(user, len(delta))
        for problem_id in delta:
            contest_id = info_problems[problem_id]['contest_id']  # TODO: get correct ones even if there are many contests
            name = info_contests[contest_id]['title'] + ' ' + info_problems[problem_id]['title']
            point = info_problems[problem_id].get('point')
            url = 'https://beta.atcoder.jp/contests/{}/tasks/{}'.format(contest_id, problem_id)
            s += '{} {} {}\n'.format(name, '({} pts)'.format(int(point)) if point else '', url)
        data += [ {
            'name': user,
            'delta': delta,
            'str': s,
        } ]
    if not data:
        print('nothing to notify...', file=sys.stderr)
    else:
        data.sort(key=lambda x: len(x['delta']), reverse=True)
        print(data)
        payload = { 'text': '\n'.join([ row['str'] for row in data ]) }
        print(payload)
        resp = requests.post(args.webhook_url, data=json.dumps(payload))
        resp.raise_for_status()


if __name__ == '__main__':
    main()
