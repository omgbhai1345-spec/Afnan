# Google OAuth Authentication for Afnan Portal

This project has been updated to use Google OAuth 2.0 for student authentication. Google Sheets is now used only as a post-login database to store or update student records.

## What changed

- Student login now redirects to Google OAuth 2.0.
- The server verifies the Google ID token and requires `email_verified`.
- Google Sheets is updated only after a successful Google login.
- The sheet is used for storing new users and updating existing users, not for deciding whether a login is allowed.
- Session cookies and CSRF protection are enabled for secure backend flows.

## Files added

- `app.py` — Flask backend that handles OAuth flow, ID token verification, session management, and SheetDB persistence.
- `requirements.txt` — Python package dependencies.
- `.env.example` — example environment variables.

## Setup

1. Create a Google OAuth Client ID in the Google Cloud Console.
   - Authorized redirect URI should be `http://localhost:5000/oauth2callback` for local development.

2. Create a `.env` file in the project directory and set:

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
BASE_URL=http://localhost:5000
REDIRECT_URI=http://localhost:5000/oauth2callback
SECRET_KEY=...
SHEETDB_API_URL=https://sheetdb.io/api/v1/<your-sheetdb-id>
FLASK_ENV=development
```

3. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

4. Run the application:

```powershell
python app.py
```

5. Open `http://localhost:5000` in your browser.

## Security notes

- In production, run behind HTTPS and set `FLASK_ENV=production`.
- Use a strong `SECRET_KEY`.
- For production sessions, replace filesystem session storage with Redis or another persistent session store.

## How it works

   - `/login` starts Google OAuth and uses an authorization code exchange.
   - `/oauth2callback` exchanges the code for tokens and verifies the Google ID token.
- If Google verifies the user and the email is verified, user metadata is persisted to Google Sheets.
- `/auth/session` returns the authenticated user session to the frontend.
- `/logout` clears the session using a CSRF-protected request.
