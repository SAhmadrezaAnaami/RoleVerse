# RoleVerse Client

The client is a static, no-build-step web application. It uses HTML, CSS, vanilla JavaScript, the Tailwind CDN for utility availability, and local semantic CSS for the RoleVerse design system.

## Run locally

Start the FastAPI service from the repository root:

```powershell
cd backend
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/` in a browser. FastAPI serves the client from the repository's `client/` directory.

## Current preview

The current client uses deterministic sample characters and local replies. It includes:

- Chat and recent conversation navigation
- Character discovery and marketplace previews
- Favorites
- English/Persian switching
- Light/dark theme switching
- Responsive mobile navigation
- Development phone OTP sign-in through `/api/v1/auth`
- Public character discovery and API-backed owner conversations
- Persisted localized greetings and ordered preview messages

The sign-in flow uses an HttpOnly session cookie and never stores the OTP or session token in browser storage. The current assistant response is a deterministic development preview; the provider streaming adapter will replace it in a later section. Do not add a bundler or Node.js dependency unless the product requirements change.
