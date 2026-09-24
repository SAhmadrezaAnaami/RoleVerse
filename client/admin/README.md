# RoleVerse Admin Workspace

The admin workspace is a static, no-build-step page served by FastAPI at `/admin.html` or `/admin/`.

It uses the existing HttpOnly session cookie and server-side admin authorization. Provider API keys, OTP values, session tokens, prompts, and message content are never requested from or stored by this page. Theme and language preferences reuse the existing local preference keys; admin API responses are not cached in browser storage.

The page supports English/Persian, RTL/LTR, light/dark themes, responsive tables, user bans, safe provider/model metadata, usage/cost visibility, settings, and audit events.
