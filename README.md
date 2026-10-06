# pymcserver

A small Minecraft 1.8.9 server written in Python. This is an ongoing project, so think of it as a place to experiment with the protocol and world interactions rather than a complete survival server.

## Run it

You'll need Python 3. Start the server from the repository root:

```sh
python main.py
```

It listens on port `25565`. Connect with a Minecraft 1.8.9 client. Type `help` in the server console to see the available commands; `stop` shuts it down.

## What works so far

You can connect, move around a small shared world, and place blocks. Several blocks have their expected orientation and interactions: doors, gates, levers, buttons, pressure plates, stairs, slabs, chests, and others. Buttons reset after a short delay, pressure plates respond to nearby players, and placing against an interactive block while sneaking still works. Rejected placements are sent back to the client so ghost blocks can be corrected.

The world is currently four chunks: 32 by 32 blocks, from Y=32 through Y=47. Changes are kept in memory and disappear when the server restarts. The game is essentially creative mode; survival mechanics aren't in place.

There are a few focused checks in `tests/test_blocks.py`. Run them from the repository root with:

```sh
python tests/test_blocks.py
```

## Still missing

This isn't a full Minecraft server yet. Redstone components can change appearance, but signals don't propagate. Chests and other containers don't open an inventory. Players aren't rendered to one another, and there are no mobs, dropped items, chat, permissions, or world saving. Gravity, plant growth, and other world simulation are also absent.

Water and lava flow, weather and kill commands, player respawn, and block mining have code in the project but haven't been rechecked recently.

## Known issue

Trapdoors can be placed on a side face, but placement on top or bottom faces may not work with the 1.8.9 client. If side placement also fails, run `log` in the server console, try once more, and check the debug output.