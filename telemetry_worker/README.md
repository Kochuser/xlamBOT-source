# Cloudflare receiver

Managed alternative to the Windows/ngrok receiver. The Python client protocol
is unchanged. Deploy this backend separately; it is not packaged in the PC EXE.

Use the Workers **Free** plan and D1 free allowances. Do not enable paid usage.
Workers request allowances and D1 read/write/storage allowances are separate:
https://developers.cloudflare.com/d1/platform/pricing/ . Quota exhaustion can
temporarily reject reports; the client keeps its bounded queue and retries.

## Deployment

1. `npm ci`, then `npx wrangler login --scopes account:read user:read workers:write workers_scripts:write d1:write`.
2. `npx wrangler d1 create xlambot-errors` and put its database ID into a local
   ignored `wrangler.local.jsonc` copied from `wrangler.jsonc`.
3. `npx wrangler d1 migrations apply xlambot-errors --remote --config wrangler.local.jsonc`.
4. Deploy with `npx wrangler deploy --config wrangler.local.jsonc`.
5. Store optional developer error delivery secrets `ERROR_TELEGRAM_BOT_TOKEN` and `ERROR_TELEGRAM_CHAT_ID` separately from the public command bot. Store `TELEGRAM_BOT_TOKEN` and a random `TELEGRAM_WEBHOOK_SECRET` using Wrangler secrets (stdin, never CLI arguments). Register `/telegram` with Telegram `setWebhook` and the same secret token. Android Plus requires `message`, `callback_query` and `pre_checkout_query` updates. Its fixed-purpose `/internal/plus/configure-webhook` endpoint requires `PLUS_BRIDGE_SECRET`, verifies the bot identity and current webhook, preserves other update types and pending messages, and enables these events without returning credentials. It cannot redirect delivery to another endpoint. The general Plus gateway still forbids `setWebhook`. Existing command menus can be retained; Plus is also reachable through `/start` and `/plus`.
6. Verify `/health`, authenticated reports/statistics, and webhook command replies. Merge source changes before publishing the signed PC update.
7. Disable obsolete Windows/ngrok receiver startup, preserving encrypted settings and databases.

## Privacy and delivery

Error reporting is enabled by default for new preferences; saved opt-outs and unreadable preferences remain disabled. Community statistics are enabled by default, with a visible notice and a separate opt-out control; existing explicit opt-outs are preserved. Error reports stay private in D1: no exception messages, raw logs, source, screenshots or account data. Inspect them through authenticated Cloudflare administration; there is no public report-reading endpoint and no public Telegram error delivery. Sanitized error notifications go only to the developer private chat through the separate `ERROR_TELEGRAM_BOT_TOKEN` and `ERROR_TELEGRAM_CHAT_ID` Worker secrets. Community commands use `TELEGRAM_BOT_TOKEN`; they never receive error details. The error outbox uses a database lease, retries failed delivery with backoff and groups repeats with a ten-minute notification interval.

Statistics uploads contain only installation-salted device IDs and match IDs, times, outcomes and trophy changes. They include historical matches when statistics sharing is enabled. Formula estimates and unknown changes remain separate from observed changes. No brawler names, account tags or device serials are transmitted. Previous anonymous aggregate results remain after opt-out; new uploads stop and presence is cleared. Online expires after 150 seconds without a heartbeat (client interval 60 seconds).

Telegram accepts only authenticated webhook requests. `/online` replies to the requesting chat and topic with separate PC and Android active bot counts. Expired, stopped and paused devices are excluded. Old `/stats`, `/today`, `/hour`, `/alltime`, `/start` and `/help` commands remain compatible aliases, returning the same platform-separated online text, without history/trophy queries. The database claims updates to prevent concurrent/repeated replies; ambiguous network acknowledgement can still cause a duplicate reply. Ordinary messages and error details are never posted or retained by this command handler.

Statistics are self-reported by consenting clients, not a count of downloads or all installations. Old clients cannot report presence. Server-side match IDs prevent retry inflation; credentials bind uploads to their installation. Credentials are randomly generated and stored hashed. Request bodies are limited to 32 KiB, 32 devices and 50 matches per upload. Cloudflare quota exhaustion causes retries without interrupting gameplay. No paid plan is required or enabled.

Daily cleanup removes error groups inactive for 30 days and Telegram update claims older than seven days. Anonymous match totals and device participation are retained for all-time statistics. Worker observability is disabled; Telegram secrets never enter the PC distribution.

## Android Plus Mini App

