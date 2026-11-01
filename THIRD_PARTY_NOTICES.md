# Third-party software

Original installer code, tests and documentation use the root [MIT license](LICENSE).
Upstream applications and factory software retain their own licenses and rights.

## CarLink

Setup downloads the official [CarLink v1.0.7 APK](https://github.com/F-e-n-y-x/CarLink/releases/tag/v1.0.7).
[Corresponding upstream source](https://github.com/F-e-n-y-x/CarLink/tree/v1.0.7)
is available separately. This repository does not modify, re-sign or distribute
the APK. CarLink uses [AGPL-3.0](https://github.com/F-e-n-y-x/CarLink/blob/v1.0.7/LICENSE);
a copy is included in [LICENSES/CarLink-AGPL-3.0.txt](LICENSES/CarLink-AGPL-3.0.txt).
CarLink incorporates DiPlay and DiAuto; their notices remain in the upstream
source. The installer enables CarLink's existing USB auto-confirm service without
copying its implementation into this repository.

## Factory launcher and earlier components

The proprietary Oshan launcher is distributed only as binary/source deltas for
the exact factory base pulled from the connected head unit. Complete APKs and
signing inputs remain private. Prior app identities and launcher deltas are
retained for older-journal recovery. Credit to
[Open Headunit](https://github.com/andreknieriem/open-headunit), the previous
projection app, and [DiPlay](https://github.com/shihabal3amri/DiPlay).

Screenshots are actual car captures. Names, icons and trademarks belong to their
respective owners. This project is not affiliated with Changan, Apple, Google or
upstream maintainers.
