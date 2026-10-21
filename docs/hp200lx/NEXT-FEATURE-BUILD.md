# Next feature-build backlog

This log tracks work after the FINAL2b / 4.0 release candidate. Entries are
planned work, not shipped capabilities. FINAL2b remains the baseline for
release acceptance; this backlog does not change its code or binaries.

## Minimal HP firmware kernel profile

Added: 2026-10-21. Status: accepted for the next feature build; not implemented.

Evaluate a compile-time profile that recovers application memory by excluding
sleep support while retaining the HP features needed for everyday use.
Provide this profile for both existing storage configurations: local-image
root and CF root. Share the source and build configuration rather than
maintaining a separate kernel fork. No release version is assigned yet.

Keep:

- BIOS keyboard support, zoom, panning and colour inversion.
- The double-speed display correction where selected.
- Required storage, serial and networking support for the selected profile.
- A small ON/OFF handler that reports sleep unavailable and prevents unintended
  firmware suspension.

Compile out:

- Sleep/wake entry and recovery, including CF and Accton recovery paths.
- The dedicated suspend stack, saved recovery state and sleep-only diagnostics.
- Sleep-only storage fingerprinting and guards; retain normal storage
  initialization, validation and integrity protections.

Omitting a runtime sleep flag is insufficient: excluded code and data must
actually disappear from the linked kernel. Keep loader help and option handling
consistent with the selected build; unsupported sleep flags must be rejected
clearly. Preserve existing filesystem-image compatibility.

### Measurement and acceptance

1. Compare full and minimal builds from the same source baseline, with identical
   settings except the profile. Record kernel text, data and BSS sizes, image
   sizes, hashes and the total bootkit footprint on DOS C:.
2. On the same hardware and filesystem image, compare free conventional memory
   and the largest available allocation after boot, with networking running,
   and with ELKSWeb running. Keep the process list, buffers, browser page and
   test sequence equivalent; distinguish resident-kernel savings from userland
   memory consumption.
3. Verify local and CF boot, serial, keyboard, zoom/pan/inversion, double-speed
   correction, application return to text, storage writes and reboot persistence.
   Verify Accton networking and fresh ELKSWeb browsing on the local profile.
4. Confirm ON/OFF does not suspend and displays the intended notice. Validate
   that the full profile retains its existing sleep behavior.
5. Publish measured savings and maintenance/packaging costs before deciding
   whether to ship the extra kernel choices. No memory-saving target is promised.

Initial inspection of FINAL2b found a 1 KiB suspend stack plus sleep code and
recovery state. That identifies potential savings, not a measured increase in
application memory. Additional kernels stored on C: consume disk space; only
the selected kernel is loaded for an ELKS session.
