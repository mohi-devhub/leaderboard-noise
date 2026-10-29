# Executed-source provenance

Files are copied byte for byte from saved sources whose hashes match recorded launch or runtime evidence. `manifest.json` maps each retained process to its matching worker. Early A10 processes are launch-attested only; later A10 and L4 worker self-hashes are checked. Normalized serialized A10 function snapshots are shipped alongside full launcher/worker sources. The Llama BOS correction has separate before/after files.

Do not format or modify these snapshots. They preserve executed/submitted code, including historical style and dependencies. Check `SHA256SUMS`; read each attestation label before claiming runtime coverage. These hashes are not third-party signatures.
