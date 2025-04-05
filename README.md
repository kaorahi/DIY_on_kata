# DIY_on_kata: A barebones engine for playing Go, easy to tweak for your own AI

This is a minimalistic Go engine built in basic Python, featuring naive MCTS and a GTP interface. It's designed to be easy to modify, making it a convenient starting point for experimenting with new search ideas or for student study projects.

The engine uses KataGo's neural network by calling KataGo itself. This is completely redundant, but it would be one of the shortest paths to achieving the above goal. By standing on KataGo's shoulders, the code remains remarkably minimal while still strong for a starter kit.

## FAQ

### How strong?

Possibly stronger than Leela Zero or ELF.

### Comparison with TamaGo?

[TamaGo](https://github.com/kobanium/TamaGo) allows you to train your own neural network. This project does not include that feature but offers simpler code for the search part, making it easy to read and modify.

## Usage

Download [KataGo](https://github.com/lightvector/KataGo) and confirm that its [analysis engine](https://github.com/lightvector/KataGo/blob/master/docs/Analysis_Engine.md) runs correctly in a terminal. Take note of its command-line arguments. For example:

```
/.../katago analysis \
  -model /.../kata_b28.bin.gz \
  -config /.../analysis_example.cfg
```

Then, try running `python gtp.py ...`, where `...` represents the above recorded command:

```
python3 /.../DIY_on_kata/gtp.py \
  /.../katago analysis \
  -model /.../kata_b28.bin.gz \
  -config /.../analysis_example.cfg
```

Enter GTP commands such as `name`, `genmove B`, and `list_commands`. Ignoring debug messages on STDERR (`... 2> /dev/null`), they should appear as follows:

```
name
= DIY_on_kata

genmove B
= Q4

list_commands
= protocol_version
name
version
known_command
list_commands
quit
boardsize
clear_board
komi
play
genmove
undo
lz-analyze
time_settings
fixed_handicap

quit
=

```

If everything works as expected, set up the command in [(patched) Lizzie](https://github.com/kaorahi/lizzie) or [LizGoban](https://github.com/kaorahi/lizgoban).

## Link

[Project Home](https://github.com/kaorahi/DIY_on_kata)
