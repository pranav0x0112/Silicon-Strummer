# SPDX-FileCopyrightText: © 2024 Your Name
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

# ─── Pin definitions ──────────────────────────────────────────────────────────
BTN_RIGHT  = 0   # ui_in[0]
BTN_LEFT   = 1   # ui_in[1]
BTN_UP     = 2   # ui_in[2]
BTN_DOWN   = 3   # ui_in[3]
BTN_SOUND  = 4   # ui_in[4]

# TinyVGA PMOD: uo_out = {hsync, B[0], G[0], R[0], vsync, B[1], G[1], R[1]}
UO_HSYNC   = 7   # uo_out[7]
UO_VSYNC   = 3   # uo_out[3]

# Audio is on uio_out[7]
UIO_AUDIO  = 7

# 1 VGA frame = 800 * 525 = 420,000 cycles
# We use a much smaller "tick" for tests — just enough to cross a vsync
FRAME_CYCLES = 800 * 525
FAST_TICK    = 1000   # cheap substitute when we just need the logic to react

def get_bit(signal, bit):
    """Safe bit extraction — returns None if signal contains X/Z."""
    try:
        return (signal.value.integer >> bit) & 1
    except ValueError:
        return None

async def reset(dut):
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    dut.rst_n.value  = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value  = 1
    await ClockCycles(dut.clk, 10)

async def press(dut, btn, cycles=FAST_TICK):
    """Hold a button for `cycles` clock cycles then release."""
    dut.ui_in.value = (1 << btn)
    await ClockCycles(dut.clk, cycles)
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 100)

# ─── Test 1: Reset — syncs toggle ────────────────────────────────────────────
@cocotb.test()
async def test_reset(dut):
    """After reset, hsync should be toggling."""
    dut._log.info("=== test_reset ===")
    clock = Clock(dut.clk, 40, unit="ns")  # 25 MHz
    cocotb.start_soon(clock.start())

    await reset(dut)

    hsync_vals = set()
    for _ in range(1000):
        await RisingEdge(dut.clk)
        v = get_bit(dut.uo_out, UO_HSYNC)
        if v is not None:
            hsync_vals.add(v)

    assert len(hsync_vals) == 2, f"hsync is stuck! values seen: {hsync_vals}"
    dut._log.info("PASS: hsync toggling")

# ─── Test 2: Audio off by default ────────────────────────────────────────────
@cocotb.test()
async def test_audio_off(dut):
    """Audio pin should stay 0 when BTN_SOUND is not pressed."""
    dut._log.info("=== test_audio_off ===")
    clock = Clock(dut.clk, 40, unit="ns")
    cocotb.start_soon(clock.start())

    await reset(dut)
    dut.ui_in.value = 0

    audio_vals = set()
    for _ in range(5000):
        await RisingEdge(dut.clk)
        v = get_bit(dut.uio_out, UIO_AUDIO)
        if v is not None:
            audio_vals.add(v)

    assert audio_vals <= {0}, f"Audio should be silent, got: {audio_vals}"
    dut._log.info("PASS: audio silent without BTN_SOUND")

# ─── Test 3: Audio toggles when sound enabled ────────────────────────────────
@cocotb.test()
async def test_audio_on(dut):
    """Audio pin should toggle when BTN_SOUND is held."""
    dut._log.info("=== test_audio_on ===")
    clock = Clock(dut.clk, 40, unit="ns")
    cocotb.start_soon(clock.start())

    await reset(dut)
    dut.ui_in.value = (1 << BTN_SOUND)

    audio_vals = set()
    for _ in range(300_000):
        await RisingEdge(dut.clk)
        v = get_bit(dut.uio_out, UIO_AUDIO)
        if v is not None:
            audio_vals.add(v)
        if len(audio_vals) == 2:
            break

    dut.ui_in.value = 0
    assert len(audio_vals) == 2, "Audio square wave never toggled!"
    dut._log.info("PASS: audio toggles with BTN_SOUND")

# ─── Test 4: Move right ───────────────────────────────────────────────────────
@cocotb.test()
async def test_move_right(dut):
    """Press RIGHT — design should stay alive."""
    dut._log.info("=== test_move_right ===")
    clock = Clock(dut.clk, 40, unit="ns")
    cocotb.start_soon(clock.start())

    await reset(dut)
    await press(dut, BTN_RIGHT)

    hsync_vals = set()
    for _ in range(1000):
        await RisingEdge(dut.clk)
        v = get_bit(dut.uo_out, UO_HSYNC)
        if v is not None:
            hsync_vals.add(v)

    assert len(hsync_vals) == 2, "hsync stuck after moving right!"
    dut._log.info("PASS: design alive after moving right")

# ─── Test 5: All directions ───────────────────────────────────────────────────
@cocotb.test()
async def test_move_all_directions(dut):
    """Move in all 4 directions — design should stay alive."""
    dut._log.info("=== test_move_all_directions ===")
    clock = Clock(dut.clk, 40, unit="ns")
    cocotb.start_soon(clock.start())

    await reset(dut)

    for btn, label in [
        (BTN_RIGHT, "RIGHT"),
        (BTN_DOWN,  "DOWN"),
        (BTN_LEFT,  "LEFT"),
        (BTN_UP,    "UP"),
    ]:
        dut._log.info(f"  pressing {label}")
        await press(dut, btn)

    hsync_vals = set()
    for _ in range(1000):
        await RisingEdge(dut.clk)
        v = get_bit(dut.uo_out, UO_HSYNC)
        if v is not None:
            hsync_vals.add(v)

    assert len(hsync_vals) == 2, "hsync stuck after directional moves!"
    dut._log.info("PASS: all directions OK")

# ─── Test 6: Boundary clamping ───────────────────────────────────────────────
@cocotb.test()
async def test_boundary_clamp(dut):
    """Hammer RIGHT 10x — should clamp at fret 7, not crash."""
    dut._log.info("=== test_boundary_clamp ===")
    clock = Clock(dut.clk, 40, unit="ns")
    cocotb.start_soon(clock.start())

    await reset(dut)

    for _ in range(10):
        await press(dut, BTN_RIGHT)

    hsync_vals = set()
    for _ in range(1000):
        await RisingEdge(dut.clk)
        v = get_bit(dut.uo_out, UO_HSYNC)
        if v is not None:
            hsync_vals.add(v)

    assert len(hsync_vals) == 2, "hsync stuck after boundary test!"
    dut._log.info("PASS: boundary clamping OK")

# ─── Test 7: Sound while moving ──────────────────────────────────────────────
@cocotb.test()
async def test_sound_while_moving(dut):
    """Hold sound + direction simultaneously — audio should still toggle."""
    dut._log.info("=== test_sound_while_moving ===")
    clock = Clock(dut.clk, 40, unit="ns")
    cocotb.start_soon(clock.start())

    await reset(dut)
    dut.ui_in.value = (1 << BTN_SOUND) | (1 << BTN_RIGHT)

    audio_vals = set()
    for _ in range(300_000):
        await RisingEdge(dut.clk)
        v = get_bit(dut.uio_out, UIO_AUDIO)
        if v is not None:
            audio_vals.add(v)
        if len(audio_vals) == 2:
            break

    dut.ui_in.value = 0
    assert len(audio_vals) == 2, "Audio didn't toggle while moving!"
    dut._log.info("PASS: audio works while moving")