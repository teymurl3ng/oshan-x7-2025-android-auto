# Third-party software and modifications

The repository's original installer, tests and documentation use the root
[MIT license](LICENSE). That license does not replace upstream software's
licenses or the rights in the car's factory applications.

## CarLink

- Project: [F-e-n-y-x/CarLink](https://github.com/F-e-n-y-x/CarLink).
- Reviewed release and corresponding source: [v1.0.7](https://github.com/F-e-n-y-x/CarLink/tree/v1.0.7).
- Upstream license: [GNU Affero General Public License v3.0](https://github.com/F-e-n-y-x/CarLink/blob/v1.0.7/LICENSE);
  an unchanged copy is included in [LICENSES/CarLink-AGPL-3.0.txt](LICENSES/CarLink-AGPL-3.0.txt).
- CarLink combines upstream DiPlay and DiAuto components; retain their own
  notices and licensing from the corresponding source tree.

This project does not publish a complete CarLink APK. Its binary delta applies
to the exact official 1.0.7 APK locally. The only application-content change is
the manifest's declared signature permission:

```diff
- <permission android:name="com.andrerinas.openheadunit.permission.NAVIGATION_UPDATE" android:protectionLevel="signature" />
+ <permission android:name="com.carlink.oshanx7trialapp.permission.NAVIGATION_UPDATE" android:protectionLevel="signature" />
```

The modified CarLink content retains the upstream AGPL-3.0 licensing. The
complete corresponding upstream source is linked above; this declaration is
in `vendor/diauto/app/src/main/AndroidManifest.xml`. The content modification
is documented and reproducible with
[tools/prepare_carlink_coexist.py](tools/prepare_carlink_coexist.py). The APK is
aligned and signed separately using a private local key. That new signing
identity is why official APK updates cannot install directly over this variant.
All other APK entry payloads, including executable code and assets, are unchanged.

Exact original/output hashes, patch identity and verification are in
[the CarLink trial guide](docs/carlink-trial.md). No runtime authentication
credentials are extracted or published.

## Other upstream and factory components

- [DiPlay](https://github.com/shihabal3amri/DiPlay): CarPlay implementation
  used by CarLink; its standalone APK was researched but not installed here.
- [Open Headunit](https://github.com/andreknieriem/open-headunit): the previous
  receiver; this repo downloads the official pinned APK when reproducing that
  historical setup. Its license is not replaced by this project's MIT license.
- The Oshan factory launcher is proprietary third-party software. The repo
  ships binary/source deltas for the exact owner-supplied factory base, not a
  complete factory or modified APK. Full APKs and signing inputs remain private.

Screenshots are actual reference-car captures of the identified applications.
Names, icons and trademarks belong to their respective owners. This project
is not affiliated with Changan, Apple, Google or the upstream app maintainers.
