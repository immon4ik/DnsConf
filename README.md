Languages: [**English**](README.md) | [**Русский**](README.ru.md)

# DNS Block&Redirect Configurer
**Allows to set Redirect and Block rules to your Cloudflare and NextDNS accounts.**

**Supports multiple accounts in a single pipeline** -- deploy to several NextDNS profiles and/or Cloudflare accounts at once using GitHub Environments.

**Ready-to-run via GitHub Actions.** [Video guide](#step-by-step-video-guide-redirect-for-nextdns)

[General comparison: Cloudflare vs NextDNS](#cloudflare-vs-nextdns)

[Setup credentials: Cloudflare](#cloudflare-credentials-setup)

[Setup credentials: NextDNS](#nextdns-credentials-setup)

[Setup profile](#setup-profile)

[Setup data sources](#setup-data-sources)

[GitHub Actions](#github-actions-setup)

[Multi-account setup](#multi-account-setup)

## Cloudflare vs NextDNS

Both providers have free plans, but there are some limitations

### Cloudflare limitations
+ 100 000 DNS requests per day
+ Ipv4 DNS requests are restricted by the only one IP. But you are free to use other methods: DoH, DoT, Ipv6
### NextDNS limitations
+ 300 000 DNS requests per month (still more than enough for personal use)
+ Slow API speed is restricted by 60 requests per minute. Takes significantly more time for script to save settings

### Cloudflare credentials setup
1) After signing up into a **Cloudflare**, navigate to _Zero Trust_ tab and create an account.
- Free Plan has decent limits, so just choose it.
- Skip providing payment method step by choosing _Cancel and exit_ (top right corner)
- Go back to _Zero Trust_ tab

2) Create a **Cloudflare API token**, from https://dash.cloudflare.com/profile/api-tokens

with 2 permissions:

    Account.Zero Trust : Edit

    Account.Account Firewall Access Rules : Edit

Set API token to **environment variable** `AUTH_SECRET`

3) Get your **Account ID** from : https://dash.cloudflare.com/?to=/:account/workers

Set **Account ID** to **environment variable** `CLIENT_ID`

### NextDNS credentials setup
1) Generate **API KEY**, from https://my.nextdns.io/account and set as **environment variable** `AUTH_SECRET`

2) Click on **NextDNS** logo. On the opened page, copy ID from Endpoints section.
   Set it as **environment variable** `CLIENT_ID`


## Setup profile
Set **environment variable** `DNS` with DNS provider name (**Cloudflare** or **NextDNS**)

## Setup data sources
Each data source must be a link to a hosts file, e.g. https://raw.githubusercontent.com/Internet-Helper/GeoHideDNS/refs/heads/main/hosts/hosts

You can provide multiple sources split by coma:
https://first.com/hosts,https://second.com/hosts

The workflow can also build a local merged hosts source from these upstreams before running the JAR:

+ `https://dns.geohide.ru:8443`
+ `https://info.dns.malw.link/hosts`
+ `https://iplist.opencck.org/ru`
+ `https://freedom.mafioznik.xyz/file/hosts`

To enable custom local hosts generation for a GitHub Environment, set:

+ `CUSTOM_HOSTS_ENABLED=true`
+ `PMS_IP=<your pms ip>`
+ `AMS_IP=<your ams ip>`
+ `CUSTOM_HOSTS_OVERRIDES_PATH=config/custom-hosts-overrides.json` (optional)
+ `MALW_LINK_BLOCK_LIMIT=<number>` (optional, defaults to `0`)

When `CUSTOM_HOSTS_ENABLED=false` or empty, the workflow uses `BLOCK` and `REDIRECT` exactly as provided in the environment.

When `CUSTOM_HOSTS_ENABLED=true`, the workflow:

+ builds `artefacts/<environment>.hosts` from the 4 upstream sources above
+ builds `artefacts/<environment>.custom.hosts`
+ preserves all block entries as block entries
+ replaces all redirect IPs with either `PMS_IP` or `AMS_IP`
+ overrides both `BLOCK` and `REDIRECT` so DnsConf reads only that local `file://...custom.hosts`

By default `MALW_LINK_BLOCK_LIMIT=0`, so the block portion of `https://info.dns.malw.link/hosts` is fully disabled during merged hosts generation:

+ this source is by far the largest block contributor and adds tens of thousands of entries
+ leaving it untrimmed makes the final `hosts` file much larger and creates unnecessary Cloudflare / pipeline load
+ the redirect portion of that source is still preserved

If you want to bring back part of its block entries, set `MALW_LINK_BLOCK_LIMIT` explicitly. Then:

+ only block entries from that source are capped
+ redirect entries from that source are preserved
+ the other upstream sources are left untouched

If `CUSTOM_HOSTS_OVERRIDES_PATH` is set, the generator applies `force_nodes` from JSON first (`hostname -> pms|ams`) and uses deterministic hostname-hash split only as the fallback.

Overrides example:

```json
{
  "force_nodes": {
    "instagram.com": "ams",
    "www.instagram.com": "ams"
  }
}
```

### 1) Setup Redirects
Set sources to **environment variable** `REDIRECT`

Script will parse sources, filtering out redirects to `0.0.0.0` and `127.0.0.1`

Thus, parsing lines:

    0.0.0.0 domain.to.block
    1.2.3.4 domain.to.redirect
    127.0.0.1 another.to.block

will keep only `1.2.3.4 domain.to.redirect` for the further redirect processing.


+ Redirect priority follows sources order. If domain appears more than one time, the first only IP will be applied.


### 2) Setup Blocklist
Set sources to **environment variable** `BLOCK`

Script will parse sources, keeping only redirects to `0.0.0.0` and `127.0.0.1`.

Thus, parsing lines

    0.0.0.0 domain.to.block
    1.2.3.4 domain.to.redirect
    127.0.0.1 another.to.block

will keep only `domain.to.block` and `another.to.block` for the further block processing.

+ You may want to provide the same source for both `BLOCK` and `REDIRECT` for **Cloudflare**.
+ For **NextDNS**, the best option might be to set `REDIRECT` only, and then manually choose any blocklists at the _Privacy_ tab.

## Script Behaviour
### Cloudflare
Previously generated data will be removed. Script recognizes old data by marks:


+ Name prefix for List: **_Blocked websites by script_** and **_Override websites by script_**
+ Name prefix for Rule: **_Rules set by script_**
+ Different **_Session id_**. **_Session id_** is stored in a description field.


After removing old data, new lists and rules will be generated and applied.

If you want to clear **Cloudflare** block/redirect settings, launch the script without providing sources in related **environment variables**. E.g. providing no value for **environment variable** `BLOCK` will cause removing old related data: lists and rules used to setup blocks.

### NextDNS

For `REDIRECT`:
+ Existing domain will be updated if redirect IP has changed
+ If new domains are provided, they will be added
+ The rest redirect settings are kept untouched

For `BLOCK`:
+ If new domains are provided, they will be added
+ The rest block settings are kept untouched

Previously generated data is removed **ONLY** when both `BLOCK` and `REDIRECT` sources were not provided.

## GitHub Actions setup

#### Step-by-step video guide: [REDIRECT for NextDNS](https://www.youtube.com/watch?v=vbAXM_xAL5I)

#### Steps (single account)

1) Fork repository
2) Go _Settings_ => _Environments_
3) Create _New environment_ with name `DNS_MAIN`
4) Provide `AUTH_SECRET` and `CLIENT_ID` to **Environment secrets**
5) Provide `DNS`,`REDIRECT` and `BLOCK` to **Environment variables**

