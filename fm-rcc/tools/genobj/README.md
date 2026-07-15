# genobj — deterministic object-XML compiler (Phase 3, not yet built)

The missing piece of the deterministic story: `gen_patch.py` compiles *patches* deterministically, but object XML for **new** scripts still comes from the model writing snippet XML against the fm-xml guides. This tool closes that gap:

- A **shape catalog**: script-step XML shapes with named slots, synthesized from the OOE corpus (`skills/fm-xml/references/ooe-source.md`), real SaXML exports, and round-trip tests — original content, redistributable.
- A compiler CLI: `genobj.py --step "Show Custom Dialog" --slots '{...}'` → validated XML fragment, ready for gen_patch AddAction wrapping or clipboard delivery.
- **Top ~30 steps first** (mine frequency from client DDRs with `ddr.py`), model+fm-xml+fmlint remains the fallback for the tail.
- Every shape lands with a golden round-trip test: scaffold → patch the step in → re-export → normalized compare (the harness in `tests/patch/test_e2e_scaffold.py` already does this dance).

Until this exists: generate via the fm-xml skill, validate with fmlint, deliver per fm-patch tier rules.
