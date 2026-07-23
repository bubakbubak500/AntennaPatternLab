# Security policy

## Supported versions

Security fixes are provided for the latest published release.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting feature:

1. open the repository's **Security** tab;
2. select **Advisories**;
3. choose **Report a vulnerability**.

Do not open a public issue for a suspected vulnerability and do not include
credentials, private station data, signing files, or certificate passwords in any
report.

Include the affected version, impact, reproduction steps, and any suggested
mitigation. You should receive an initial response within seven days.

## Release integrity

Official Windows releases are published only through GitHub Releases. The
current application and installer are not Authenticode-signed. Release checksums
and GitHub build-provenance attestations are published, and the in-app updater
verifies the installer's SHA-256 before making it available to launch. Windows
may show an unknown-publisher warning until a trusted signing certificate is
introduced.
