# Release process

Official releases are created by `.github/workflows/release.yml`.

No release secrets are currently required. Packages are intentionally published
without an Authenticode signature until a trusted code-signing certificate is
available. The release page and application clearly disclose this.

## Create a release

1. Update the version in `pyproject.toml`.
2. Ensure the Inno Setup definition and application package use the same version.
3. Merge the version change through an approved pull request.
4. Create and push a tag named `vMAJOR.MINOR.PATCH`.
5. The release workflow verifies that the tag matches the project version.
6. GitHub Actions runs tests, builds the application and installer, confirms that
   the installer is unsigned, creates the update manifest and checksums, records
   GitHub build-provenance attestations, and publishes a GitHub Release.

The update manifest is always available at:

`https://github.com/bubakbubak500/AntennaPatternLab/releases/latest/download/release-manifest.json`

When Authenticode signing is added later, keep the same asset names and manifest
URL so installed applications remain on the same update channel. Never commit a
PFX file or its password.
