#!/bin/bash
# regenerate board, fill zones, run DRC, summarize
set -e
cd "$(dirname "$0")"
# keep the generator's own complaints visible: a silently failed GND link or an
# unresolved net is a real defect that DRC only shows as "unconnected items"
python3 gen_pcb.py | grep -Ei "fail|unresolved|complete on pass" || true
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 refill.py ../pico506.kicad_pcb 2>/dev/null | head -1
python3 project_files.py >/dev/null
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc --severity-all --format report -o ../drc.txt ../pico506.kicad_pcb 2>/dev/null | tail -1
echo "== violation classes:"
grep -E "^\[" ../drc.txt | sort | uniq -c | sort -rn
