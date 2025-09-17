#!/usr/bin/env python3
"""
play_sheet_on_virtual_organ.py
--------------------------------
Parse a MusicXML/MIDI/ABC file and stream it in real time to a *virtual* organ
(using FluidSynth) that plays through the computer's speakers.
"""

import sys
import time
import mido
from music21 import converter, note, chord, stream
import fluidsynth

# ----------------------------------------------------------------------
# 1️⃣  Configuration
# ----------------------------------------------------------------------
SCORE_FILE = "score.xml"                # <-- change to your file
SOUND_FONT = "organ.sf2"                # <-- path to an organ soundfont
ORGAN_PROGRAM = 1                       # GM program number for a pipe organ
TEMPO_BPM = None                         # If None, read from the score

# ----------------------------------------------------------------------
# 2️⃣  Open FluidSynth
# ----------------------------------------------------------------------
try:
    fs = fluidsynth.Synth()
    fs.start(driver="alsa")  # On Windows use "dsound", on macOS use "coreaudio"
    sfid = fs.sfload(SOUND_FONT)
    if sfid == -1:
        raise RuntimeError(f"Could not load soundfont '{SOUND_FONT}'")
    fs.program_select(0, sfid, 0, ORGAN_PROGRAM)  # channel 0, organ program
except Exception as e:
    print(f"[ERROR] Failed to initialise FluidSynth: {e}")
    sys.exit(1)

print(f"[+] FluidSynth started – using '{SOUND_FONT}' (program {ORGAN_PROGRAM})")

# ----------------------------------------------------------------------
# 3️⃣  Load and parse the score
# ----------------------------------------------------------------------
try:
    score = converter.parse(SCORE_FILE)
except Exception as e:
    print(f"[ERROR] Could not read score '{SCORE_FILE}': {e}")
    sys.exit(1)

# If the user supplied a tempo, override whatever is in the file
if TEMPO_BPM is not None:
    bpm = TEMPO_BPM
else:
    # Pull the first MetronomeMark from the file; fall back to 120 if absent
    met_mark = score.metronomeMarkBoundaries
    bpm = met_mark[0].number if met_mark else 120

print(f"[+] Score parsed – tempo set to {bpm} BPM")

# ----------------------------------------------------------------------
# 4️⃣  Helper: convert a music21 element into one or more FluidSynth note
#      events (with proper timing)
# ----------------------------------------------------------------------
def play_element(el, time_offset):
    """
    el: music21 Element (Note or chord)
    time_offset: how many seconds to wait *before* this element starts
    """
    # Wait until the start time of this element
    time.sleep(time_offset)

    if isinstance(el, note.Note):
        pitch = el.pitch.midi
        duration = el.quarterLength  # in quarter‑lengths

        # FluidSynth expects values 0–127
        fs.noteon(0, pitch, 127)          # channel 0, note on, max velocity
        # Wait for the note’s duration
        time.sleep(duration * (60.0 / bpm))
        fs.noteoff(0, pitch)

    elif isinstance(el, chord.Chord):
        # Organs are monophonic, but we still want to honour every voice.
        # For a realistic pipe‑organ, we could let each voice go to its own
        # channel; here we simply play all voices on the same channel.
        dur = el.quarterLength
        pitches = [p.midi for p in el.pitches]
        for p in pitches:
            fs.noteon(0, p, 127)
        time.sleep(dur * (60.0 / bpm))
        for p in pitches:
            fs.noteoff(0, p)

# ----------------------------------------------------------------------
# 4️⃣  Stream the score note‑by‑note
# ----------------------------------------------------------------------
# Flatten the score so we get a simple timeline of elements.
flat = score.flat

# We’ll keep a running clock (seconds) to know when to fire each event.
# This keeps the code *independent* of FluidSynth’s own clock.
start_time = time.perf_counter()
current_offset = 0.0  # seconds

# Convert tempo to seconds‑per‑quarter‑note
seconds_per_quarter = 60.0 / bpm

# Iterate through all musical elements that have timing info.
# We ignore rests – the clock is driven by the durations of the previous
# note(s).
for el in flat.getElementsByClass(['Note', 'Chord']):
    # The element already carries a `.duration.quarterLength`.
    duration_q = el.duration.quarterLength
    # Wait until the element’s start time
    # (the loop itself naturally respects the duration of the *previous* note)
    play_element(el, current_offset)
    # Advance the clock by this element’s duration
    current_offset += duration_q * seconds_per_quarter

print("[+] Playback finished – shutting down FluidSynth.")
fs.delete()
