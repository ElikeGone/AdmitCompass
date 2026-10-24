# User accounts (Step 11)

> **On by default.** Set `AC_ENABLE_ACCOUNTS=false` to turn accounts off. When they're off, the auth and account APIs return 404, Sign In / Sign Up are hidden, and saved work stays in the browser.

## What it does
- **Sign up:** name, email, password and confirmation. The email is lower-cased and must be unique. The password must be 10–128 characters.
- **Sign in, sign out, and a session restored on refresh** (`GET /api/auth/me`).
- **Account-linked saved work:**
  - saved programs;
  - the applicant profile (validated `ApplicantProfile`, which by design has no name, contact details or ID numbers);
  - completed roadmap tasks, per analysis.
- **Guests:** everything public still works without an account, and guest data stays in the browser (`localStorage`).
- **Opt-in import:** after signing in, if this browser has saved work that isn't in the account yet, a dialog offers to add it.
  - Import only adds: nothing in the account is replaced or deleted.
  - Duplicates and invalid ids are skipped and counted.
  - The browser copy is left as it is.

## Turning accounts on and off
- **On by default:** Sign In / Sign Up appear in the header, and the account routes work.
- **`AC_ENABLE_ACCOUNTS=false`** (or `0`, `no`, `off`) turns them off: every `/api/auth/*` and `/api/account/*` route returns 404, the header controls are hidden, and saved work stays in the browser.
- **Review build** (`run_review.sh`): accounts use local SQLite in a fresh temporary file (`AC_DB_PATH` points to a `mktemp` directory), created at start-up and not shared with any other run.
- **HTTPS:** when accounts are served over HTTPS behind a TLS-terminating proxy, set `AC_COOKIE_SECURE=1` so the session cookie gets the `Secure` flag. The value must be `1`; `true` is not recognized.

## Setup
No new dependencies are needed. The database is created automatically on first use. To create it explicitly, or to purge expired sessions:

```
.venv\Scripts\python scripts\init_db.py
```

| Setting | Default | Purpose |
|---|---|---|
| `AC_DB_PATH` | `data/app/accounts.sqlite3` (git-ignored) | SQLite file location |
| `AC_COOKIE_SECURE` | off; on automatically when the app itself receives HTTPS | Set to `1` whenever accounts are served over HTTPS through a proxy that terminates TLS. Only the value `1` is recognized; `true` is ignored. |
| `AC_ALLOWED_ORIGINS` | the app's own origin only | Extra comma-separated origins allowed to make state-changing requests |

## Security design
- **Passwords:** hashed with scrypt (Python's `hashlib`; N=2^14, r=8, p=1, 16-byte random salt), stored as `scrypt$N$r$p$salt$hash`. OWASP lists scrypt as an acceptable choice when Argon2id isn't available, and using it avoids a new dependency. Plaintext passwords are never stored or logged.
  - Unknown emails still run a dummy hash, so response timing doesn't reveal which accounts exist.
- **Sessions:**
  - The token is 256 random bits (`secrets.token_urlsafe(32)`), sent only in the `ac_session` cookie: `HttpOnly`, `SameSite=Lax`, `Path=/`, and `Secure` on HTTPS.
  - The database stores only the token's SHA-256.
  - Sessions expire 7 days after creation, or after 24 hours unused.
  - A new token is issued on every sign-in or sign-up, and any previous session from that browser is deleted.
  - Sign-out deletes the server session and clears the cookie.
  - The token is never in `localStorage`.
- **CSRF:**
  - Every state-changing auth or account request must carry an `Origin` (or `Referer`) matching the site.
  - Signed-in writes also need the per-session CSRF token in `X-CSRF-Token`. JavaScript gets it from `/api/auth/me` and keeps it in memory only.
  - No CORS middleware is installed, so there is no credentialed cross-origin access.
- **Rate limiting:** after 5 failed sign-ins for one email within 15 minutes, further attempts are refused with 429; the limit is 20 failures per IP address. The counters are in memory.
- **Authorization:**
  - Every account query is parameterized and filtered by the session's `user_id`.
  - No endpoint takes a user id from the client.
  - Program ids are checked against the catalog, and task and run ids against strict patterns.

## Limitations (read before deploying)
- **Not production-ready.** This needs an independent security review before real users rely on it.
- **No password reset:** there is no email-delivery service, so a forgotten password can't be recovered. The sign-in form says so.
- **No email verification:** an address isn't proven to belong to the person who registered it.
- **HTTPS is required** for real use. Over plain HTTP the cookie isn't `Secure`, and credentials travel unencrypted. Behind a proxy that terminates TLS, set `AC_COOKIE_SECURE=1`.
- **SQLite:** a single file. It needs a persistent disk (many free hosts wipe their filesystem on redeploy) and backups, and it suits one server process only.
- **Rate-limit counters** live in memory: they reset on restart and aren't shared between processes.
- **Profiles are stored as given.** Profiles saved to an account are real applicant data (education, budget, goals). There is no export or delete-account feature yet.
- **Live analyses** are still kept in server memory, not in the account; only the saved demo's progress is account-linked.

# Voice input for Ask AdmitCompass

- **Browser speech recognition only:** the microphone button in the Ask AdmitCompass question box uses the browser's built-in speech recognition (the Web Speech API). AdmitCompass has no transcription server, no speech-to-text provider and no extra API key for voice.
- **Support depends on the browser:** Chrome, Edge and Safari are supported where their speech recognition is available. Firefox may show "Voice input isn’t supported in this browser. Type your question instead."
- **Permission:** the browser asks for microphone access only after the user clicks the microphone button.
- **Nothing is sent automatically:** the transcript is written into the question box so the user can review and edit it. It's sent only when the user presses Send (or Enter), like a typed question.
- **Privacy:**
  - AdmitCompass receives only the transcript the user chooses to send, through the normal Ask AdmitCompass request with its existing safety checks.
  - Audio is not stored by AdmitCompass, and AdmitCompass never receives it.
  - Speech-to-text is done by the browser. Some browsers (Chrome, for example) use their vendor's own online speech service, so voice input isn't guaranteed to work offline.
- **Messages:**
  - network error — "Voice input is temporarily unavailable. Type your question instead.";
  - microphone blocked — "Microphone access is blocked. Allow it in your browser settings, or type your question instead.";
  - unsupported browser — "Voice input isn’t supported in this browser. Type your question instead.";
  - no speech — "I didn’t hear anything. Try again or type your question."
- **When the online speech service fails** (the browser reports a `network` error):
  - **On-device retry:** if the browser supports on-device speech recognition (newer Chrome, feature-detected), AdmitCompass retries on-device automatically when it's installed. If it can be downloaded, AdmitCompass offers a "Download on-device speech" button; the browser downloads a language pack once. After that, dictation runs on the device.
  - **Browser guidance:** browsers known to block the online speech service — Brave, and embedded Electron windows such as an app's built-in preview — get specific guidance: "This browser blocks the online speech service that voice input needs. Open AdmitCompass in Chrome, Edge or Safari, or type your question instead."
  - **Otherwise:** the network message above is shown.
- **Typing always works:** the text box and Enter-to-send are unchanged.

## Voice input limitations
- **Successful dictation with a physical microphone was not tested in this environment.** Dictation, editing, stopping and the unsupported state were tested with a simulated speech API; the blocked-microphone state was tested with a real browser speech API that had no microphone access.
- **Browser support varies;** recognition quality and language handling depend on the browser.
