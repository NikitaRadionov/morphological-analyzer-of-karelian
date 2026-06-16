#!/bin/bash
# Builds the lexd+twol FST pipeline. Run inside WSL from this directory:
#   wsl -d Ubuntu -- bash -c "cd '/mnt/c/.../karelian_analyzer/fst' && bash build.sh"
set -e

lexd karelian.lexd | hfst-txt2fst -o lexd.hfst
hfst-twolc -q karelian.twol -o twol.hfst
hfst-compose-intersect lexd.hfst twol.hfst -o gen.hfst
hfst-invert gen.hfst -o ana.hfst
hfst-fst2fst -O gen.hfst -o gen.hfstol
hfst-fst2fst -O ana.hfst -o ana.hfstol

echo "Built gen.hfst / ana.hfst / gen.hfstol / ana.hfstol"