`/plus` is the phone-first Plus storefront; `/miniapp` retains the PC remote panel. Private `/start`, `/online` and Plus-home replies include a Web App button. The storefront uses the existing signed Telegram identity exchange and HttpOnly session. `/mini/plus/*` verifies the session and Origin before forwarding the server-selected Telegram user to the Plus service. Browser-supplied user/admin IDs are overwritten.

The 1.2 UI shows entitlement, device, manual 50-Star / 30-day renewal, referrals, payment history and support. Trials are removed at the 1.2 cutover; existing paid, VIP and referral access is preserved. Invoice closure in the browser never grants access: the app polls entitlement confirmed by the payment webhook. A missing or old phone blocks purchase before invoice creation. No recurring billing is requested.

Apply receiver migration `0006_event_details.sql` and Plus migration `0003_referrals.sql` before the 1.2 workers. Deploy this receiver first with the community flag disabled, deploy Plus with the new policy, then enable `PLUS_COMMUNITY_ENABLED=true` here. Preserve live secrets, bindings and sales settings. Back up both D1 databases before applying migrations.

Telegram and Mini App access requires channel membership when the community flag is enabled. The verified bot must be an administrator of @xlamModz. Authenticated `getChatMember` checks use the private bridge and a short cache; financial support, checkout and payment/refund events remain available independently. Android gameplay is never gated by channel membership. New users entering through a referral link and confirming membership count once; every five qualified users adds ten days to the inviter's Plus. Reward delivery uses the existing durable outbox. Historical unregistered visitors cannot be reconstructed retroactively.

Online shows fresh active bots separately from installations seen in the previous day. The 150-second expiry and pause exclusion remain unchanged; expired clients are never revived to increase the count. Visible data refreshes every minute with an update time. Users without sharing or on old Android clients may not appear.

Receiver SQL/auth tests, Plus payment tests and local-browser checks cover ownership, consent, invoice reuse, cancellation, forged browser payment callbacks, confirmed payment, support and unlinking. These checks do not charge real Stars.

## Private PC Mini App

Local Settings → Telegram creates a random single-use pairing key valid for ten minutes. PC credentials use Windows user DPAPI. Remote control is off until configured; disconnect blocks commands without stopping gameplay. Each Telegram user can link multiple PCs and sees only their linked PCs. Keep the PC and bot running.

Set the verified owner's numeric `ADMIN_TELEGRAM_USER_ID` in Worker secrets. Public commands are `/online` and `/panel`; expose `/admin` only in the owner's private-chat command scope. The private-chat menu button opens the HTTPS `/miniapp` URL. Apply migration 0003 and the SQLite Durable Object binding before enabling the menu.

Telegram initData uses HMAC verification, a ten-minute freshness window and a private launch restriction. One-hour HttpOnly sessions protect the shell and owner-only admin API. Pairing is atomic; new keys/revocation remove old access. PC views run in an isolated sandbox with separate one-hour grants scoped to one installation. Those grants cannot authenticate admin requests. Pages, APIs and images retain their PC scope, including parallel tabs.

A SQLite Durable Object on the Workers Free plan relays requests over the PC's outbound TLS WebSocket and hibernates when idle. No router ports, inbound local HTTP exposure or paid plan are needed. Allowed device controls, queues, brawler selection, Think/mode controls, calibration, recordings/annotation and statistics reuse protected Flask handlers. Worker and PC independently block general settings, access configuration, updates and shutdown. Deadlines and bounded messages prevent delayed/replayed actions. Export downloads over 32 MiB locally. Screens, history and PC logs are relayed only when the linked owner opens them; the admin journal does not persist them.

Only the verified administrator reads sanitized errors, technical activity and anonymous panel version changes. First observation differs from an actual revision change; repeated heartbeats do not duplicate events. Timestamp/row cursors paginate equal-time records. Raw PC logs belong to each linked owner and are not harvested from other installations. Version observations begin at deployment; old update timestamps cannot be reconstructed. Expired sessions/grants and activity older than 30 days are removed daily. Free-tier quota exhaustion can interrupt remote control while local gameplay continues.

## Verification

`npm test` executes the production queries and migrations against SQLite with
fake Telegram credentials. Also check `npx wrangler deploy --dry-run`, apply local
migrations and exercise registration/events in `npx wrangler dev` before live
deployment. Never use real credentials for automated tests.

Android presence uses the same authenticated `/v1/statistics` protocol with `platform: "android"`, no matches, and a random device ID. Missing platform stays PC for compatibility; existing rows without metadata are also PC. Active clients heartbeat every 60 seconds; Stop and opt-out clear presence, and process loss expires after 150 seconds. Apply migration 0005 before deploying the platform counter. Android app versions through 1.0.8 do not send presence.
