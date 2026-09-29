# HP BIOS keyboard and display services

These notes answer Greg Haerr's [IRQ2/zoom question](https://github.com/ghaerr/elks/issues/2236#issuecomment-5880382415)
using the HP 100LX / HP 200LX Developer's Guide (Hewlett-Packard, 1994).
They separate the documented BIOS design from the paths tested by this port.

## Keyboard and manual display controls

The guide's **Pre-Processing (Before Int 09h)** section, original SDK file
`C3000011.HTM`, describes a software keyboard controller. KBD and TIMER1 are
both IRQ2 / INT 0Ah sources. TIMER1 moves through debounce, scan-code creation,
and scan-code delivery states. Delivery triggers IRQ1 / INT 09h through Hornet
hardware; it is not an `INT 09h` instruction. The **Keyboard Overview** also
describes placing the scan code in port 60h before triggering IRQ1.

The next section, **Hotkey Sequences**, `C3000012.HTM`, explicitly assigns
Zoom and Menu+Arrow window movement to that keyboard-controller emulation,
outside INT 09h. It also lists contrast, shading, inversion, and annunciator
controls. Their inclusion in the guide does not mean all have been tested here.

This explains why manual zoom and panning can work with ELKS's normal scan-code
keyboard/TTY path and existing BIOS console driver. The port preserves the ROM
IRQ2 service; it does not implement those display hotkeys itself. Hardware
testing of 3.5.2c confirms manual zoom and panning, including during a busy user
loop that was successfully stopped with Ctrl-C. The precise internal ROM call
sequence has not been disassembled or traced.

## BIOS interfaces and the cursor-tracking distinction

| Guide section / original SDK file | What it establishes |
| --- | --- |
| **INT 0Ah: Hornet-Specific Hardware Interrupt**, `C3000021.HTM` | IRQ2 multiplexes up to 16 sources using a RAM service-vector table and a rotating poll; TIMER1 receives priority. IRQ2 is not solely a keyboard interrupt. |
| **INT 10h, AH=D0h: Text Zoom**, `C3000057.HTM` (guide page 3-73) | Changes the font/display-controller setup and `CRTZOOM` while retaining `CRTMODE` and screen data. This documents an interface; it does not prove the hotkey handler invokes it through an interrupt instruction. |
| **INT 15h, AH=45h: Window Keys & Cursor Tracking Control**, `C300007B.HTM` | Controls manual window movement and automatic cursor tracking separately through `WINFLG`. |
| **Display Cursor Update Request Interrupt**, `C3000023.HTM` | IRQ2's display-cursor service sets `CurFlag`. The BIOS INT 08h timer service performs the deferred adjustment that keeps the cursor in view. |

Manual panning and automatic cursor tracking must therefore not be conflated.
This port uses ELKS's native IRQ0 timer; it does not chain the BIOS INT 08h
handler. Working Menu+Arrow panning is not evidence that the BIOS's deferred
cursor-tracking path is fully maintained. No timer-chaining change is made in
3.5.2d.

## What this tells us about stacks

The reviewed sections explain why different IRQ2 sources and display hotkeys
could exercise different ROM paths, but do not specify a worst-case IRQ2 CPU
stack requirement. They do not establish a need for a 1 KiB interrupt stack.
The guide's separate System Manager application-stack advice is not an IRQ2
stack specification.

3.5.2c observed written peaks of 202/700 bytes on task stacks and 224/1024 on
the shared interrupt stack. Those measurements include wrapper/probe overhead
and are not worst-case bounds. 3.5.2d disables `CONFIG_ASYNCIO` for synchronous
ATA-CF, allowing upstream's normal 640-byte task-stack selection; the shared
stack remains 1024 bytes for the next hardware test.

Before combining broader `kstack`/`istack` tracing with our custom ROM probe,
their marker conventions must be reconciled. In our pinned upstream source,
`check_istack()` scans for nonzero words, task tracing uses `0x5555`, and the
ROM probe paints `0xA55A`. Enabling both unchanged would contaminate the stack
measurements. 3.5.2d retains the ROM probe and leaves `CONFIG_TRACE` disabled.

## Source locations

The project working copy contains `HP_100LX_200LX_Developers_Guide_combined.html`
with section IDs such as `page-c3000012-htm`, and a searchable text export.
In the 530-page local PDF export, preprocessing/hotkeys are on PDF pages 31–32,
IRQ2/DCI on 47–49, Text Zoom on 71–72, window control on 95–96, and Keyboard
Overview on 140–141. These are export page numbers, not the original chapter
page numbering. Original SDK filenames above identify the sections across
editions without depending on the local PDF pagination.
