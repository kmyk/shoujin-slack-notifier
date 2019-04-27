# Python Version: 3.x
import contextlib
import datetime
import json
import os
import time
import traceback

import psycopg2
import requests

delay = os.environ.get('ATCODER_PROBLEMS_DELAY', 10)
name = os.environ.get('FRONTEND_DOMAIN', __name__)

def slack_message(webhook_url, text):
    resp = requests.post(webhook_url, data=json.dumps({'text': text}))
    resp.raise_for_status()

@contextlib.contextmanager
def db():
    config = {
        'host': os.environ['POSTGRES_HOST'],
        'user': os.environ['POSTGRES_USER'],
    }
    dsn = ' '.join(map('='.join, config.items()))
    with psycopg2.connect(dsn) as conn:
        conn.autocommit = True
        yield conn


def atcoder_problems(path):
    resp = requests.get('https://kenkoooo.com/atcoder{}'.format(path))
    resp.raise_for_status()
    data = json.loads(resp.content)
    return { row['id']: row for row in data }

def update_user(atcoder_id, problems, contests, cur):
    submissions = atcoder_problems('/atcoder-api/results?user={}'.format(atcoder_id))
    for submission in submissions.values():
        submission_url = 'https://atcoder.jp/contests/{}/submissions/{}'.format(submission['contest_id'], submission['id'])
        problem_url = 'https://atcoder.jp/contests/{}/tasks/{}'.format(submission['contest_id'], submission['problem_id'])
        contest = contests[submission['contest_id']]
        problem = problems[submission['problem_id']]
        problem_name = '{}: {}'.format(contest['title'], problem['title'])

        cur.execute('''
            INSERT INTO problems (problem_url, problem_name)
            VALUES (%s, %s)
            ON CONFLICT (problem_url) DO NOTHING
        ''', (problem_url, problem_name))

        cur.execute('''
            INSERT INTO submissions (submission_url, problem_url, user_id, result, score)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (submission_url) DO NOTHING
        ''', (submission_url, problem_url, atcoder_id, submission['result'], submission['point']))

def summarize_user(user_id, atcoder_id, last_reported, cur):
    cur.execute('''
        SELECT problem_url, problem_name, score, created_at
        FROM submissions JOIN problems USING (problem_url)
        WHERE user_id = %s AND result = 'AC' AND created_at > %s
    ''', (atcoder_id, last_reported))
    submissions = cur.fetchall()

    lines = []
    for problem_url, problem_name, score, created_at in submissions:
        cur.execute('''
            SELECT 1
            FROM submissions
            WHERE problem_url = %s AND user_id = %s AND result = 'AC' AND created_at < %s
        ''', (problem_url, atcoder_id, created_at))
        if cur.fetchone():
            continue
        lines += ['{} ({} pts) {}'.format(problem_name, score, problem_url)]

    count = len(lines)
    if count >= 20:
        lines = [ '(omitted...)' ]
    lines = ['@{} solved *{}* problems!'.format(user_id, count)] + lines
    text = '\n'.join(lines)
    return { 'count': count, 'text': text }

def report_room(room_id, webhook_url, problems, contests, conn):
    print('[*] report_room({})'.format(repr(room_id)))
    cur = conn.cursor()
    cur.execute('SELECT last_reported FROM last_reported WHERE room_id = %s', (room_id, ))
    row = cur.fetchone()
    if row:
        last_reported, = row
    else:
        last_reported = datetime.datetime.now()
        cur.execute('INSERT INTO last_reported (room_id, last_reported) VALUES (%s, %s)', (room_id, last_reported))
    cur.execute('SELECT user_id, atcoder_id FROM users WHERE room_id = %s', (room_id, ))
    users = cur.fetchall()

    try:
        for user_id, atcoder_id in users:
            update_user(atcoder_id, problems, contests, cur)
            time.sleep(delay)
    except Exception as e:
        traceback.print_exc()
        try:
            slack_message(webhook_url, '{}: `{}` at user @{}'.format(name, e.__class__.__name__, user_id))
        except:
            traceback.print_exc()
        return

    results = []
    for user_id, atcoder_id in users:
        result = summarize_user(user_id, atcoder_id, last_reported, cur)
        if result['count']:
            results += [result]
    results.sort(key=lambda result: result['count'], reverse=True)
    text = '\n\n'.join([result['text'] for result in results]).strip()

    if text:
        print(text)
        try:
            slack_message(webhook_url, text)
        except:
            traceback.print_exc()
        cur.execute('UPDATE last_reported SET last_reported = %s WHERE room_id = %s', (datetime.datetime.now(), room_id))


def report_all_rooms(conn):
    print('[*] report_all_rooms()')
    cur = conn.cursor()
    cur.execute('SELECT room_id, webhook_url FROM rooms WHERE activated = TRUE')
    rooms = cur.fetchall()

    try:
        contests = atcoder_problems('/resources/contests.json')
        problems = atcoder_problems('/resources/problems.json')
    except:
        traceback.print_exc()
        return

    for room_id, webhook_url in rooms:
        report_room(room_id, webhook_url, problems, contests, conn)

def main():
    today = datetime.date.today()
    while True:
        if today != datetime.date.today():
            today = datetime.date.today()
            with db() as conn:
                print('[*] begin')
                report_all_rooms(conn)
                print('[*] end')
        time.sleep(5 * 60)


if __name__ == '__main__':
    main()
