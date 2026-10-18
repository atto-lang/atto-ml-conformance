# Contract peers (draft, not verified)

This folder holds **independent** TypeSpec and JSON Schema Draft 2020-12
authorities for small **metadata**. This is not a generated-equals-authored
parity pass yet. The TypeSpec generator must emit its own JSON Schema witness,
and `ORESOFTWARE/typespec-json-schema-validator` (tjsv) must compare peer
schemas in memory with fail-closed diagnostic and digest-bound receipts.
Plain structural diff is not enough where schema vocabularies differ.

P0 schema deliberately supports only f32/f64 contiguous CPU descriptor
metadata; the kernel, runtime, and binary storage are NOT modeled here.
The emitted TypeSpec schema's bounds, required keys, and additional-property
closure must be reconciled with the independent JSON Schema before adoption.
JSON Schema alone cannot prove `storageLength == product(shape)` or that the
byte count equals `dtype_size * storageLength`; validate those separately in
the Oreslang runtime with overflow-safe checked arithmetic.

`ml-device.wit` is a versioned **future boundary proposal**, not an implemented
driver, ABI, or compatibility claim. It must be compiled against a pinned WIT
toolchain and cross-checked with capability/ownership transfer semantics.
Opaque resources are not raw GPU pointers. Explicit GPU requests must not
silently fall back to CPU.

Keep tensor payloads in size-bounded binary storage rather than JSON values.
No production promotion without peer-drift comparison, invalid/oversize
negative tests, generator/toolchain SHAs, and actual `.ores` runtime evidence.
