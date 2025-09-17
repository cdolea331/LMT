#!/usr/bin/env python3
"""
play_sheet_on_organ.py
----------------------
Parse a MusicXML/MIDI/ABC file and stream it in real time to a MIDI‑capable digital organ.
"""

import sys
import time
import mido
from music21 import converter, note, chord, stream

# ------------------------------------------------------------------
# 1️⃣  Configuration -------------------------------------------------
# ------------------------------------------------------------------
SCORE_FILE = "score.xml"           # <-- change to your file (MusicXML, MIDI, ABC, etc.)
MIDI_PORT_NAME = "YourOrganMidiPort"  # <-- the name of the MIDI port your organ listens on
ORGAN_CHANNEL = 1                 # MIDI channel (1‑16); most organs use channel 1
ORGAN_KEY_OFFSET = 0              # if your organ uses a different key numbering
TIME_RESOLUTION = 0.05            # seconds per quarter‑note (adjust for tempo)

# ------------------------------------------------------------------
# 2️⃣  Open the MIDI port --------------------------------------------
# ------------------------------------------------------------------
try:
    midi_out = mido.open_output(MIDI_PORT_NAME, virtual=False)
except OSError as e:
    print(f"ERROR: Could not open MIDI port '{MIDI_PORT_NAME}'.")
    print(f"Available ports: {mido.get_input_names()} (input) | {mido.get_output_names()} (output)")
    sys.exit(1)

print(f"[+] Connected to MIDI port: {MIDI_PORT_NAME}")

# ------------------------------------------------------------------
# 3️⃣  Load and parse the score ------------------------------------
# ------------------------------------------------------------------
try:
    score = converter.parse(SCORE_FILE)
except Exception as e:
    print(f"ERROR: Could not parse '{SCORE_FILE}': {e}")
    sys.exit(1)

print(f"[+] Loaded score '{SCORE_FILE}'")

# ------------------------------------------------------------------
# 4️⃣  Flatten the score to a stream of notes/chords ----------------
# ------------------------------------------------------------------
flat_notes = score.flat.notesAndRests
print(f"[+] Score contains {len(flat_notes)} note/rest objects")

# ------------------------------------------------------------------
# 5️⃣  Helper: convert a music21 element to MIDI events -------------
# ------------------------------------------------------------------
def note_to_midi_events(m21_note, start_tick):
    """
    Given a music21 Note or Rest, return a list of MIDI messages
    (note_on, note_off) with correct timings.
    """
    events = []

    # MIDI channel (0‑based)
    chan = ORGAN_CHANNEL - 1

    if isinstance(m21_note, note.Rest):
        # Just skip rests – no MIDI message
        duration = m21_note.duration.quarterLength
        return events, duration

    # For chords, pick the highest pitch (or use all voices)
    if isinstance(m21_note, chord.Chord):
        # Use the highest note in the chord as the organ “voice”
        pitches = sorted(m21_note.pitches, key=lambda p: p.midi)
        midi_pitch = pitches[-1].midi
    else:
        midi_pitch = m21_note.pitch.midi

    # Apply key offset (if needed)
    midi_pitch += ORGAN_KEY_OFFSET

    # Compute velocity (0–127)
    velocity = int(m21_note.volume.velocity) if m21_note.volume.velocity else 64

    duration = m21_note.duration.quarterLength

    # Build MIDI messages
    events.append(mido.Message('note_on', note=midi_pitch, velocity=velocity,
                               channel=chan, time=start_tick))
    events.append(mido.Message('note_off', note=midi_pitch, velocity=0,
                               channel=chan, time=duration * 1000))  # mido uses ms

    return events, duration

# ------------------------------------------------------------------
# 6️⃣  Main playback loop --------------------------------------------
# ------------------------------------------------------------------
# Convert quarterLength to milliseconds per quarter
ms_per_quarter = 60000 / 120  # default 120 BPM -> you can read tempo from the score
# Use tempo from the score if present
if score.metronomeMarkBoundaries:
    # Take the first tempo marking
    bpm = score.metronomeMarkBoundaries[0][2].number
    ms_per_quarter = 60000 / bpm
    print(f"[+] Tempo found: {bpm} BPM (ms/quarter={ms_per_quarter:.2f})")

print("[+] Starting playback …")

for idx, m21_obj in enumerate(flat_notes):
    # Determine how many ticks (ms) to wait before sending the next event
    # We use absolute time for simplicity; more complex scheduling can be added
    events, dur = note_to_midi_events(m21_obj, 0)
    if not events:
        # It's a rest; just sleep
        time.sleep(dur * TIME_RESOLUTION)
        continue

    # Send events
    for msg in events:
        # mido's send() expects relative time (time in ticks); we set it directly
        midi_out.send(msg)
        # Wait for the message duration (convert ms to seconds)
        time.sleep(msg.time / 1000.0)

print("[+] Playback finished. Closing MIDI port.")
midi_out.close()
