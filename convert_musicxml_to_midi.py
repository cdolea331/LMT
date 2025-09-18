#!/usr/bin/env python3
"""
convert_musicxml_to_midi.py

A tiny command‑line tool that turns a MusicXML file into a standard MIDI file.

Usage
-----
    python convert_musicxml_to_midi.py input.xml output.mid

Dependencies
------------
    pip install music21
"""

import argparse
import os
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
#  Helper function – all the heavy lifting lives here
# --------------------------------------------------------------------------- #
def musicxml_to_midi(xml_path: Path, midi_path: Path, program: int = None) -> None:
    """
    Convert a MusicXML file to a MIDI file.

    Parameters
    ----------
    xml_path : Path
        Path to the source MusicXML file.
    midi_path : Path
        Path where the resulting MIDI file will be written.
    program : int, optional
        Global MIDI program (0‑127) to apply to every part.  If omitted, the
        program information embedded in the MusicXML (if any) is preserved.
    """
    from music21 import converter, midi

    # Load the MusicXML file.  `converter.parse` understands the format by
    # file extension and will use musicxml parsing internally.
    try:
        score = converter.parse(str(xml_path))
    except Exception as exc:
        raise RuntimeError(f"Failed to parse MusicXML: {exc}") from exc

    # Optionally override all instruments with a single program.
    if program is not None:
        if not 0 <= program <= 127:
            raise ValueError("Program number must be in the range 0‑127.")
        for part in score.parts:
            part.insert(0, midi.ProgramChange(program, part.id))

    # Write the MIDI file.  `score.write` accepts a format identifier.
    try:
        score.write('midi', str(midi_path))
    except Exception as exc:
        raise RuntimeError(f"Failed to write MIDI: {exc}") from exc

# --------------------------------------------------------------------------- #
#  CLI handling
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert MusicXML → MIDI using music21."
    )
    parser.add_argument(
        "--input_xml",
        type=Path,
        help="Path to the source MusicXML file.",
    )
    parser.add_argument(
        "--output_midi",
        type=Path,
        help="Path where the resulting MIDI file will be written.",
    )
    parser.add_argument(
        "-p", "--program",
        type=int,
        default=None,
        help="Optional global MIDI program (0‑127) to apply to all parts.",
    )
    args = parser.parse_args()

    # Basic sanity checks
    if not args.input_xml.is_file():
        parser.error(f"Input file does not exist: {args.input_xml}")

    if args.output_midi.exists():
        confirm = input(
            f"{args.output_midi} already exists. Overwrite? [y/N] "
        ).lower()
        if confirm != "y":
            print("Aborted.")
            sys.exit(0)

    # Perform conversion
    try:
        musicxml_to_midi(args.input_xml, args.output_midi, args.program)
        print(f"✅  Successfully created {args.output_midi}")
    except Exception as exc:
        print(f"❌  Conversion failed: {exc}")
        sys.exit(1)


# --------------------------------------------------------------------------- #
#  If this file is executed directly, run the CLI
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    main()
