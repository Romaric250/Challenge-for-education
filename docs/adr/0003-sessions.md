# Sessions

## Status

Accepted

## Decision

Access tokens last 15 minutes and are signed with HS256. They are set as an `HttpOnly` `SameSite=Lax` cookie and also returned in JSON for a mobile client. Refresh tokens last 7 days, are stored only as a SHA-256 hash, and rotate on every use. Reuse of an old refresh token revokes the whole family.

Cookie mutations from a browser must send `X-Requested-With: tutor` and an `Origin` in `CORS_ORIGINS`. A request with `Authorization: Bearer` is treated as an API client and skips that check.

Passwords are hashed with Argon2id, must be at least 10 characters, and are rejected when they match a small denylist or contain the username.

## Consequences

The web app must be served from the same site as the API, or proxy the API, because `SameSite=Lax` cookies are not sent on cross-site `fetch`. Locally, Next.js rewrites `/api` to the API.
