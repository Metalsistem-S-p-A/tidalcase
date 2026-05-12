# Storage providers

Tidalcase can mount remote storage into tide sessions so a user's files
follow them across launches. Under the hood every storage provider is an
[rclone](https://rclone.org/) remote, so anything rclone speaks works:
S3, MinIO, Azure Blob, Google Drive, SFTP, WebDAV, SMB, local paths, …

Storage is configured at runtime from **Admin → Storage**.

## Concepts

- **Storage provider** — a configured rclone remote (S3 bucket, SMB share,
  etc.).
- **Mount** — a binding of a storage provider into a tide at a specific
  in-container path. A tide can have multiple mounts; a user can have
  per-user prefixes evaluated at launch.

## Adding a provider

1. **Admin → Storage → Add provider.**
2. Pick a backend type (these mirror rclone's backends).
3. Fill in the credentials/config — they're stored encrypted in the
   Tidalcase DB (encryption key derived from `SECRET_KEY`).
4. Click **Test** to verify the credentials before saving.

### Example: S3

| Field           | Example                                |
| --------------- | -------------------------------------- |
| Provider name   | `team-bucket`                          |
| Backend         | `s3`                                   |
| Endpoint        | `https://s3.eu-west-1.amazonaws.com`   |
| Access key ID   | `AKIA…`                                |
| Secret access key | (secret)                             |
| Bucket          | `tidalcase-userdata`                   |
| Region          | `eu-west-1`                            |

### Example: SMB

| Field        | Example                       |
| ------------ | ----------------------------- |
| Host         | `files.example.com`           |
| Share        | `home`                        |
| Domain       | `EXAMPLE`                     |
| Username     | (per-user — see below)        |
| Password     | (per-user — see below)        |

## Mounting into a tide

In **Admin → Tides → <tide> → Mounts → Add**:

| Field         | Notes                                                       |
| ------------- | ----------------------------------------------------------- |
| Provider      | One of the configured storage providers.                    |
| Source path   | Path inside the remote. Supports `{username}` and `{user_id}` placeholders. |
| Mount point   | Path inside the tide container (e.g. `/home/kasm-user/data`). |
| Mode          | `rw` or `ro`.                                               |

When the tide is launched, the agent calls rclone with the provider's
config, mounts the remote (via `rclone mount` or a sidecar, depending on
backend), and exposes it at the chosen path inside the container.

### Per-user paths

The `{username}` and `{user_id}` placeholders are substituted at launch
time. Common pattern:

| Source path                              | Result for user `alice`           |
| ---------------------------------------- | --------------------------------- |
| `home/{username}`                        | `home/alice`                      |
| `users/{user_id}/work`                   | `users/c0ffee.../work`            |

This is the recommended way to give every user their own private directory
without creating one provider per user.

### Per-user credentials

For backends where each user has their own credentials (SMB with personal
home shares, for instance), leave the username/password fields empty on the
provider and tick **Use user's session credentials**. Tidalcase will then
pass through the credentials the user typed at login (only available for
LDAP and local auth providers).

## Security considerations

- **Credentials at rest.** Provider configs are encrypted with a key derived
  from `SECRET_KEY`. Rotating `SECRET_KEY` will make existing storage
  configs unreadable — re-enter them, or migrate the secret yourself before
  rotating.
- **Credentials in transit.** rclone respects each backend's TLS settings;
  always prefer HTTPS/SMB-3 with encryption / SFTP over plain protocols.
- **Mount surface.** Inside a tide session the user has shell access to the
  mount. Mount only directories you're comfortable that user being able to
  read/write at the OS level.
- **Logs.** rclone is configured to log to the agent's stdout. Failed
  mounts and auth errors show up in `docker compose --profile agent logs
  tidalcase-agent`.

## Listing what's mounted

For a running session, **Admin → Tides → Sessions → <session> → Mounts**
shows the active mounts and their state. The same information is exposed on
the agent at `/api/agent/instances/<id>/mounts` (JWT-authenticated).
