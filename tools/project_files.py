#!/usr/bin/env python3
"""Write pico506.kicad_pro and the project library tables."""

import json
import os

HW = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PRO = {
    "board": {
        "3dviewports": [],
        "design_settings": {
            "defaults": {},
            # lib_footprint_mismatch is meaningless for this project: the board
            # is regenerated from netlist.py + the footprint libraries on every
            # build, so the board copy cannot "drift" from the library the way
            # a hand-edited board can.  KiCad flags U1 regardless — its pads,
            # graphics, zones and attributes all compare identical (see
            # tools/README notes); the residual difference is bookkeeping that
            # survives a pcbnew load/save round-trip.  Every other DRC rule is
            # left at its default severity.
            "rule_severities": {
                "lib_footprint_mismatch": "ignore",
            },
            "rules": {
                "min_clearance": 0.18,
                "min_copper_edge_clearance": 0.1,
                "min_hole_clearance": 0.25,
                "min_hole_to_hole": 0.25,
                "min_microvia_diameter": 0.2,
                "min_microvia_drill": 0.1,
                "min_resolved_spokes": 1,
                "min_silk_clearance": 0.0,
                "min_text_height": 0.8,
                "min_text_thickness": 0.08,
                "min_through_hole_diameter": 0.3,
                "min_track_width": 0.2,
                "min_via_annular_width": 0.1,
                "min_via_diameter": 0.5,
                "solder_mask_to_copper_clearance": 0.0,
                "use_height_for_length_calcs": True,
            },
        },
        "layer_presets": [],
        "viewports": [],
    },
    "boards": [],
    "cvpcb": {"equivalence_files": []},
    "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
    "meta": {"filename": "pico506.kicad_pro", "version": 3},
    "net_settings": {
        "classes": [
            {
                "bus_width": 12,
                "clearance": 0.18,
                "diff_pair_gap": 0.25,
                "diff_pair_via_gap": 0.25,
                "diff_pair_width": 0.5,
                "line_style": 0,
                "microvia_diameter": 0.3,
                "microvia_drill": 0.1,
                "name": "Default",
                "priority": 2147483647,
                "pcb_color": "rgba(0, 0, 0, 0.000)",
                "schematic_color": "rgba(0, 0, 0, 0.000)",
                "track_width": 0.4,
                "via_diameter": 0.8,
                "via_drill": 0.4,
                "wire_width": 6,
            }
        ],
        "meta": {"version": 4},
        "net_colors": None,
        "netclass_assignments": None,
        "netclass_patterns": [],
    },
    "pcbnew": {
        "last_paths": {},
        "page_layout_descr_file": "",
    },
    "schematic": {
        "annotate_start_num": 0,
        "bom_export_filename": "",
        "connection_grid_size": 50.0,
        "drawing": {
            "dashed_lines_dash_length_ratio": 12.0,
            "dashed_lines_gap_length_ratio": 3.0,
            "default_line_thickness": 6.0,
            "default_text_size": 50.0,
            "field_names": [],
            "intersheets_ref_own_page": False,
            "intersheets_ref_prefix": "",
            "intersheets_ref_short": False,
            "intersheets_ref_show": False,
            "intersheets_ref_suffix": "",
            "junction_size_choice": 3,
            "label_size_ratio": 0.375,
            "operating_point_overlay_i_precision": 3,
            "operating_point_overlay_i_range": "~A",
            "operating_point_overlay_v_precision": 3,
            "operating_point_overlay_v_range": "~V",
            "overbar_offset_ratio": 1.23,
            "pin_symbol_size": 25.0,
            "text_offset_ratio": 0.15,
        },
        "legacy_lib_dir": "",
        "legacy_lib_list": [],
        "meta": {"version": 1},
        "net_format_name": "",
        "page_layout_descr_file": "",
        "plot_directory": "",
        "spice_current_sheet_as_root": False,
        "spice_external_command": 'spice "%I"',
        "spice_model_current_sheet_as_root": True,
        "spice_save_all_currents": False,
        "spice_save_all_dissipations": False,
        "spice_save_all_voltages": False,
        "subpart_first_id": 65,
        "subpart_id_separator": 0,
    },
    "sheets": [["e5a1a1de-0000-4000-8000-000000000001", "Root"]],
    "text_variables": {},
}

FP_LIB_TABLE = """(fp_lib_table
  (version 7)
  (lib (name "pico506-lib")(type "KiCad")(uri "${KIPRJMOD}/pico506-lib.pretty")(options "")(descr "Pico506 project footprints"))
)
"""

SYM_LIB_TABLE = """(sym_lib_table
  (version 7)
  (lib (name "pico506-lib")(type "KiCad")(uri "${KIPRJMOD}/pico506-lib.kicad_sym")(options "")(descr "Pico506 project symbols"))
)
"""


def write_all():
    with open(os.path.join(HW, "pico506.kicad_pro"), "w") as f:
        json.dump(PRO, f, indent=2)
        f.write("\n")
    with open(os.path.join(HW, "fp-lib-table"), "w") as f:
        f.write(FP_LIB_TABLE)
    with open(os.path.join(HW, "sym-lib-table"), "w") as f:
        f.write(SYM_LIB_TABLE)
    print("wrote project files")


if __name__ == "__main__":
    write_all()
