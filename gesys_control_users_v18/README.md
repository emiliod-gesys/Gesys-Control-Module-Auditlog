# Control (gesys_control_users_v18)

**User activity audit, key action tracking and control dashboards for Odoo 18.**

This module records and monitors key user actions across your Odoo instance for audit, compliance and support. It includes dashboards, statistics and optional automatic purge.

## Features

- **Action log** – Records tracked actions such as validate, post, cancel, export, print, email, import and selected model operations.
- **Change lines** – Optional field-level diff (old/new values) for write operations.
- **Views** – All actions, actions by employee, filters by date and type.
- **Activity dashboard** – Overview of recent user activity.
- **Statistics dashboard** – Charts and aggregates by hour, day, week or month.
- **Reports** – PDF (activity, executive, by user) and Excel export.
- **Rules** – Per-model rules to exclude users or fields from logging (Manager only) for supported tracking flows.
- **Configuration** – Timezone, language (EN/ES), read logging, log mode, retention and automatic purge.

## Requirements

- **Odoo:** 18.0
- **Python:** `xlsxwriter`
- **Dependencies:** `base`, `mail`, `account`, `web`, `sale`, `purchase`

## Installation

1. Put the module in your Odoo addons path.
2. Update the Apps list and install **Control**.
3. Assign users to **Control / User** (view) or **Control / Administrator** (config and rules).

## Configuration

- **Control → Configuration** (Manager): timezone, retention, auto-delete frequency, language, read logging, log mode.
- **Control → Rules**: define which models are tracked and optionally exclude users or fields.

## Security

- **Control / User** – Access to actions, activity and statistics (read-only).
- **Control / Administrator** – Same as User plus configuration and rules.

## License

LGPL-3.

## Author

**Gesys**

- Website: [https://gesysgt.odoo.com](https://gesysgt.odoo.com)

- Contact: emiliodiaz@gesys.gt

## Odoo Store Checklist

For publication on the Odoo App Store:

- **Icon:** Included at `static/description/icon.png` (PNG format).
- **Description:** The store uses `static/description/index.html` (English, no JavaScript; only YouTube/mailto and links to files in `static/description` per Odoo guidelines).
- **Manifest:** Optional fields for the store: `support` (email), `images` (e.g. `['images/main_screenshot.png']`), `live_test_url` (demo instance).
- **Price:** `39.99 USD` (`price`: `39.99`, `currency`: `USD`).
