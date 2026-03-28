## How it works

Silicon Strummer turns the VGA display into a playable guitar fretboard. The screen is divided into a grid of 8 frets (columns) × 6 strings (rows), each cell roughly 80×80 pixels. A cursor highlights the currently selected note in amber. Moving the cursor changes the selected note, and holding the sound button outputs a square wave tone on the audio pin at the corresponding frequency. Note pitch is mapped linearly across the 48-cell grid (~100 Hz to ~2 kHz).

## How to test

Connect a VGA monitor via the TinyVGA PMOD. Use the input buttons as follows:

- **ui_in[0]** — move cursor right (next fret)
- **ui_in[1]** — move cursor left (previous fret)
- **ui_in[2]** — move cursor up (previous string)
- **ui_in[3]** — move cursor down (next string)
- **ui_in[4]** — hold to enable audio output

Move the cursor around the fretboard grid and hold the sound button to hear the note at the selected position. The cursor is shown as a bright amber cell; grid lines are dim blue and string lines are dim green on a black background.

## External hardware

- TinyVGA PMOD (connected to `uo_out`) for VGA display output
- Speaker or audio output circuit connected to `uio_out[7]` for square wave audio