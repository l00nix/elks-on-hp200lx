# Release 4.0 source and build guide

Download `hp200lx-4.0-source.tar.gz` from the release and verify SHA256SUMS.
The authoritative matching source is the archive's `hp200lx-4.0-source/` tree.
Repository-root ELKS source/build instructions are historical; use this snapshot
for the released HP kernels. `src/` contains ELKS, `ports/local1/` the DOS helpers
and kernel profiles, `applications/` the frozen ELX sources, and `vendor/` the
browser/graphics sources and notices. `SOURCE-HISTORY.md` preserves provenance.

The package promotes FINAL2b without recompiling or changing binary IDs.
Build on a Linux host with the ELKS IA16 cross toolchain, NASM, make, Python 3
and a C compiler. The toolchain is an external dependency, not included.
From the extracted root:

```sh
export CROSS=/absolute/path/to/elks/cross
bash ports/local1/build.sh
bash assemble-final2.sh
```

The build creates CF and local kernels and their matching sizes/maps/helpers.
`ports/local1/RUNELKS.BAT` uses the fixed C:\ELKS39FB directory. Do not change
kernel size constants or combine helpers from another build. The source archive
also includes frozen linked artifacts for the emulator checks and comparison.
No claim of cross-toolchain byte reproducibility is made for an arbitrary compiler.

For software checks, install Python `unicorn` and supply the original files:

```sh
export HPLOCAL_TEST_IMAGE=/absolute/path/to/fd2880-minix.img
export HPLOCAL_720_IMAGE=/absolute/path/to/ELKS2M.MNX
export HPLOCAL_3M_IMAGE=/absolute/path/to/ELKS4M.MNX
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 verify-preserved.py
```

Run checks from the extracted root. `verify-preserved.py` uses the historical
FINAL2 validation manifest to check unchanged filesystem/application inputs.
Individual utility build instructions remain in applications/*; ELKSWeb source
and its external-build integration are maintained at https://github.com/l00nix/ELKSWeb.
The source archive includes the browser snapshot matching the shipped binary.

The image-tools ZIP includes the stock-image injector and exact historical CF
build inputs. Their historical READMEs describe original candidate construction;
use the 4.0 README for installation and support scope. Existing image/kernel
banners are deliberately retained. No proprietary HP ROM or DOS runtime is bundled.
