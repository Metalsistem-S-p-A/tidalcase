# Authentication providers

Tidalcase ships with **local users** out of the box and can be extended with
external providers configured at runtime from **Admin → Auth providers**.

Supported provider types:

- `local` — username + password stored in the Tidalcase database (bcrypt).
- `ldap` — generic LDAP / Active Directory bind.
- `oidc` — any OpenID Connect–compliant identity provider.
- `azure-ad` — Microsoft Entra ID (Azure AD) — a preconfigured OIDC flavour.

Multiple providers can be enabled simultaneously; users pick one at the
login screen.

All providers honour the same Tidalcase RBAC: once a user authenticates,
their permissions come from the **groups** they belong to in Tidalcase, not
from the provider.

## Local

Always available, no configuration needed. The first `admin` user is created
on first start (see [deployment.md](deployment.md#first-start)).

To add users:

1. **Admin → Users → Add user.**
2. Pick a username, set an initial password, assign one or more groups.
3. Tick **Require password change at next login** if you want them to rotate
   it.

Optional TOTP MFA can be enabled per user from **Profile → Security** (the
user does this themselves) or forced for whole groups from **Admin →
Groups → <group> → Require MFA**.

## LDAP / Active Directory

Common fields under **Admin → Auth providers → Add → LDAP**:

| Field           | Example                                       |
| --------------- | --------------------------------------------- |
| Server URI      | `ldaps://dc.example.com:636`                  |
| Bind DN         | `CN=tidalcase,OU=Service Accounts,DC=example,DC=com` |
| Bind password   | (secret)                                      |
| User search base | `OU=Users,DC=example,DC=com`                 |
| User filter     | `(&(objectClass=user)(sAMAccountName={username}))` |
| Attribute: email | `mail`                                       |
| Attribute: display name | `displayName`                         |
| Group search base | `OU=Groups,DC=example,DC=com`               |
| Group filter    | `(&(objectClass=group)(member={user_dn}))`    |

Notes:

- Use `ldaps://` whenever possible. Plain LDAP is supported but not
  recommended.
- The provider only reads from LDAP — it never writes.
- Group mapping (auto-assign Tidalcase groups based on LDAP group membership)
  is set up in **Auth provider → Group mapping**: each entry maps an LDAP
  group DN to a Tidalcase group. Users get every Tidalcase group their LDAP
  groups map to, evaluated at every login.

## OIDC (generic)

For OIDC providers other than Azure AD:

| Field            | Example                                           |
| ---------------- | ------------------------------------------------- |
| Issuer URL       | `https://auth.example.com/realms/main`            |
| Client ID        | `tidalcase`                                       |
| Client secret    | (secret)                                          |
| Redirect URI     | `https://tidalcase.example.com/api/auth/oidc/callback` |
| Scopes           | `openid email profile`                            |
| Username claim   | `preferred_username`                              |
| Email claim      | `email`                                           |
| Groups claim     | `groups` (optional, used for group mapping)       |

The discovery document at `<issuer>/.well-known/openid-configuration` must
be reachable from the backend container.

Register the redirect URI on the IdP side **exactly** as above — with your
real `DOMAIN`.

## Azure AD / Entra ID

Use the **Azure AD** provider type — it's a preset OIDC config that uses
Microsoft's discovery URL.

In the Azure portal:

1. **App registrations → New registration.**
2. Redirect URI: `https://<DOMAIN>/api/auth/oidc/callback` (Web type).
3. **Certificates & secrets → New client secret.** Save the value.
4. **API permissions →** Microsoft Graph → `User.Read`, optionally
   `GroupMember.Read.All` if you want group mapping.

In Tidalcase:

| Field            | Where it comes from                |
| ---------------- | ---------------------------------- |
| Tenant ID        | App registration → Overview        |
| Client ID        | App registration → Overview        |
| Client secret    | What you saved in step 3           |

Group mapping uses the Azure AD group **object IDs** (GUIDs), not display
names.

## MFA

Tidalcase supports **TOTP** (Google Authenticator, 1Password, Authy, …) for
local and OIDC accounts:

- Per-user opt-in: **Profile → Security → Enable TOTP**, scan the QR with
  any TOTP app, save backup codes.
- Per-group enforcement: **Admin → Groups → <group> → Require MFA**. Users
  in the group are forced to enrol on next login.

TOTP doesn't apply to LDAP providers (use your LDAP server's own MFA
integration instead).

## How sessions work

After a successful login, the backend issues a short-lived JWT in an
`HttpOnly` cookie (`auth_request`). The frontend uses it for API calls; the
backend validates the JWT signature against `SECRET_KEY` on every request.

A refresh token (also HttpOnly) lets the frontend rotate the access token
without re-prompting the user. Both tokens have a configurable lifetime in
**Admin → Settings → Session timeout**.

Rotating `SECRET_KEY` invalidates every existing session immediately. That's
the nuclear option if you suspect a token leak.

## Authentik in front of Tidalcase

If you ran `docker compose --profile auth up -d`, the bundled Authentik
talks to its own Postgres database and exposes itself on port 9443. You can
either:

- Configure it as an **OIDC provider** in Tidalcase and let users hit
  Tidalcase directly (cleanest); or
- Put Authentik in front as a **forward-auth proxy** via Traefik — same
  pattern flowcase originally documented. This requires extra Traefik
  middleware labels which are not enabled by default in `docker-compose.yml`.

The OIDC approach is recommended unless you specifically need Authentik to
gate access to other apps too.
