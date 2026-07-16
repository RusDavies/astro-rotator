# Security Policy

## Supported Versions

Astro Rotator is pre-alpha. Security fixes currently target the `main` branch.

## Reporting a Vulnerability

Please report suspected vulnerabilities privately through GitHub's private
vulnerability reporting for this repository when available, or contact the
maintainer directly.

Do not publish proof-of-concept exploits, private image metadata, location data,
or raw frame samples while a report is being triaged.

## Security Scope

In scope:

- unsafe parsing of supported image formats;
- unsafe filesystem behavior in CLI input/output handling;
- dependency vulnerabilities affecting normal installation or execution;
- report output that unexpectedly exposes sensitive frame metadata.

Out of scope for security reporting:

- expected exposure of metadata that the user explicitly asks the tool to report;
- unsupported file formats;
- local denial-of-service from intentionally huge or malformed files unless the
  behavior is surprising for normal CLI use.

## Data Handling Notes

Astrophotography frames and reports can contain private timestamps, locations,
equipment details, and target history. Treat shared frames, generated reports,
and sidecar metadata as potentially sensitive.
