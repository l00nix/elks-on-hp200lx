# Release 4.0 source and build guide

Download `hp200lx-4.0-source.tar.gz` from the release and verify SHA256SUMS.
The authoritative matching source is the archive's `hp200lx-4.0-source/` tree.
Repository-root ELKS source/build instructions are historical; use this snapshot
for the released HP kernels. `src/` contains ELKS, `ports/local1/` the DOS helpers
and kernel profiles, `applications/` the frozen ELX sources, and `vendor/` the
browser/graphics sources and notices. `SOURCE-HISTORY.md` preserves provenance.

The naming refresh rebuilds the accepted implementation with 4.0 version text.
No functional kernel or application changes are included in this refresh.
Build on a Linux host with the ELKS IA16 cross toolchain, NASM, make, Python 3
and a C compiler. The toolchain is an external dependency, not included.
From the extracted root:

```sh
export CROSS=/absolute/path/to/elks/cross
bash ports/local1/build.sh
bash assemble-release4.sh
```

The build creates CF and local kernels and their matching sizes/maps/helpers.
`ports/local1/RUNELKS.BAT` uses the fixed C:\ELKS4 directory. Do not change
kernel size constants or combine helpers from another build. The source archive
also includes frozen linked artifacts for the emulator checks and comparison.
No claim of cross-toolchain byte reproducibility is made for an arbitrary compiler.

For software checks, install Python `unicorn` and supply the original files:

```sh
export HPLOCAL_TEST_IMAGE=/absolute/path/to/fd2880-minix.img
export HPLOCAL_720_IMAGE=/absolute/path/to/ELKS2M.MNX
export HPLOCAL_3M_IMAGE=/absolute/path/to/ELKS4M.MNX
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 verify-release4.py
```

Run checks from the extracted root. `verify-release4.py` checks the packaged boot binaries against the release manifest.
Historical manifests preserve the original candidate identities.
Individual utility build instructions remain in applications/*; ELKSWeb source
and its external-build integration are maintained at https://github.com/l00nix/ELKSWeb.
The source archive includes the browser snapshot matching the shipped binary.

The image-tools ZIP includes the stock-image injector and exact historical CF
build inputs. Their historical READMEs describe original candidate construction;
use the 4.0 README for installation and support scope. The refreshed image/kernel banners use 4.0. The included brand_images.py is a
workspace-dependent audit script; the injector and growth tools have their own
standalone instructions. No proprietary HP ROM or DOS runtime is bundled.
