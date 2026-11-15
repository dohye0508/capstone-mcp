# Round 3 file and calculator checks

No Capstone GUI, sensor, debug endpoint or native mutation was used. Tests exercise internal contracts and synthetic snapshots only.

## Reproduced safety defects fixed

- Calculator selection no longer falls back to the first arbitrary Edit control. It requires an enabled identified formula editor, rejects ambiguous candidates, and refuses truncated snapshots before editor input. This prevents a missing calculator editor from overwriting a search/name field.
- Native file dialogs cannot establish unique targets from truncated snapshots. Empty export snapshots no longer cause an indexing exception.
- Export cleanup failures are no longer silently swallowed during an earlier failure. The error retains the original failure, identifies the known export handle, and explicitly reports that an unresolved native dialog may still block Capstone. It does not click unknown child dialogs or guess confirmation labels.

These changes do not implement the complete Capstone calculator grammar or certify native dialog behavior.

## Additional read-only archive evidence

Inspected XML in all 26 installed QuickStart templates under `C:/Program Files/PASCO scientific/Capstone/Resources/Templates` and the 34 user-provided archives. No archive was modified or uploaded.

| Source | Files | XML members | DataSet elements | Segment observations |
| --- | ---: | ---: | ---: | --- |
| Installed templates | 26 | 26 | 41 | All have exactly one segment |
| User corpus | 34 | 34 | 332 | All have exactly one segment |

No numeric stored independent-axis member was present in this combined corpus. Uppercase `TRUE`/`FALSE` occurred extensively. The sole mixed-case `True` in the templates was `DataSource.ShortName` in `Monitoring Weather.cap`: it is a name, **not a boolean field**, so it does not justify relaxing boolean parsing.

CAP03 therefore still needs a native boolean-field example; CAP04 still needs a real multi-segment file and export that establish segment ordering/gap semantics. CAP07 still needs proof that a counted NUL is a terminator rather than a stored character. No representation was guessed.

CAP17 received an additional unconditional regression with distinct independent/dependent members and deliberately different values. The parser reads each declared member correctly. This refutes a blanket source-level assertion that the dependent filename is always used for both axes; it does not establish unobserved native encodings. Production parser behavior did not need changing for that test.

WF01 remains OS/native-format verification debt: unsupported clipboard handles are rejected before copying, but synthetic tests cannot certify OLE delayed rendering or every clipboard owner.

CALC01 remains native grammar/acceptance verification debt. Submission continues to return unverified status rather than claim that a syntactically balanced expression was accepted.
