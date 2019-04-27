# Python Version: 3.x
import binascii
import contextlib
import json
import os

import flask
import jinja2
import psycopg2
import requests

app = flask.Flask(__name__)


def isident(s):
    return s and s[0].isalnum() and all([ c.isalnum() or c in '-_' for c in s ])


def slack_message(webhook_url, text):
    resp = requests.post(webhook_url, data=json.dumps({'text': text}))
    resp.raise_for_status()


def db():
    if not hasattr(flask.g, 'db'):
        config = {
            'host': os.environ['POSTGRES_HOST'],
            'user': os.environ['POSTGRES_USER'],
        }
        dsn = ' '.join(map('='.join, config.items()))
        flask.g.db = psycopg2.connect(dsn)
        flask.g.db.autocommit = True
    return flask.g.db


@app.route('/')
def get_index():
    return flask.render_template('index.html')


@app.route('/room/list')
def get_rooms():
    cur = db().cursor()
    cur.execute('SELECT room_id, activated FROM rooms')
    rooms = [dict(zip(['room_id', 'activated'], row)) for row in cur.fetchall()]
    data = {
        'ok': True,
        'rooms': rooms,
    }
    return flask.jsonify(data)


@app.route('/room/new', methods=['POST'])
def post_room_new():
    room_id = flask.request.form['room_id']
    webhook_url = flask.request.form['webhook_url']

    if not isident(room_id):
        flask.abort(400)

    cur = db().cursor()

    # remove if not activated
    cur.execute('DELETE FROM rooms WHERE room_id = %s AND activated = FALSE', (room_id, ))

    # check
    cur.execute('SELECT 1 FROM rooms WHERE room_id = %s', (room_id, ))
    if cur.fetchone():
        flask.abort(400)

    # insert
    token = binascii.hexlify(os.urandom(16)).decode()
    cur.execute('INSERT INTO rooms (room_id, webhook_url, token) VALUES (%s, %s, %s)', (room_id, webhook_url, token))
    slack_message(webhook_url, 'registered  (token = `{}`)'.format(token))
    return flask.jsonify({ 'ok': True })


@app.route('/room/token', methods=['POST'])
def post_room_token():
    room_id = flask.request.form['room_id']

    cur = db().cursor()
    cur.execute('SELECT webhook_url FROM rooms WHERE room_id = %s', (room_id, ))
    row = cur.fetchone()
    if not row:
        flask.abort(404)
    webhook_url, = row
    token = binascii.hexlify(os.urandom(16)).decode()
    cur.execute('UPDATE rooms SET token = %s WHERE room_id = %s', (token, room_id))
    slack_message(webhook_url, 'token = `{}`'.format(token))
    return flask.jsonify({ 'ok': True })


@contextlib.contextmanager
def auth():
    room_id = flask.request.form['room_id']
    token = flask.request.form['token']

    cur = db().cursor()
    cur.execute('SELECT webhook_url, activated FROM rooms WHERE room_id = %s AND token = %s', (room_id, token))
    row = cur.fetchone()
    if not row:
        flask.abort(403)
    webhook_url, activated = row
    if not activated:
        cur.execute('UPDATE rooms SET activated = TRUE WHERE room_id = %s', (room_id, ))
        slack_message(webhook_url, 'activated')
    yield room_id, webhook_url


@app.route('/room/activate', methods=['POST'])
def post_room_activate():
    with auth() as (room_id, webhook_url):
        return flask.jsonify({ 'ok': True })


@app.route('/room/users', methods=['POST'])
def post_room_users():
    with auth() as (room_id, webhook_url):

        cur = db().cursor()
        cur.execute('SELECT user_id, atcoder_id FROM users WHERE room_id = %s', (room_id, ))
        users = [dict(zip(['user_id', 'atcoder_id'], row)) for row in cur.fetchall()]

        data = {
            'ok': True,
            'users': users,
        }
        return flask.jsonify(data)


@app.route('/room/useradd', methods=['POST'])
def post_room_useradd():
    user_id = flask.request.form['slack_id']
    atcoder_id = flask.request.form['atcoder_id']
    if not isident(user_id) or not isident(atcoder_id):
        flask.abort(400)

    with auth() as (room_id, webhook_url):
        resp = requests.get('https://atcoder.jp/users/{}'.format(atcoder_id))
        if resp.status_code != 200:
            flask.abort(400)

        cur = db().cursor()
        cur.execute('INSERT INTO users (room_id, user_id, atcoder_id) VALUES (%s, %s, %s)', (room_id, user_id, atcoder_id, ))
        slack_message(webhook_url, 'user @{} is added  (AtCoder: `{}`)'.format(user_id, atcoder_id))
        return flask.jsonify({ 'ok': True })


@app.route('/room/userdel', methods=['POST'])
def post_room_userdel():
    user_id = flask.request.form['slack_id']

    with auth() as (room_id, webhook_url):
        cur = db().cursor()
        cur.execute('DELETE FROM users WHERE room_id = %s AND user_id = %s', (room_id, user_id))
        slack_message(webhook_url, 'user @{} is deleted'.format(user_id))
        return flask.jsonify({ 'ok': True })


@app.route('/room/delete', methods=['POST'])
def post_room_delete():
    with auth() as (room_id, webhook_url):
        cur = db().cursor()
        cur.execute('DELETE FROM rooms WHERE room_id = %s', (room_id, ))
        slack_message(webhook_url, 'deleted')
        return flask.jsonify({ 'ok': True })


if __name__ == '__main__':
    app.run(debug=True)
