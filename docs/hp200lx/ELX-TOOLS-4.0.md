# ELX tools in Release 4.0

CF images already contain the tested updates. The unchanged local MNX images
contain earlier builds; use `hp200lx-4.0-elx-tools.zip` to update those or an older
filesystem. These executables run under ELKS, not DOS.

Transfer individual files from `bin/` to a writable ELKS filesystem. For a roomy
filesystem, transfer `ELX40.TAR`, then from /root run `tar xf ELX40.TAR` and
`cd /root/elx40`. Run `./elxbat` etc. to select the update rather than /bin's older
copy. Check `df` before transfer: the 720 KiB image may not have room for both
archive and extracted files. Transfer one executable at a time when space is tight.
To install permanently, keep a host backup, then copy the chosen executable to
/bin and `chmod 755 /bin/NAME`. No automatic installer is run.

| Program | Usage |
| --- | --- |
| ELXbat 0.1.4 | `elxbat`; partial redraw of changed regions, light theme, two voltage gauges, power icon and nominal warning markers. R rereads, Q/Esc exits. |
| ELXstat | `elxstat`, `elxstat -v`; firmware/system summary including cached battery volts and power source. |
| ELX Commander | `elxcmd LEFT RIGHT`; Tab switches panel; arrows select; Enter opens; V views; C copies; M moves; D deletes; N creates directory; R refreshes; Q returns from viewer or exits panels. Read each confirmation prompt. Existing destinations are not overwritten. |
| ELXdash 0.2.0-test4 | `elxdash`; Tab selects, Left/Right adjusts; B opens Battery menu; Up/Down selects, Enter chooses, Esc cancels. Q exits. Charging stays locked without explicit `--charge-test`; charging is experimental and not certified by this release. |
| ELXctl | `elxctl status`, `elxctl contrast 16`, `elxctl volume 2`, `elxctl zoom 80x25`, `elxctl annunciators right`, `elxctl firmware-timeout 180`. `--help` lists options. Firmware timeout is not ELKS's sleep policy. |
| ELXcap | `elxcap /root/SCREEN.BMP` captures the HP display. `-f pbm` selects PBM; default BMP and PBM preserve the same monochrome pixels. Existing files are not overwritten. |

Delayed capture from the palmtop:

```sh
elxcap -q -d 15 /root/BATTERY.BMP >/tmp/elxcap.log 2>&1 &
elxbat
```

Leave ELXbat visible for at least 15 seconds. Alternatively, run a manual capture
from an existing serial shell while the desired display remains on the HP.
The optional `--hotkey` / Alt+period kernel integration is not included in 4.0;
“kernel patch needed” for that mode is expected.

Battery values are firmware-cached voltages of unknown age, not percentages or
remaining runtime. Gauge triangles are nominal BIOS reference thresholds;
firmware alert flags are shown separately. Release acceptance does not establish
ADC freshness or certify charging. Sleep is blocked while graphics tools run.

Original GPL/font notices accompany the source. GEMCAP/CAPLX inspired capture,
CXCTL and ABC/LX informed control workflows, and Commander uses the familiar
Norton Commander two-panel model; these are independent implementations.
