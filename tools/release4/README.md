# 4.0 promotion helpers

These scripts package the frozen project-workspace inputs under output/; they
are an audit of release preparation, not standalone kernel build scripts.
Follow docs/hp200lx/BUILD-4.0.md with the release source archive for a kernel build.
No tool here writes physical media, modifies filesystem inputs, or publishes.
prepare_docs.py reconstructs the publication prose from the reviewed staging
files; package.py verifies frozen input hashes, packages sources/images/tools,
and emits checksums; verify.py verifies archives, source identity and local links.
