# Legacy SDK Archive

`/legacy/` contains vendor-supplied and historical SDK material that is kept
for reference only.

## `vm64/`

`/legacy/vm64/` is an archived snapshot of the legacy VMR64 SDK. It is:

- unmaintained
- not part of the supported `nextwaves-sdk` v1.x surface
- not covered by the repository root MIT license

Licensing and provenance:

- The legacy C++ serial transport includes code derived from
  `wjwwood/serial`, which carries MIT/BSD licensing in its preserved headers.
- The remaining VMR64 reader code is vendor-supplied legacy code and retains
  its original headers and licensing terms.

Keep existing headers intact when referencing this archive. Do not copy legacy
files into `/sdk/nation/` without a separate licensing review.
