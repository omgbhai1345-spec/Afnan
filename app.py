import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote, urlencode

import requests
from flask import (
    Flask,
    jsonify,
    redirect,
    request,
    send_file,
    session,
    url_for,
    abort,
)
from flask_session import Session
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
SHEETDB_API_URL = os.getenv('SHEETDB_API_URL', 'https://sheetdb.io/api/v1/uipal0hntoejb')
REDIRECT_URI = os.getenv('REDIRECT_URI')
SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_urlsafe(32))

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise RuntimeError('GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in environment variables.')

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config.update(
    SESSION_TYPE='filesystem',
    SESSION_PERMANENT=True,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.getenv('FLASK_ENV', '').lower() == 'production',
)
Session(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

if REDIRECT_URI is None:
    REDIRECT_URI = os.getenv('BASE_URL', 'http://localhost:5000').rstrip('/') + '/oauth2callback'

GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_SCOPE = 'openid email profile'


def _create_csrf_token() -> str:
    token = secrets.token_urlsafe(32)
    session['csrf_token'] = token
    return token


def _verify_csrf_token(token: str) -> bool:
    return token and session.get('csrf_token') == token


def _current_time_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'


def _client_metadata() -> dict:
    ua = request.user_agent
    return {
        'Device': ua.platform or 'unknown',
        'Browser': ua.browser or 'unknown',
        'IP Address': request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown',
    }


def _sheetdb_search_user(email: str):
    url = f"{SHEETDB_API_URL}/search?Gmail={quote(email)}"
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        return None
    data = response.json()
    if isinstance(data, list) and data:
        return data[0]
    return None


def _sheetdb_create_user(user_data: dict) -> bool:
    payload = {'data': [user_data]}
    response = requests.post(SHEETDB_API_URL, json=payload, timeout=10)
    return response.ok


def _sheetdb_update_user(email: str, user_data: dict) -> bool:
    url = f"{SHEETDB_API_URL}/Gmail/{quote(email)}"
    payload = {'data': [user_data]}
    response = requests.put(url, json=payload, timeout=10)
    return response.ok


def _persist_user(user_info: dict) -> dict:
    now = _current_time_iso()
    metadata = _client_metadata()
    existing = _sheetdb_search_user(user_info['email'])
    if existing:
        preserved_registration = existing.get('Registration Time') or existing.get('registration time') or now
        row = {
            'Google User ID': user_info['id'],
            'Full Name': user_info['name'],
            'Gmail': user_info['email'],
            'Profile Photo URL': user_info.get('picture', ''),
            'Last Login': now,
            'Login Time': now,
            'Registration Time': preserved_registration,
            'Device': metadata['Device'],
            'Browser': metadata['Browser'],
            'IP Address': metadata['IP Address'],
            'User Role': 'Student',
            'Account Status': 'Active',
        }
        success = _sheetdb_update_user(user_info['email'], row)
        if not success:
            raise RuntimeError('Failed to update Google Sheet record for existing user.')
        row['Registration Time'] = preserved_registration
        return row

    row = {
        'Google User ID': user_info['id'],
        'Full Name': user_info['name'],
        'Gmail': user_info['email'],
        'Profile Photo URL': user_info.get('picture', ''),
        'Login Time': now,
        'Registration Time': now,
        'Last Login': now,
        'Device': metadata['Device'],
        'Browser': metadata['Browser'],
        'IP Address': metadata['IP Address'],
        'User Role': 'Student',
        'Account Status': 'Active',
    }
    success = _sheetdb_create_user(row)
    if not success:
        raise RuntimeError('Failed to create Google Sheet record for new user.')
    return row


@app.after_request
def set_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


@app.route('/')
def index():
    return send_file(str(BASE_DIR / 'new.html'))


@app.route('/login')
def login():
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'response_type': 'code',
        'scope': GOOGLE_SCOPE,
        'redirect_uri': REDIRECT_URI,
        'state': state,
        'access_type': 'offline',
        'prompt': 'select_account',
    }
    return redirect(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@app.route('/oauth2callback')
def oauth2callback():
    error = request.args.get('error')
    if error:
        return abort(400, f'Google OAuth error: {error}')

    state = request.args.get('state')
    if not state or state != session.get('oauth_state'):
        return abort(400, 'Invalid OAuth state parameter.')

    code = request.args.get('code')
    if not code:
        return abort(400, 'Missing authorization code from Google.')

    token_response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': REDIRECT_URI,
            'grant_type': 'authorization_code',
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=10,
    )
    if token_response.status_code != 200:
        return abort(400, 'Failed to exchange authorization code for tokens.')

    token_data = token_response.json()
    id_token_str = token_data.get('id_token')
    if not id_token_str:
        return abort(400, 'Google did not return an ID token.')

    try:
        id_info = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except ValueError:
        return abort(400, 'Invalid or expired Google ID token.')

    if not id_info.get('email_verified'):
        return abort(403, 'Google email address is not verified.')

    user_info = {
        'id': id_info.get('sub'),
        'email': id_info.get('email'),
        'name': id_info.get('name', ''),
        'picture': id_info.get('picture', ''),
        'email_verified': id_info.get('email_verified', False),
    }

    persisted_user = _persist_user(user_info)

    session.clear()
    session['user'] = {
        'id': persisted_user['Google User ID'],
        'email': persisted_user['Gmail'],
        'name': persisted_user['Full Name'],
        'picture': persisted_user['Profile Photo URL'],
        'email_verified': True,
        'last_login': persisted_user['Last Login'],
        'registered_at': persisted_user['Registration Time'],
        'role': persisted_user['User Role'].lower() if persisted_user.get('User Role') else 'student',
    }
    _create_csrf_token()
    session.permanent = True

    return redirect(url_for('index'))


@app.route('/auth/session')
def auth_session():
    user = session.get('user')
    if not user:
        return jsonify({'logged_in': False}), 401
    return jsonify({
        'logged_in': True,
        'user': user,
        'csrf_token': session.get('csrf_token'),
    })


@app.route('/logout', methods=['POST'])
def logout():
    request_token = request.headers.get('X-CSRF-Token')
    if not _verify_csrf_token(request_token):
        return jsonify({'error': 'Invalid CSRF token.'}), 400
    session.clear()
    return jsonify({'logged_out': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=os.getenv('FLASK_ENV') != 'production')
