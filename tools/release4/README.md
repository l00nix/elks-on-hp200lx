# 4.0 packaging audit scripts

These scripts consume the original project-workspace inputs under output/. They
are an audit of release preparation, not standalone build or install scripts.
Follow docs/hp200lx/BUILD-4.0.md with the release source archive to build kernels.

The original prepare_docs.py/package.py/verify.py record the initial promotion.
The naming refresh uses package_refresh.py, brand_images.py and verify_refresh.py.
The latter verifies archive checksums, matching source outputs and local links.
brand_images.py updates only the documented image paths and checks preservation
of all other contents/metadata. No script here writes physical media or publishes.
