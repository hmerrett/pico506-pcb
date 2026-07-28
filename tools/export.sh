#!/bin/bash
# Export the review/publish artefacts: schematic PDF, 3D renders, fab outputs.
# Run tools/check.sh first — this exports whatever is currently on disk.
set -e
cd "$(dirname "$0")"

CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
HW=..
DOC=$HW/doc
mkdir -p "$DOC"

echo "== schematic PDF"
$CLI sch export pdf --no-background-color -o "$HW/pico506-sch.pdf" \
    "$HW/pico506.kicad_sch" 2>/dev/null | tail -1

echo "== 3D renders"
for side in top bottom; do
    $CLI pcb render --side "$side" --quality high --background opaque \
        --width 2400 --height 1400 --zoom 0.85 \
        -o "$DOC/pico506-3d-$side.png" "$HW/pico506.kicad_pcb" 2>/dev/null \
        | tail -1
done
# an angled view reads better than orthographic top-down for a README hero shot
# 330 rather than -30: the arg parser rejects any value starting with '-'
$CLI pcb render --side top --quality high --background opaque \
    --perspective --rotate 330,0,25 --width 2400 --height 1400 --zoom 0.9 \
    -o "$DOC/pico506-3d-iso.png" "$HW/pico506.kicad_pcb" 2>/dev/null | tail -1

echo "== layer plots (PDF, for eyeballing copper/silk)"
$CLI pcb export pdf --layers F.Cu,F.Silkscreen,Edge.Cuts \
    --mode-single -o "$DOC/pico506-front.pdf" "$HW/pico506.kicad_pcb" \
    2>/dev/null | tail -1
$CLI pcb export pdf --layers B.Cu,B.Silkscreen,Edge.Cuts --mirror \
    --mode-single -o "$DOC/pico506-back.pdf" "$HW/pico506.kicad_pcb" \
    2>/dev/null | tail -1

echo "== fab: gerbers + drill + BOM + position"
rm -rf "$DOC/gerber"
mkdir -p "$DOC/gerber"
$CLI pcb export gerbers --no-protel-ext -o "$DOC/gerber/" \
    "$HW/pico506.kicad_pcb" 2>/dev/null | tail -1
$CLI pcb export drill --format excellon --excellon-separate-th \
    -o "$DOC/gerber/" "$HW/pico506.kicad_pcb" 2>/dev/null | tail -1
(cd "$DOC" && zip -qr pico506-gerbers.zip gerber && echo "wrote pico506-gerbers.zip")
$CLI sch export bom --fields 'Reference,Value,Footprint,${QUANTITY},Datasheet' \
    --labels 'Refs,Value,Footprint,Qty,Datasheet' \
    --group-by Value,Footprint --sort-field Reference \
    -o "$DOC/pico506-bom.csv" "$HW/pico506.kicad_sch" 2>/dev/null | tail -1
$CLI pcb export pos --format csv --units mm --side both \
    -o "$DOC/pico506-pos.csv" "$HW/pico506.kicad_pcb" 2>/dev/null | tail -1

echo
echo "artefacts in $DOC:"
ls -1 "$DOC"
