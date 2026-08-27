# Quickstart

Get from a mockup to a pasted Power Apps screen in about five minutes.

## 1. Install the skill

You have two options. They deliver the same skill — pick whichever fits your setup.

### Option A — as a Claude Code plugin (recommended)

```bash
/plugin marketplace add YKUNAKORN/power-app-yaml
/plugin install power-app-yaml@power-app-yaml
```

Claude Code reads the plugin from `.claude-plugin/plugin.json` and loads the skill
from `skills/power-app-yaml/`. Update later with:

```bash
/plugin marketplace update power-app-yaml
```

### Option B — as a plain skill folder

Copy the skill directory into wherever your Claude setup loads skills from:

```bash
git clone https://github.com/YKUNAKORN/power-app-yaml.git
cp -r power-app-yaml/skills/power-app-yaml  <your-skills-directory>/
```

The folder that must land in your skills directory is
**`skills/power-app-yaml/`** (the one containing `SKILL.md`), not the repository
root.

## 2. Give Claude a mockup

Anything visual works:

- An HTML/CSS export from Google Stitch, v0, or Figma
- A screenshot of a UI
- A hand-drawn wireframe photo

Ask, in plain words:

> Convert this to pa.yaml — make it a Power Apps screen.

## 3. Claude produces the `.pa.yaml`

It reads the confirmed-controls catalog, starts from the closest example screen,
decomposes your mockup into controls, and hands back a full file. Anything it is
not sure about is tagged `# UNVERIFIED` and comes with a small isolated
paste-test snippet.

## 4. Paste into Power Apps Studio

1. Open your Canvas app in **Power Apps Studio**.
2. Add a **blank screen**.
3. With the screen selected, use **Paste code** (the tree-view context menu, or
   `Ctrl+V` after copying the whole file).
4. Paste the **entire** file — Studio needs the full `Screens:` wrapper, not a
   fragment.

## 5. Feed results back

If Studio shows an error or warning, paste the exact text back to Claude. It
knows which codes block a paste (`PA1001`, `PA2108`) and which are harmless
version warnings (`PA2105`, `PA2106`) — see [troubleshooting](troubleshooting.md).

If a Studio test confirms a control the catalog did not have, please
[report it](https://github.com/YKUNAKORN/power-app-yaml/issues/new?template=control-report.yml)
so the next person benefits.

## Next steps

- Add another screen: ask Claude to "add a screen to this app" and give it the
  new mockup — it reuses the existing screen names for `Navigate()`.
- Keep your catalog honest: when your Studio confirms or corrects something,
  update your local `skills/power-app-yaml/references/confirmed-controls.md`.