+ The action will be launched every day at **01:30 UTC**. To set another time, change cron at `.github/workflows/github_action.yml`
+ You can run the action manually via `Run workflow` button: switch to _Actions_ tab and choose workflow named **DNS Block&Redirect Configurer cron task**

---

## Multi-account setup

The workflow supports deploying to **multiple DNS accounts** (NextDNS and/or Cloudflare) in a single pipeline run. Each account is configured as a separate **GitHub Environment** with its own secrets and variables.

### How it works

The pipeline consists of two jobs:

1. **`build`** -- builds the JAR artifact once
2. **`deploy`** -- runs in parallel for each environment listed in the `matrix.environment` array. Each matrix entry uses its own GitHub Environment, which provides isolated secrets and variables.

### Step-by-step guide

#### 1) Create GitHub Environments

Go to your repository _Settings_ => _Environments_ and create an environment for each DNS account. Recommended naming convention:

| Environment name | Description |
|---|---|
| `DNS_MAIN` | Primary DNS profile (e.g. home network) |
| `DNS_TV` | Smart TV profile |
| `DNS_PS5` | PlayStation 5 profile |
| `DNS_WORK` | Work devices profile |

You can use any names you like -- just make sure they match the workflow matrix.

#### 2) Configure each environment

For **each** environment, set the following:

**Environment secrets** (encrypted, not visible in logs):

| Secret | Value |
|---|---|
| `AUTH_SECRET` | API token (Cloudflare) or API key (NextDNS) for this account |
| `CLIENT_ID` | Account ID (Cloudflare) or Profile ID (NextDNS) for this account |

**Environment variables** (plain text):

| Variable | Value |
|---|---|
| `DNS` | `Cloudflare` or `NextDNS` |
| `BLOCK` | Comma-separated URLs to hosts files for blocklists (optional) |
| `REDIRECT` | Comma-separated URLs to hosts files for redirects (optional) |
| `CUSTOM_HOSTS_ENABLED` | `true` to ignore external `BLOCK` / `REDIRECT` sources and use a locally built custom hosts file instead (optional) |
| `PMS_IP` | Replacement IP for part of redirect domains in custom hosts mode |
| `AMS_IP` | Replacement IP for the rest of redirect domains in custom hosts mode |

Each environment is completely independent -- you can mix Cloudflare and NextDNS accounts, use different block/redirect sources for each, etc.

#### 3) Update the workflow matrix

Edit `.github/workflows/github_action.yml` and list your environments in the `matrix.environment` array:

```yaml
strategy:
  fail-fast: false
  matrix:
    environment:
      - DNS_MAIN
      - DNS_TV
      - DNS_PS5
```

#### Example: 3 accounts with different providers

| Environment | DNS | Description |
|---|---|---|
| `DNS_MAIN` | NextDNS | Home network, block + redirect |
| `DNS_TV` | NextDNS | Smart TV, redirect only |
| `DNS_PS5` | Cloudflare | PS5, block + redirect |

Each environment has its own `CLIENT_ID`, `AUTH_SECRET`, `DNS`, `BLOCK`, `REDIRECT` values. The pipeline builds the JAR once, then deploys to all three accounts in parallel with `fail-fast: false` -- if one account fails, the others will still be processed.
