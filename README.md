# NMSii — the No Man's Sky Items Interface

The numbers No Man's Sky doesn't show you, for the two lookups you actually
make while playing: *what does this refine into*, and *how do I get that from
what I'm carrying*. Then the rest: which dish buffs what, where every item
belongs in storage, every route to nanites, and every portal address drawn in
glyphs. For players who want the real figures rather than a wiki's memory of
them.

Every number comes from the game's own recipe table — 361 refining and 1,323
cooking recipes as of Cosmos 7.06 — extracted from the game files, not from a
wiki transcription. It grew out of a set of
written guides (the Suika Box notes); `20.refiner-recipes.md` is the prose
version of what this app queries.

It is one dataset with several ways in: a website, a terminal app, an MCP
server for AI assistants, and plain markdown. Plus a printable **cheat sheet**
of the recipes worth memorising.

## Pick your way in

| | |
| --- | --- |
| 🌐 **Web** | **[nmsii.dlu.one](https://nmsii.dlu.one)** — nothing to install, works on a phone next to the game. [On the web](#on-the-web) |
| ⌨️ **Terminal** | `uv run nms` in a checkout, or `mise run tui`: the same screens with vim keys and a command palette. [In the terminal](#in-the-terminal) |
| 📦 **Container** | `podman compose run --rm tui` for the app, `podman compose up site` for the site offline. [In a container](#in-a-container) |
| 🤖 **AI / MCP** | `nms mcp`, registered by `mise run mcp:install-claude` (or `install-codex`, `-pi`, `-opencode`, `-goose`). [For AI assistants](#for-ai-assistants-mcp) |
| 📝 **Markdown** | [`llms.txt`](https://nmsii.dlu.one/llms.txt), `llms-full.txt` and `md/`, one page per item. [As markdown](#as-markdown-for-bots-and-ai) |
| 🖨️ **Print** | the cheat sheet, [Latte for paper](https://nmsii.dlu.one/pdf/nms-cheatsheet.pdf) and [Mocha for screens](https://nmsii.dlu.one/pdf/nms-cheatsheet-dark.pdf). [The cheat sheet](#the-cheat-sheet) |

![the recipe list](docs/img/recipes.svg)

---

## On the web

The site is a static version of the same screens — recipes, chain planner,
nanites, cooking, multi-tools, portal addresses with the glyphs drawn, storage,
inventory — for a phone next to the game or anyone without a terminal. No
server, no Python at runtime: `scripts/build_web.py` runs the same modules the
TUI uses and exports their answers into `web/data.json` (about 75 KB gzipped),
and the page only searches, sorts and draws. The chain tree walk, the inventory
matching and the portal arithmetic are the only logic redone in JavaScript
(`site/src/lib/core.js`), and `tests/test_web.py` runs them under node against
the Python so the two cannot drift.

The page is [Svelte 5](https://svelte.dev) built by [Vite](https://vite.dev),
with no router or UI library on top: one component per screen in
`site/src/views/`, the shared pieces (the list with its vim keys, the glyph
strip, the header, the search palette) in `site/src/components/`, and each
component's own CSS beside it. `web/` holds what is served as it is — fonts,
favicons, and everything the export writes — and the build copies it into
`dist/` next to the bundle. Links keep the `#/recipes?item=…` shape they have
always had, and what the browser remembers stays under the same `nms-items:`
keys.

It needs node, which `mise install` sets up at the version `mise.toml` pins
(any node 22.12 or newer works too); `package-lock.json` pins the rest.

```fish
mise run web:dev    # export, then a live-reloading dev server on localhost:8790
mise run site       # export, build dist/, and serve it on localhost:8791
mise run web:check  # svelte-check over the components
```

It is live at **[nmsii.dlu.one](https://nmsii.dlu.one)**.
`.github/workflows/pages.yml` runs the tests, exports the data, builds the
site and publishes `dist/` to GitHub Pages on every push to `main`; the
cheat-sheet PDFs are published with it. The custom domain is a repo setting, not a `CNAME` file --
an Actions deploy ignores one -- so `scripts/pages.py` manages it through `gh`
(`mise run pages:setup`, `pages:https`, `pages:status`). DNS is a Cloudflare
`CNAME` record `nms → rdlu.github.io`, DNS only, so GitHub can issue the
certificate. `main` only moves through a pull request whose required `check`
passed; `mise run deploy <pr>` is the whole release: wait for that PR to be
green, merge it on GitHub, fast-forward the local `main`, and watch Pages.

It wears the same skin as the dotfiles and plugii sites: iA Writer Duo for
text, 0xProto for code, numbers and navigation (both self-hosted in
`web/fonts/` with their OFL licenses), square corners and `┌─ Title ───` pane
headings. The accent is the game's HUD gold, with Dracula's colours kept for
what carries meaning; neutral greys in the dark, a warmed Alucard in the light,
and a Light / Dark / System menu that follows the OS by default.

What lives in the browser stays there: the inventory and any portal addresses
you save are kept in `localStorage`. *Export mine* on the portals page downloads
the saved addresses in `data/locations.json`'s shape, to merge into the file.

---

## In the terminal

`nms` is where it started: a [Textual](https://textual.textualize.io) TUI with
the same screens as the site, plus vim keys, a command palette, themes, and
saving portal addresses to `data/locations.json`. It works offline once
installed. The app needs Python 3.11+ and Textual (plus the MCP SDK, for `nms mcp`), and
any terminal with 256 colours. Two ways to run it from a checkout; the
container route below needs neither.

**uv**, which fetches Python itself:

```fish
git clone https://github.com/rdlu/nms-items-interface; cd nms-items-interface
uv run nms
```

**mise**, to work on it:

```fish
mise install        # uv + typst + node
mise run setup      # fonts for the PDF, potrace for the glyphs (paru)
mise run sync       # python deps
mise run tui        # go
```

## In a container

**podman or docker**, nothing else on the machine:

```fish
git clone https://github.com/rdlu/nms-items-interface; cd nms-items-interface
podman compose run --rm tui     # the TUI, in this terminal
podman compose up site          # the web version on http://localhost:8001
podman compose build            # after a git pull
```

The inventory is kept in a named volume, and `data/locations.json` is mounted
from the checkout, so addresses saved in the container are the ones a pull
request would share. `docker compose` reads the same `compose.yaml`.

---

## For AI assistants (MCP)

Ask a chat assistant how to make Antimatter and it answers from whatever wiki
text it remembers, from whichever patch. `nms mcp` serves NMSii's own answers
over the [Model Context Protocol](https://modelcontextprotocol.io) instead, on
stdio, so an assistant can look them up: the same `Book`, chain planner,
gettable scores, storage rules, dishes and portal arithmetic the TUI and the
site use, computed by the same code. It is read-only: it never touches your
inventory or `data/locations.json`.

**Tools.** Every one takes item names or game IDs (`"Chromatic Metal"` or
`STELLAR2`); a name that matches several items comes back as an error listing
them, rather than a guess.

| Tool | Answers |
| --- | --- |
| `search_items(query)` | items by name or ID, tolerating partial words and typos |
| `item_info(item)` | value, category, description, storage home, buff, how gettable it is, and the recipes that make it and use it |
| `search_recipes(query, domain, sort, item, role)` | the recipe table filtered and sorted as on the main screen: multiplier, fastest, output/hour, profit, gettable, name |
| `plan_chain(item, qty, tier, allow_cooking)` | the cheapest tree from a source tier (0, 1, 2), the raw materials to gather or find, total machine time |
| `nanite_routes()` | every route to nanites, best nanites/hour first |
| `cooking_by_buff(buff?)` | dishes per stat boosted, strongest first, with their quickest recipe |
| `where_to_store(item)` | its home in the storage layout, or sell / junk / use it, and why |
| `craftable_from(inventory)` | given `{"Carbon": 200, "Oxygen": 50}`: what you can make now, and what you are one ingredient short of |
| `convert_portal_address(text, planet?)` | portal code ↔ galactic address, glyph names in dialling order, voxel position |
| `saved_locations(kind?, query?, origin?)` | the addresses in `data/locations.json`, with both forms and the glyphs |

**Resources:** `nmsii://source` (which game build the data was extracted
from), `nmsii://guide/{page}` (the site's markdown pages: `guide`, `recipes`,
`nanites`, `cooking`, `multitools`, `storage`, `portals`) and
`nmsii://items/{ID}` (one item's page). **Prompt:** `plan_refining_chain`.

**Quick setup**, from the checkout:

```fish
mise run mcp:install-claude                  # Claude Code, user scope
mise run mcp:install-codex                   # OpenAI's Codex CLI
mise run mcp:config                          # the JSON for anything else
```

Each install task registers `uv run --directory <this checkout> nms mcp`;
running it again replaces the entry rather than adding a second.
`--container` registers the podman route below instead, `--dry-run` prints the
commands (or the config diff) and changes nothing, and
`mcp:install-claude --scope user|project|local` picks where Claude Code keeps
it. `mise run mcp:uninstall claude` (or `codex`, ..., `all`) takes it out again.

| Client | Task | How it registers |
| --- | --- | --- |
| Claude Code | `mcp:install-claude` | `claude mcp add` |
| Codex | `mcp:install-codex` | `codex mcp add` |
| pi ([pi.dev](https://pi.dev)) | `mcp:install-pi` | `pi mcp add` |
| opencode | `mcp:install-opencode` | the `mcp.nmsii` entry in `~/.config/opencode/opencode.json` |
| goose | `mcp:install-goose` | the `extensions.nmsii` entry in `~/.config/goose/config.yaml` |

opencode and goose have no command that adds a server without prompting, so
their files are edited directly: backed up first (`*.bak-<time>`), and only the
nmsii entry is touched. A commented `opencode.jsonc` is refused rather than
rewritten, with the entry printed to paste in by hand. Each task fails with a
plain message when its client is not installed.

**By hand**, the same thing. Claude Code:

```fish
claude mcp add nmsii -- uv run --directory /path/to/nms-items-interface nms mcp
```

**Claude Desktop, and other clients** that take a JSON config
(`claude_desktop_config.json`, `.mcp.json`, Cursor, and so on);
`mise run mcp:config` prints this with the path filled in:

```json
{
  "mcpServers": {
    "nmsii": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/nms-items-interface", "nms", "mcp"]
    }
  }
}
```

**In a container**, with nothing but podman: `-T` turns off the tty the TUI
needs, so stdin and stdout are a plain pipe.

```fish
claude mcp add nmsii -- podman compose -f /path/to/nms-items-interface/compose.yaml run --rm -T tui nms mcp
```

or `mise run mcp:config --container` for the JSON. Build the image once first
(`mise run box:build`), so the first connection does not wait on it.
`compose.yaml` sets `x-podman: in_pod: false` for this route: otherwise
podman-compose creates a pod on the first `run` and prints its ID on stdout,
into the JSON-RPC stream, and that first connection fails.

`mise run mcp:inspect` opens the server in the
[MCP Inspector](https://github.com/modelcontextprotocol/inspector) to try the
tools by hand (`npx` fetches it; needs node). `mise run test:mcp` checks every
tool against the module it wraps, then the server in-process and as `nms mcp`
over a real pipe, and the install tasks against stand-in clients.

### As markdown, for bots and AI

The site is a JavaScript app, so a crawler or a language model that does not
run it would see an empty shell. The same export writes everything it shows as
plain files, from the very bundle that becomes `data.json`, so the two cannot
disagree:

| | |
| --- | --- |
| [`llms.txt`](https://nmsii.dlu.one/llms.txt) | the [llms.txt](https://llmstxt.org) index: what NMSii is, where the data comes from and how old it is, and a link to each page below |
| `md/*.md` | one page per section — recipes, nanites, cooking, multi-tools, storage, portals — and `guide.md`, what the columns mean and how the chain planner chooses |
| `md/items/<ID>.md` | one page per item (1,447): value, storage home, buff, every recipe making and using it, and its cheapest chain from Tier 0. `md/items/index.md` lists them by category |
| `llms-full.txt` | the section pages and the item index in one file (~460 KB); the item pages stay out, since they are the recipe table again, cut per item |
| `data.schema.json` | JSON Schema for `data.json` — hand-written, checked against the export by the tests |
| `sitemap.xml`, `robots.txt` | so crawlers find all of it |

The chain on each item page is core.js's tree walk redone in Python over the
same exported `via` maps; `tests/test_markdown.py` holds it to both
`graph.plan` and the JS. `mise run web:md` rebuilds only these and prints their
sizes.

Every page's footer says so too: *AI friendly* links that page's markdown twin
(an item's own page from its recipes or chain view), llms.txt and the item index,
and the head's `<link rel="alternate" type="text/markdown">` follows it.

An assistant that can run tools gets more than these files from the
[MCP server](#for-ai-assistants-mcp): the chain planner for any quantity and
tier, and the inventory matching, neither of which a static page can do.

---

## What's inside

| | |
| --- | --- |
| ⌨️ **`nms`** | The TUI: fuzzy search, reverse lookup, chain planning, inventory. `mise run tui` |
| 🖨️ **Cheat sheet** | Three-page landscape A4 ([Typst](https://typst.app)) — the money engine, the nanite ladder, the kitchen. Catppuccin **Latte** for print and **Mocha** for screens. `mise run pdf:build` |
| 🧮 **Recipe graph** | Chain planner that answers "cheapest way to N of X from things I can pick up" — the same graph walk that produced the Tier 0/1/2 lists in the notes |
| 💠 **Nanite ladder** | Every route to nanites ranked by nanites/hour, with how gettable each input is and where it drops |
| 🍳 **Cooking buffs** | What each dish does when you eat it, per stat, with what it sells for |
| 🔫 **Multi-tools** | The 8 types compared, the 5 weapons measured, and how to get the free S-class ones |
| 🌀 **Portal addresses** | Glyphs ↔ galactic coordinates, offline, plus the addresses from the guides — where the good tools and Exotics are |
| 🗄️ **Where does it go?** | Every item's home in the storage guide's layout — one of the ten Storage Containers, the Nutrient Processor, Cold Storage — or *sell*, *junk*, *use it now*. Type a home ("sell", "cold") to list everything that goes there |
| 📦 **Inventory** | Type what you're carrying; see what refines right now and what you're one ingredient short of |
| 🤖 **`nms mcp`** | The same answers for AI assistants, as an [MCP](https://modelcontextprotocol.io) server — see [For AI assistants](#for-ai-assistants-mcp) |

### Keys

`Ctrl+P` opens the **command palette**, which lists every mode the app has by
name and marks the one you are in:

```
● Recipes: Refining          ● Sort: multiplier        Nanite ladder
· Recipes: Cooking           · Sort: fastest           Portal addresses
· Recipes: All recipes       · Sort: units profit      Inventory
```

Type `profit` and press Enter to sort by profit; `shared` to filter saved
addresses to the ones other people found. Cycle keys are faster once you know
the order and opaque until you do — pressing `s` four times reaches "units
profit", but nothing on screen ever said that was an option. The palette is
also what lets the footer group its keys: nothing is hidden by being left out
of the bar.

**Themes.** The palette's *Theme* entry recolours the whole app, and the
choice is remembered. The default, `dracula-clear`, is Dracula's accents with
no background at all: your terminal's own shows through, transparency
included. `dracula-neutral` is the same accents on solid greys, because stock
Dracula's `#282A36` reads as blue next to a black terminal. Every Textual
built-in works too.

Vim motions work in every table, tree and scrollable pane:

| | |
| --- | --- |
| `j` `k` | down / up · `h` `l` pan a wide table sideways |
| `g g` `G` | top / bottom · `ctrl+d` `ctrl+u` half page |
| `/` | search — **insert mode**: type freely, `Esc` or `Enter` returns to normal mode |
| `Esc` | in normal mode, clears the search and any filter |

Then the actions:

| | |
| --- | --- |
| `f` `s` | cycle domain (refining / cooking / all) and sort — or pick either by name from `Ctrl+P` |
| `p` `r` | recipes that **produce** the highlighted item / that **consume** it |
| `Enter` | pivot to everything touching that item · `Backspace` clears the filter |
| `c` | **chain plan** it — inside: `t` source tier, `n` quantity, `C` allow cooking |
| `n` | the **nanite ladder** — every route to nanites, ranked |
| `e` | **cooking effects** — what each dish does when eaten |
| `m` | **multi-tools** — types, weapons, getting one, tips |
| `P` | **portal addresses** — convert glyphs, and the places worth going |
| `a` `i` | add to inventory / open the inventory screen (`/` opens its add field) |
| `w` | **where does it go?** — the storage container for an item, or whether to sell or junk it |
| `d` | show/hide the detail pane — it hides itself below 100 columns |
| `?` | full help |
| `ctrl+p` | command palette — every mode by name |

### Reading the columns

- **Mult** — units out per unit in. `x6 loop` means the recipe feeds itself:
  `1 Chlorine + 2 Oxygen → 6 Chlorine` multiplies the seed six times, which is
  the only kind of recipe that grows a stack out of nothing.
- **Time** — one batch, from the game files. The in-game display is often wrong.
- **Machine** — Portable/Personal (1 input), Medium (2), Large (3).
- **Rate / Profit** — units per hour with one machine kept fed, and the
  base-value difference across one batch. Profit is in units and says nothing
  about nanites; those get their own screen.
- **Gettable** — how reachable the hardest ingredient is. `T0/T1/T2 +n` means
  refinable from surface materials / asteroids / an atmosphere harvester, `n`
  refining steps away. `needs seed` means refinable but wanting a material none
  of those tiers contain — a stellar metal, typically, of which you need two
  units ever. `loot (...)` means no recipe makes it.

### The chain planner

Pick any item, press `c`, and it works backwards to a source set — by default
the five things you can pick up on any planet (Oxygen, Carbon, Ferrite Dust,
Di-hydrogen, Sodium), `t` widens that to asteroids and then an atmosphere
harvester. The cost it minimises is **refiner-seconds per unit**, so the plan is
the one that ties up a machine for the least time, not merely the shortest one.

![a production chain](docs/img/chain.svg)

If nothing reaches the target it says so and lists what the item *is* made
from — that is how you find out something has to be looted rather than refined.

### Nanites

Nanites are the second currency, and a units column is actively misleading
about them: one Salvaged Data is ~51,000 units *or* 15 nanites. Press `n` for
every route to nanites ranked by nanites/hour per refiner — which reproduces
the guide's finding that Larval and Hadal Cores (3,000/h) beat the headline
230-nanite Hyaline Brain (259/h) twelvefold, and that Runaway Mould is the
slowest converter in the game at 24/h.

Each row also carries how gettable the input is and where it drops.

![the nanite ladder](docs/img/nanites.svg)

### Cooking

Eat or sell? Both, in that order. Every cooked product grants a temporary buff
*and* multiplies base value several times over, so the dish you eat is the dish
you sell — cook the batch, eat one, sell the rest. Press `e` for the 19 buffs
and the strongest dishes for each, with what they sell for and what one batch
adds over its ingredients.

![cooking buffs](docs/img/food.svg)

### Multi-tools

Four tabs: the 8 types side by side, the 5 primary weapons with their measured
best hit, where each rare type comes from (three of them free — the Harmonic
Camp puzzle, Sentinel Pillars, Korvax Monolith interfaces), and the tips that
matter: adjacency is horizontal and vertical only, supercharged slots want a
2×2 block, and Damage Potential is not damage output.

![multi-tools](docs/img/multitools.svg)

### Portal addresses

Press `P`. One box does both jobs: paste a **portal code** (twelve hex digits,
one per glyph), a **galactic address** (`0824:007F:00F3:01AC`, what a signal
booster shows) or a nmsportals.github.io link and it converts as you type —
type anything else and it searches the addresses you have saved.

![portal addresses](docs/img/portals.svg)

It is [nmsportals.github.io](https://nmsportals.github.io/) offline, with the
same constants:

```
galactic X = (portal X + 2047) % 4096      portal X = (galactic X + 2049) % 4096
galactic Y = (portal Y +  127) %  256      portal Y = (galactic Y +  129) %  256
galactic Z = (portal Z + 2047) % 4096      portal Z = (galactic Z + 2049) % 4096
```

The two frames disagree only about where zero is — portal coordinates count
from the **centre** of the galaxy, galactic ones from a corner — which is the
whole reason the same place has two unrecognisably different addresses. The
test suite pins that on the one fact both agree about: portal `000000000000`
is the galaxy centre, and galactic coordinates call it `07FF:007F:07FF`.

An address reads `p SSS YY ZZZ XXX` — planet, system index, then the voxel as
height, width, length. The screen colours each field in the code, in the glyph
list and in the drawn symbols, so it is obvious which three glyphs are X.

🔑 **The hex digit is the position on the dial.** The 16 glyphs sit in a fixed
order, `0`–`9` then `A`–`F`, so `A` is the eleventh symbol, every time — and
you need all 16 unlocked, not twelve.

#### The symbols themselves

A hex code is only half an address: at the portal you are looking at sixteen
pictures, not sixteen digits. So the actual shapes are in here too, once, in
`data/glyphs.json` — outlines traced off the art
[nmsportals](https://nmsportals.github.io/) draws its dial with, plus the same
mask knocked down to braille for the terminal. `mise run data:glyphs` re-derives
both; it needs `potrace`, and it is deliberately **not** part of
`mise run refresh`, because the symbols do not change when the game patches.

One source, two shapes, because the two places a glyph appears want opposite
things. The cheat sheet wants **vectors**: the fill is left out of the traced
path, so the same shape prints dark on Latte and light on Mocha — a PNG of
white line art would simply vanish on paper. A terminal wants **characters**:
it cannot show a PNG and no ordinary font has these symbols, so the same mask
is also stored as braille, 2×4 dots per cell, which is the only resolution
fine enough to keep `sunset` from collapsing into a blob.

On the portal screen both the converter and the saved-address detail draw the
twelve symbols, coloured by field the way the hex already is. The layout is
whatever the pane can hold: twelve across at 8×4 cells wants 107 columns, at
6×3 it wants 83, and below that it stacks six and six on the field boundary —
planet, system and Y above, Z and X below. Under about 40 columns it gives up
and leaves the hex, which is all it ever had.

Whether that draws is up to the terminal, not the app. **Ghostty draws braille
itself**, with its internal sprite renderer rather than the font — ask it:

```fish
ghostty +show-face --string="A⣿"
# U+41 « A » found in face "JetBrains Mono".
# U+28FF « ⣿ » is handled by Ghostty's internal sprites.
```

so it is cell-perfect there whatever `font-family` says. A terminal that asks
the font instead needs one carrying `U+2800`–`U+28FF`: plain JetBrains Mono
does **not** have it, its Nerd Font build does, and so do most patched
monospace fonts. With neither you get boxes where the glyphs should be, and
nothing else on the screen changes.

Because nothing at runtime re-derives that file, `mise run pdf:build` checks it
against `portals.py` before drawing: one position out and every address on the
sheet would point at a different star, plausibly.

| | |
| --- | --- |
| `D` | dial an address glyph by glyph — for when all you have is the symbols, off a video or a screenshot |
| `y` `Y` | copy the portal code / the galactic address |
| `s` `e` `d` | save what is converted, edit it, drop it to the trash |
| `u` `T` | undo the last drop / show the trash |
| `f` `o` | filter the saved list by kind / by who found it |
| `p` | change the planet glyph — the one a galactic address cannot carry |
| `Enter` | on a saved row, loads it back into the converter |

#### Mine, and shared

Every saved address is one of two kinds, and `o` cycles between them:

| | |
| --- | --- |
| **mine** | you stood there. Stamped with the date you saved it. The default when you press `s` |
| **shared** | off a catalogue or from a friend |

That split is worth more than it looks. What is verified in a catalogue entry
is the **address** — the location is seeded to the coordinate and generally
survives a patch. The class, the slot count and the headline damage figure are
somebody else's claim about somebody else's save, and those rot. Your own finds
are the ones you can vouch for.

The save form takes a prefix for Kind and Found — `multi`, `s` — and refuses
anything it cannot read rather than correcting it quietly: a kind that is not a
kind used to become `other`, and a galaxy of `twelve` used to become Euclid,
both without a word. The address itself needs no checking, since the form only
opens on one that already parsed. Saving a code you already have is allowed —
one system can hold a tool *and* a ship — but it says so.

Nothing deletes outright. `d` moves an address to the trash, `u` takes the last
one back, `T` lists what is in there — and inside the trash `u` restores the row
you are on while `d` is the one that really deletes. The trash rides along in
the same file under `_trash`, keeping the drop date and the row it came from, so
undo puts an address back where it was rather than at the end, and something
dropped in one session is still recoverable in the next.

The saved addresses live in `data/locations.json`, committed alongside the
guides they came from rather than hidden in XDG state, because they are
findings: they diff, review and share like everything else here. Press `s` to
add one through a form, or edit the file directly — it carries its own schema.
It ships with the fifteen from the Euclid shortlists in guides
21 (`21.multitool-damage.md`) and 14 (`14.starships-ranked.md`)
— seven multi-tools and eight Exotic starships, read off the Portal Repository
in September 2026, all marked `shared`. From the multi-tool screen, `P` opens
the list already filtered to tools.

### Inventory

![inventory](docs/img/inventory.svg)

---

### The cheat sheet

`mise run pdf:build` writes `docs/pdf/nms-cheatsheet.pdf` (Latte, for print) and
`nms-cheatsheet-dark.pdf` (Mocha, for screens):

1. **Money engine** — the ×6 loops, the precious-metal engine, best profit per
   batch and per machine-hour, the six refiner rules.
2. **Nanites** — every converter with where its input drops, then the
   essentials you should stop mining, and what Tier 0 / Tier 1 reach.
3. **Kitchen** — top dishes by value, then all 19 buffs with their three best
   dishes each.
4. **Multi-tools** — the 8 types, the weapons measured, how to get the free
   ones, and the adjacency and supercharged-slot rules.
5. **Portals** — all 16 glyphs in dial order **drawn**, how to read an address,
   the conversion both ways, and every saved address in two tables: the ones
   you found and the ones you were told about. Every address carries its twelve
   symbols beside the hex, coloured by field, so at the portal you dial off the
   page without translating anything.

It is generated from `data/cheatsheet.json`, so it cannot drift from the app —
including its own prose: claims like "every row below is 5s in the Processor"
are re-checked against the rows on each build and disappear if they stop being
true. The portals page goes further: `mise run pdf:build` round-trips every address
and re-checks the galaxy-centre invariant, so the build fails rather than
printing a code you cannot dial.

---

## Where the data comes from

Straight out of the installed game. `scripts/extract_game.py` unpacks the
recipe, product and substance tables and the English language tables from the
game's `.pak` archives with [hgpaktool](https://github.com/monkeyman192/HGPAKtool),
decompiles them to MXML with
[MBINCompiler](https://github.com/monkeyman192/MBINCompiler), and parses that
into `.cache/game/` (gitignored, like everything extracted: no game file is
ever committed). `scripts/build_data.py` then flattens it into the committed
files the app reads:

| | |
| --- | --- |
| `data/items.json` | 1,498 items — the 697 that recipes touch plus everything else that can sit in a cargo slot. Name, type, category, rarity, base value, and for cooked food the stat it buffs and how strongly |
| `data/recipes.json` | 1,684 recipes — flat, with ratio, loop multiplier, batch time, profit and rate precomputed |
| `data/source.json` | provenance: game version and build, the tool versions, the extraction date. Currently *Cosmos 7.06, build 180836* (GOG build 60091801558572527), MBINCompiler v7.04.1-pre3, hgpaktool 1.1.3 |
| `data/cheatsheet.json` | the subset the PDF prints |
| `data/acquisition.json` | **hand-written** — where loot comes from, since the game files record what a recipe needs but never where to find it. Taken from the guides; where they say nothing, the app says "unknown" rather than guessing |
| `data/storage.json` | **hand-written** — the storage layout from guide 24, section 10: what each of the ten containers holds, as ordered rules. The guide's named items first, then their families by the game's own subtitle and type; first match wins, no match means 9 - Inbox |
| `data/multitools.json` | **hand-written** — the multi-tool reference. The game files carry nothing useful about multi-tools, so this comes wholesale from guides 05 and 21 |
| `data/locations.json` | **hand-written** — portal addresses, from the Euclid shortlists in guides 14 and 21, plus whatever you find. The `s` key on the portal screen appends to it |
| `data/glyphs.json` | the 16 symbols — outlines for the PDF and braille for the terminal, both traced from the [nmsportals](https://nmsportals.github.io/) dial art by `mise run data:glyphs`. Regenerated only if it is lost; the glyphs do not move |

The extractor writes the tables in the same JSON shape as
[NMS-Handbook](https://github.com/ApexFatality93/NMS-Handbook), which publishes
the same game tables and was this project's source until Cosmos (it lags behind
patches). So `build_data.py` is the one normaliser for both, and Handbook stays
as a fallback for a machine without the game: `mise run data:refresh-handbook`.
Built from the same game version, the two give identical `data/`.

The game is read from `~/Games/No Man's Sky` (the GOG install); set
`$NMS_GAME_DIR` for anywhere else, Steam included. Nothing is written there.
`mise run sync` installs hgpaktool (the `extract` extra in `pyproject.toml`) and
`mise install` the pinned MBINCompiler — a self-contained binary, no .NET needed.

### After a game patch

1. **Pin the MBINCompiler release for the patch.** `mise run mbin:releases`
   lists the latest; set its tag as the `version` of
   `github:monkeyman192/MBINCompiler` in `mise.toml`.
2. `mise install`
3. `mise run game:version` — the game's version and build, the pinned
   MBINCompiler, and whether it still reads every table this build ships.
   If it says *MISMATCH*, back to step 1: MBINCompiler only warns on a struct
   it does not know, so the extract refuses to go on rather than misread.
4. `mise run extract:all` — unpack → decompile → convert → `data/`. Each stage is
   also its own task (`extract:unpack`, `extract:decompile`,
   `extract:convert`, `data:build`) to re-run one alone.
5. `mise run extract:diff` — what the patch changed against the last commit:
   recipes added, removed or retuned, items, values, times. Markdown;
   `docs/cosmos-changes.md` is this report for Cosmos.
6. `mise run test` — including the numbers the written guides assert.
7. `mise run pdf:build` — re-pick the cheat sheet and rebuild both PDFs.

`mise run refresh` is steps 4 and 7 in one.

The test suite is the point of step 6: it asserts the claims the notes make —
the three ×6 loops, Living Pearl → 100 Gold, Tier 0 reaching exactly 30
materials, the items no recipe produces, Larval Cores at 3,000 nanites/hour
against Runaway Mould's 24 — so if the game moves a ratio, it fails loudly
instead of quietly printing a wrong sheet. When a claim really did change,
update the guide and the test together; Cosmos moved three (see
`docs/cosmos-changes.md`).

---

## Contributing a portal address

The shared list in `data/locations.json` takes contributions two ways, both
checked by `scripts/portal_issue.py` with the same rules the TUI and the site
use to convert an address.

- **An issue**, on the *Share a portal address* form. The portals page on
  [nmsii.dlu.one](https://nmsii.dlu.one/#/portals) opens it pre-filled from its
  save form. The `Contributions` workflow reads the issue, converts the
  address, looks for duplicates, and replies in one comment it keeps updated:
  the glyphs and coordinates it read, or what to fix. It labels the issue
  `valid` or `needs-fix`, and checks again on every edit. When the repo owner
  adds `accepted`, it appends the entry as `shared`, credited to the reporter
  and the issue, and opens the pull request that closes it. That pull request
  starts no CI of its own (GitHub runs no workflow for one a workflow opened),
  so the bot validates the file and posts the required `check` status on it
  itself.
- **A pull request** editing the file. CI's `check` validates the whole file
  strictly (fields, kinds, galaxies, dialable codes, duplicates); when that
  file is the whole change, that is all it runs, in seconds. The TUI's loader
  skips a broken row so a screen never breaks; a PR is told instead. Locally:
  `mise run contrib:validate`.

The issue body is never handed to a shell: the script reads it from the event
file. `mise run contrib:setup` creates the labels and lets the workflow open
pull requests, once per repo; `mise run contrib:pending` lists what is waiting.

**Abuse protection.** Only the repo owner's `accepted` label adds anything,
and the checks need no secrets. Every job has a short timeout (3 minutes for
the issue jobs), and a burst of edits to one issue cancels all
but the newest check; an accept in progress is never cancelled. One person
may have three other submissions waiting: past that, a new one is labelled
`on-hold` with a single polite reply instead of being checked, and an edit
after the others are reviewed checks it and drops the label (the owner,
members and collaborators are exempt). `contrib:setup` also makes every
outside contributor's fork PR wait for approval before any workflow runs on
it. If it still gets out of hand, `mise run contrib:lockdown` turns on
GitHub's interaction limits (`--limit existing_users|contributors_only|collaborators_only`,
`--expiry one_day|three_days|one_week|one_month`), `contrib:unlock` lifts
them, and `contrib:status` shows the limits, the fork approval policy, open
submissions per author and the bot's runs in the last 24 hours. The tasks
that write take `--dry-run`.

---

## Roadmap

What's planned, roughly in order. Each item is an issue with the
[`roadmap`](https://github.com/rdlu/nms-items-interface/issues?q=is%3Aissue+label%3Aroadmap)
label; comment there before starting on one, so two people don't build the
same thing.

| | |
|---|---|
| [#13](https://github.com/rdlu/nms-items-interface/issues/13) Installable web app | the site as a PWA that works offline next to the game (in progress) |
| [#14](https://github.com/rdlu/nms-items-interface/issues/14) Desktop app | the site wrapped with Tauri v2, for people who don't want Python or podman |
| [#15](https://github.com/rdlu/nms-items-interface/issues/15) Rust + ratatui? | a serious evaluation of moving the CLI, TUI and MCP server to Rust, for single-binary installs. Not decided yet |
| [#16](https://github.com/rdlu/nms-items-interface/issues/16) Cheaper CI | split one slow test so a full CI run bills one minute (a good first issue) |
| [#18](https://github.com/rdlu/nms-items-interface/issues/18) AI helpers | CLAUDE.md, AGENTS.md, project skills and agent definitions for maintaining the repo |

Portal addresses are always welcome without asking first; see above.

---

## Tasks

Every task, as `mise tasks` lists them; nothing here needs a raw `npm` or
`vite` command remembered. The everyday ones sit in `mise.toml`; the rest are
scripts in `mise-tasks/<group>/<name>`, which mise names `group:name`.

**Everyday**

| Task | Does |
| --- | --- |
| `mise run tui` | the app (also `mise run run`) |
| `mise run dev` | the app with live CSS reload, for editing `app.tcss` |
| `mise run test` | pytest — data integrity + a headless pass over the TUI, across every core (`test:fast`) |
| `mise run check` | what CI runs: the full suite, the components, the shared addresses and the site build |
| `mise run ci:local` | what pull-request CI runs: `check`, plus `lint:shell` |
| `mise run deploy <pr>` | wait for the PR's checks (up to 20 min), refuse unless green, `gh pr merge --merge --delete-branch`, fast-forward a clean local `main`, and follow the Pages deploy (`--no-watch` to skip that); with no PR, re-run Pages for `main` |
| `mise run site` | build, then serve `dist/` on `:8791` as Pages will (alias of `web:site`) |
| `mise run refresh` | full data rebuild from the installed game: `extract:all` → `pdf:build` |
| `mise run setup` | system deps: the PDF fonts, potrace, resvg, imagemagick (paru) |
| `mise run sync` | Python deps, including hgpaktool for the extract |

**`tui:*`** — the app's side tools

| Task | Does |
| --- | --- |
| `mise run tui:console` | Textual debug console, beside `mise run dev` |
| `mise run tui:serve` | serve the TUI itself in a browser on `:8000` (textual serve) |
| `mise run tui:screenshot` | regenerate the SVGs in this README |

**`test:*`** — slices of the suite

| Task | Does |
| --- | --- |
| `mise run test:fast` | the full suite in parallel (pytest-xdist, `-n auto --dist worksteal`); serial is `uv run pytest -n0` |
| `mise run test:web` | only the web checks: the export, `site/src/lib/core.js` against the Python, the storage keys |
| `mise run test:md` | only the markdown checks: a page per item, numbers against `data.json`, chains, links, the schema |
| `mise run test:mcp` | only the MCP checks: each tool against its module, the server in-process and over stdio, the install tasks |

**`web:*`** — the static site

| Task | Does |
| --- | --- |
| `mise run web:install` | the site's npm packages, as `package-lock.json` pins them (skipped when current) |
| `mise run web:data` | export `web/data.json` and its markdown version (`llms.txt`, `web/md/`) for the static site |
| `mise run web:md` | only the markdown version, with the size of each file |
| `mise run web:dev` | export, then the site's live-reloading dev server on `:8790` |
| `mise run web:check` | svelte-check over the site's components; warnings fail it |
| `mise run web:build` | export, then build the deployable site into `dist/` |
| `mise run web:site` | build, then serve `dist/` on `:8791` as Pages will |
| `mise run web:favicon` | redraw the site icon from the Atlas glyph |

**`pages:*`** — GitHub Pages

| Task | Does |
| --- | --- |
| `mise run pages:status` | DNS, Pages settings, certificate and the last deploy |
| `mise run pages:setup` | turn Pages on with the Actions source and the `nmsii.dlu.one` domain |
| `mise run pages:https` | enforce HTTPS once the certificate is issued |

**`contrib:*`** — shared portal addresses

| Task | Does |
| --- | --- |
| `mise run contrib:validate` | check `data/locations.json` the way a pull request is checked |
| `mise run contrib:setup` | the bot's labels, letting the workflow open PRs, and holding every outside fork PR for approval (`--dry-run` prints the calls) |
| `mise run contrib:pending` | shared addresses waiting for review, with the bot's verdict |
| `mise run contrib:status` | interaction limits, fork PR approval policy, open submissions per author, bot runs in the last 24h |
| `mise run contrib:lockdown` | emergency brake: GitHub interaction limits, `existing_users` for `one_day` by default (`--limit`, `--expiry`, `--dry-run`) |
| `mise run contrib:unlock` | lift the interaction limits (`--dry-run`) |

**`box:*`** — containers (podman)

| Task | Does |
| --- | --- |
| `mise run box:tui` | the TUI in a container |
| `mise run box:site` | the static site in a container on `:8001` |
| `mise run box:build` | rebuild both images |

**`mcp:*`** — the MCP server for AI assistants ([setup](#for-ai-assistants-mcp))

| Task | Does |
| --- | --- |
| `mise run mcp:serve` | the server on stdio, as a client launches it (`nms mcp`) |
| `mise run mcp:inspect` | the server in the MCP Inspector web UI (`npx`, needs node) |
| `mise run mcp:install-claude` | register with Claude Code; `--scope user\|project\|local`, `--container`, `--dry-run` |
| `mise run mcp:install-codex` | register with OpenAI's Codex CLI; `--container`, `--dry-run` |
| `mise run mcp:install-pi` | register with pi (pi.dev); `--container`, `--dry-run` |
| `mise run mcp:install-opencode` | add the entry to opencode's config, backed up first; `--container`, `--dry-run` |
| `mise run mcp:install-goose` | add the extension to goose's config, backed up first; `--container`, `--dry-run` |
| `mise run mcp:uninstall <client>` | remove it from `claude`, `codex`, `opencode`, `goose`, `pi` or `all`; `--dry-run` |
| `mise run mcp:config` | print the JSON config for any other client, path filled in; `--container` |

**`extract:*`, `game:*`, `mbin:*`** — the game's tables

| Task | Does |
| --- | --- |
| `mise run game:version` | installed game version + build, the pinned MBINCompiler, and whether it reads this build |
| `mise run mbin:releases` | the latest MBINCompiler releases, to pick the pin after a patch |
| `mise run extract:all` | rebuild `data/` from the game: the four stages below in order |
| `mise run extract:unpack` | unpack the needed tables from the game's `.pak` files into `.cache/game/mbin/` |
| `mise run extract:decompile` | MBIN → MXML with the pinned MBINCompiler; fails on any table it does not recognise |
| `mise run extract:convert` | MXML → NMS-Handbook-shaped JSON in `.cache/game/json/`, version recorded |
| `mise run data:build` | normalise `.cache/game/json/` into `data/items.json`, `recipes.json`, `source.json` |
| `mise run extract:diff` | what changed in `data/` against the last commit, as markdown |

**`data:*`** — everything else under `data/`

| Task | Does |
| --- | --- |
| `mise run data:cheatsheet` | re-pick the cheat-sheet rows into `data/cheatsheet.json` |
| `mise run data:refresh-handbook` | the `refresh` rebuild from NMS-Handbook, without the game: fetch → normalise → cheat sheet → PDFs |
| `mise run data:fetch` | fallback: download NMS-Handbook's copy of the tables into `.cache/handbook/` |
| `mise run data:build-handbook` | normalise `.cache/handbook/` into `data/` instead |
| `mise run data:glyphs` | re-trace the 16 portal symbols into `data/glyphs.json` (`data:fetch-glyphs`, then `data:build-glyphs`) |

**`pdf:*`** — the cheat sheet

| Task | Does |
| --- | --- |
| `mise run pdf:build` | both cheat-sheet PDFs into `docs/pdf/` (re-picks the cheat sheet first) |
| `mise run pdf:watch` | rebuild the light PDF on every save |

**`hooks:*`, `lint:*`** — local checks (see [Git hooks](#git-hooks))

| Task | Does |
| --- | --- |
| `mise run hooks:install` | turn on the pre-commit and pre-push hooks, beside any global ones |
| `mise run hooks:uninstall` | turn them off again |
| `mise run hooks:run` | run both hooks now, on the whole tree |
| `mise run hooks:status` | the hooks git will run per event, local and global |
| `mise run lint:shell` | `bash -n` and shellcheck over `mise-tasks/`, `.githooks/`, `scripts/*.sh` |

**`deps:*`**

| Task | Does |
| --- | --- |
| `mise run deps:outdated` | what is behind: mise tools (node, uv, typst), npm packages, Python dependencies |

### Renamed tasks

The tasks used to be one flat list. The old names still run, as aliases of
the new ones, except `web`, which is now `tui:serve` so it does not read as
part of the site's `web:*`.

| Was | Now |
| --- | --- |
| `web-install`, `web-data`, `web-md`, `web-dev`, `web-check`, `web-build` | `web:install`, `web:data`, `web:md`, `web:dev`, `web:check`, `web:build` |
| `site`, `favicon` | `web:site` (`site` stays as the short name), `web:favicon` |
| `web` (textual serve) | `tui:serve` — no alias |
| `console`, `screenshot` | `tui:console`, `tui:screenshot` |
| `test-web`, `test-md` | `test:web`, `test:md` |
| `pages-setup`, `pages-https`, `pages-status` | `pages:setup`, `pages:https`, `pages:status` |
| `validate-locations`, `contrib-setup`, `contrib-pending` | `contrib:validate`, `contrib:setup`, `contrib:pending` |
| `box-tui`, `box-site`, `box-build` | `box:tui`, `box:site`, `box:build` |
| `extract`, `extract-unpack`, `extract-decompile`, `extract-convert`, `extract-diff` | `extract:all`, `extract:unpack`, `extract:decompile`, `extract:convert`, `extract:diff` |
| `game-version`, `mbin-releases` | `game:version`, `mbin:releases` |
| `fetch`, `build-data`, `build-data-handbook`, `cheatsheet-data` | `data:fetch`, `data:build`, `data:build-handbook`, `data:cheatsheet` |
| `glyphs`, `fetch-glyphs`, `build-glyphs` | `data:glyphs`, `data:fetch-glyphs`, `data:build-glyphs` |
| `refresh-handbook` | `data:refresh-handbook` |
| `pdf`, `pdf-watch` | `pdf:build`, `pdf:watch` |
| `deps-outdated` | `deps:outdated` |

### Git hooks

`mise run hooks:install` turns on two hooks, so most of what CI checks fails
on your machine first and costs no Actions minutes. They are git's
config-based hooks (`hook.<name>.event`/`.command` in the repo's local
config), not `core.hooksPath`, so global hooks keep running beside them.

- **pre-commit**, on the staged files only: actionlint on workflows, `bash -n`
  and shellcheck on the shell scripts, a JSON parse of `data/*.json`,
  `contrib:validate` when `data/locations.json` is staged, svelte-check when
  `site/` is.
- **pre-push**, on what the push changes: the suite in parallel, and the
  export plus the site build, each only when the change can affect it
  (`scripts/changes.sh`, the same filter CI uses).

Skip them once with `NMSII_SKIP_HOOKS=1` or `--no-verify`. CI
(`.github/workflows/ci.yml`) still checks every pull request, for Dependabot,
forks and anyone without the hooks. Its `check` job is the required status
check on `main`, so it runs on every ready pull request, even a docs-only one
(a checkout and a diff, in seconds); a draft waits until it is marked ready.

### Keeping dependencies current

- `mise run deps:outdated` lists everything that is behind, in one place, and
  changes nothing.
- **node** is set in one line, `node = "24"` in `mise.toml`'s `[tools]`. The
  Pages workflow installs it through mise from that line, so bumping it there
  bumps CI too. It tracks the newest LTS. The `Containerfile`'s
  `node:24-slim` stage should follow it.
- **Dependabot** (`.github/dependabot.yml`) opens weekly pull requests for the
  npm packages, as one group, and for the GitHub Actions. That includes
  `setup-uv`, which is pinned to an exact release because it publishes no
  moving major tag. Those pull requests now get CI (`ci.yml`: the suite,
  svelte-check, the export and site build, the shell lint), so a green check
  means the bump builds.
- **Python** is locked in `uv.lock`; `uv lock --upgrade` moves it.

---

## Layout

```
src/nms_items/
  model.py     items, recipes, the forward/reverse indexes, search
  graph.py     chain planning (Knuth's AND-OR Dijkstra), reachability, the nanite ladder
  ease.py      how gettable an item is: tier, chain depth, raw breadth, loot notes
  food.py      cooked dishes grouped by the buff they grant
  multitools.py  the hand-written multi-tool reference, loaded from data/
  portals.py   glyphs <-> galactic coordinates, and the saved addresses
  glyphart.py  the 16 symbols as braille, for drawing a code in a terminal
  inventory.py what you're carrying, persisted to XDG state
  mcp_server.py  `nms mcp`: the answers above as MCP tools, for AI assistants
  app.py       the recipe table + detail pane
  screens.py   chain, nanites, cooking, multi-tools, portals, inventory, help
  widgets.py   the vim-keyed DataTable, Tree, scroll pane and search box
scripts/       extract from the game (or fetch), normalise, diff, pick cheat-sheet rows, trace glyphs, screenshots, web export
site/          the web page's source (Svelte 5 + Vite), built into dist/
  index.html   the shell, and the theme script that runs before first paint
  src/App.svelte  header, view, footer; picks the view from the #/route
  src/views/   one component per screen: Recipes, Chain, Nanites, Cooking, Portals, ...
  src/components/  List (the vim-keyed table), GlyphStrip, Header, Palette, ThemeMenu, ...
  src/lib/     core.js (the logic test_web.py checks), data, router, keys, storage
  src/global.css  the skin's tokens, fonts and base; each component styles itself
web/           served as it is: fonts/, favicons, and what build_web.py exports
package.json, vite.config.js  the site's build, pinned by package-lock.json
scripts/pages.py  GitHub Pages settings for nmsii.dlu.one, via gh
scripts/portal_issue.py  checks contributed addresses: issue form, PRs, the accept step
scripts/mcp_clients.py  registers `nms mcp` with AI clients (the mcp:install-* tasks)
.github/       the Pages deploy, the contributions bot, the issue form
Containerfile, compose.yaml  the TUI and the site without a local Python
cheatsheet.typ the PDF
```

---

## License

[GPL-3.0](LICENSE). Recipe and item data are extracted from the game files
with hgpaktool (MIT) and MBINCompiler (LGPL-3.0), neither of which is
redistributed here; until Cosmos they came from
[NMS-Handbook](https://github.com/ApexFatality93/NMS-Handbook) (GPL-3.0), still
the fallback source. No Man's Sky and its data belong to Hello Games. Portal glyphs are traced from [nmsportals](https://nmsportals.github.io/).

