# Vicuna plugins

The official plugin index for [Vicuna](https://github.com/anslwy/vicuna).
Settings → Plugins → **Explore** reads [`index.json`](index.json) from this
repo, so everything listed here can be installed with one click.

## Submit a plugin

1. Publish your plugin in a public GitHub repo with a `vicuna-plugin.json`
   (on the default branch, or as an asset of the latest release). See the
   samples: [Scratchpad](https://github.com/anslwy/vicuna-plugin-scratchpad)
   (side panel) and [Lagoon](https://github.com/anslwy/vicuna-theme-lagoon)
   (themes).
2. Open a PR here that adds one entry to `plugins` in `index.json`:

   ```json
   {
     "id": "my-plugin",
     "name": "My Plugin",
     "description": "One or two sentences.",
     "author": "your-github-name",
     "source": "you/vicuna-my-plugin",
     "kinds": ["theme"],
     "icon": "https://raw.githubusercontent.com/you/vicuna-my-plugin/main/icon.svg",
     "screenshot": "https://raw.githubusercontent.com/anslwy/vicuna-plugins/main/screenshots/my-plugin.png",
     "tags": ["dark"],
     "minVicuna": "0.0.45"
   }
   ```

   | field | rules |
   |---|---|
   | `id` | lowercase letters, digits, dashes; must equal the manifest's `id` |
   | `name`, `author` | 1–60 characters |
   | `description` | 1–300 characters, plain text |
   | `source` | `owner/repo` on GitHub |
   | `kinds` | `theme`, `panel` and/or `harness`, matching what the manifest provides |
   | `icon`, `screenshot` | optional; https on `raw.githubusercontent.com` or `github.com` only (screenshots can live in this repo's `screenshots/`) |
   | `tags` | optional; up to 8 short strings |
   | `minVicuna` | optional; oldest Vicuna version the plugin works with |

3. CI (`scripts/validate.py`) checks the entry and fetches your manifest.
   Run it locally with `python3 scripts/validate.py`.

Vicuna treats this index as untrusted: entries that break these rules are
skipped, text is shown as plain text, and installs still validate the
plugin's own manifest.

## Harness plugins

A plugin with `harnesses` adds a Work harness: an ACP-speaking CLI that the user installs themselves.
`acp.command` must be a bare program name (no paths), `acp.args` must not contain shell metacharacters, and
Vicuna asks the user to approve the exact command before it runs. `scripts/validate.py` checks the same rules
as Vicuna. [anslwy/vicuna-plugin-muse](https://github.com/anslwy/vicuna-plugin-muse) documents the full manifest
and works as a template.
