# Release 4.0 hardware acceptance

The maintainer declared all planned tests complete on **2026-10-21**, including
sleep-guard behaviour, and authorized release. This records acceptance of the
FINAL2b promotion; it does not fabricate individual measurements absent from logs.

| Coverage | Evidence and result |
| --- | --- |
| Local boot | 720 KiB and 3 MiB images exercised on hardware; stock v0.9.2 FD2880 boot/browser also demonstrated. Exact FINAL2b local identities confirmed by serial on both speed variants. |
| Accton sleep, both speeds | User reported six connected-cable sleep/wake cycles, including a roughly 30-second sleep. Serial checks retained ktcp PID 4 across repeated checks and verified marker hashes, new writes, DNS, fresh HTTP and GIF download after wake. |
| Internet after wake | FrogFind HTML fetched (1,273 bytes) and GIF (1,888 bytes); GIF MD5 7ca81e8805d80095e8de8baf2c1b87b3. No ktcp restart for those checks. |
| Local double persistence | /root/sleep2, MD5 e5ba02f8716d16acefcc92e600fab736, matched before/after and in the DOS backing image. |
| Local single persistence | /root/sleep2b, MD5 4b4322e154f0e0d98d4d7fabe525b56a, matched after repeated wake and reboot. |
| Offline local checks | Entire single image downloaded; double image reconstructed from 4 KiB CRC map/delta and independently matched against whole-file DOS CRC/length. Forced read-only mfsck -fsv exited 0 for both; copied images unchanged. |
| Offline caveat | Both post-test copies had state 0: clean flag unset, error flag unset. No structural errors found, no repair/flag rewrite performed. Cause of the flag state not established. |
| CF | Both speed variants exercised during acceptance. Exact FINAL2b double CF identity confirmed; user reported edit sleep. Old markers remained unchanged; new cf2bprobe MD5 6d41fc2811f5e4145930745e2b18eaa5 survived reboot. Single exact-FINAL2b CF detail is not separately captured in the final serial record; maintainer closed overall acceptance. |
| Empty-slot local double | FINAL2b local root confirmed; user reported shell sleep and edit refusal. Existing marker matched; new write/sync/read succeeded. Source explicitly restricts local sleep to PID 1 idle shell. |
| Guards | Maintainer confirmed sleep guards work. Local edit refusal is expected. Graphics/serial/general-app suspend are excluded. |
| Applications | User confirmed ELXbat partial updates/power status, ELXdash menu/locked charging, and Commander view/copy/no-overwrite/move/delete/cancel/mkdir/nonempty-directory refusal. Serial checked file hashes. These utility binaries did not change during FINAL2b promotion. |

## Frozen build identity

- KERNLOC SHA256: 800272df3f11dda6e4e98864c691f15025fff934c8ced128856f980704ab81b1
- KERNCF SHA256: e48701173b95857289547ecc958ae62580bc4a7f150395ee23d1827abdeeffa5
- Build identity: hp200lx-3.9-final2b-local / hp200lx-3.9-final2b-cf, 2026-10-20.
- Software suite: 39 discovered, 39 passed, zero skipped. Preserved-image handoffs
  and unchanged utility hashes/audits also passed.
- Image construction: independent Minix checks, payload/metadata comparison and
  reproducible images. CF growth has 13 regression tests plus host-side data beyond
  32 MiB readback/fsck; it is not evidence of physical high-zone access on every card.

Offline copy SHA256s (used images, not distribution downloads):

- Single: 155a11c7b6688d7b25024e2983988b4135e8df56675784985bd823d26ce811e7
- Double: a535653d246b609b029667191aa7cdd7e52422e3a7eae4f3e5930f4eda3e969a

Raw chronological hardware notes remain in the project acceptance archive.
The release source includes frozen software-validation reports. Earlier reports
marked “hardware pending” retain their original dates; this acceptance summary
supersedes that status, without changing historical evidence.

## 4.0 naming refresh — 21 October 2026

The current boot folder is C:\ELKS4. Both rebuilt kernels differ from the
accepted candidate only in version strings; symbol maps and executable code
are identical. Current hashes are in the release MANIFEST.json. Image banners
and documentation were updated, and the unused CF /linux copy matches 4.0.
All other image paths, permissions, ownership, links and geometry were verified
unchanged. Each refreshed filesystem passed a forced read-only offline check.
The original hardware identities above are retained as historical evidence.
