# Release process

Official releases are created by `.github/workflows/release.yml`.

## Required repository secrets

- `WINDOWS_SIGNING_CERTIFICATE_BASE64`: a Base64-encoded, password-protected PFX
  code-signing certificate;
- `WINDOWS_SIGNING_CERTIFICATE_PASSWORD`: the PFX password.

The certificate must support Windows code signing and chain to a certificate
authority trusted by supported Windows versions. Never commit the PFX or password.

## Create a release

1. Update the version in `pyproject.toml`.
2. Ensure the Inno Setup definition and application package use the same version.
3. Merge the version change through an approved pull request.
4. Create and push a signed or annotated tag named `vMAJOR.MINOR.PATCH`.
5. The release workflow verifies that the tag matches the project version.
6. GitHub Actions runs tests, builds the application, signs the application EXE,
   builds and signs the installer and uninstaller, verifies Authenticode, creates
   the update manifest and checksums, and publishes a GitHub Release.

The update manifest is always available at:

`https://github.com/bubakbubak500/AntennaPatternLab/releases/latest/download/release-manifest.json`

If certificate renewal is required, replace the two secrets before creating a
release. Existing releases remain timestamp-valid after the certificate expires,
provided the timestamp was created while the certificate was valid.
