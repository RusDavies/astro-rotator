# Open Source Tools and Comparable Workflows

Research date: 2026-07-15.

This note records tools and workflows that overlap with Astro Rotator's job: finding, explaining, and applying a compensation angle for altazimuth field rotation. The useful lesson is not "clone a stacker." It is where existing tools already solve pieces of the pipeline, where they assume good WCS or plate-solving state, and where Astro Rotator's evidence-report niche remains distinct.

## Findings

### Siril

- Source: https://siril.org/
- Related workflow: calibration, registration, stacking, enhancement, FITS/SER processing, scripts, and astrometry-aware processing.
- Useful pattern: Siril treats registration as part of a larger preprocessing sequence and exposes several registration modes for different image content, including star-based and object/body-based cases.
- Astro Rotator implication: keep output compatible with normal preprocessing workflows instead of becoming a whole stacking suite. A future CLI should be able to emit derotated FITS/TIFF plus an evidence report that can live beside Siril scripts.
- Notable boundary: Siril already stacks registered frames. Astro Rotator should focus on deriving and explaining the derotation evidence, especially mixed geometry/image/telemetry sources.

### DeepSkyStacker

- Sources: https://deepskystacker.free.fr/ and https://github.com/deepskystacker/DSS/releases
- Related workflow: deep-sky registration and stacking, with current open-source releases and practical handling of RAW/FITS/TIFF preprocessing.
- Useful pattern: preprocessing decisions such as scaling before registration affect whether faint images can be registered at all. Brightness and calibration handling are not just cosmetic when registration is the next step.
- Astro Rotator implication: derotation should record preprocessing assumptions that affect evidence quality, such as stretched/scaled inputs, calibration state, and whether image-derived angles came from linear or display-stretched data.
- Notable boundary: DeepSkyStacker is stacker-first and GUI-oriented. Astro Rotator remains library/CLI-first with explicit evidence provenance.

### Astroalign

- Sources: https://astroalign.quatrope.org/ and https://github.com/quatrope/astroalign
- Related workflow: WCS-free registration of stellar images by matching similar three-star asterisms and estimating an affine transformation.
- Useful pattern: it is directly aligned with the image-registration evidence provider, especially where metadata or WCS is missing.
- Astro Rotator implication: keep the dependency-free synthetic registration spike as the sign-convention reference, then evaluate Astroalign as an optional backend for real star fields. Its warnings matter: extended objects, sparse fields, crowded fields, and hot pixels can break or bias matching.
- Candidate future work: spike `astroalign` against synthetic PGM-derived arrays and an external real-image preview stack; compare angle, translation, failure diagnostics, and hot-pixel sensitivity against the current dependency-free estimator.

### Astropy `reproject`

- Source: https://reproject.readthedocs.io/
- Related workflow: resampling astronomical images into another WCS or celestial projection.
- Useful pattern: it is for WCS-trusted reprojection, not discovery of an unknown registration transform.
- Astro Rotator implication: `reproject` is a later output/resampling candidate when frame WCS is trusted or after plate solving has produced reliable WCS. It should not replace image registration for frames with missing or wrong WCS.
- Candidate future work: after FITS/WCS ingestion exists, spike `reproject` for WCS-preserving derotation and footprint reporting.

### KStars/Ekos, StellarSolver, and plate-solving workflows

- Source: https://kstars-docs.kde.org/en/user_manual/ekos-align.html
- Related workflow: image capture, plate solving, mount alignment, polar alignment, and orientation/framing feedback using StellarSolver, astrometry.net, ASTAP, or Watney.
- Useful pattern: production capture software already treats plate solving as the way to reconcile what the mount thinks with what the camera sees.
- Astro Rotator implication: plate-solving output should be a first-class evidence source once the CLI can ingest solver artifacts or FITS WCS headers. Also copy the failure-model thinking: bad position/scale priors can slow or break solving, and the report should expose those assumptions.
- Notable boundary: Ekos is acquisition and mount-control software. Astro Rotator should ingest its outputs before it tries to control anything.

### ASCOM Alpaca rotator model

- Sources: https://ascom-standards.org/api/ and https://ascom-standards.org/alpyca/alpaca.rotator.html
- Related workflow: device protocol and rotator abstraction, including mechanical angle, synced position angle, reverse behavior, and persistent sync offset.
- Useful pattern: the distinction between mechanical position and sky position angle is exactly the kind of offset/parity problem Astro Rotator must represent rather than hide.
- Astro Rotator implication: future mount/rotator telemetry should carry mechanical angle, synced/equatorial PA if known, sync method, reverse flag, and offset confidence as separate diagnostics. Do not reduce these to one unlabelled angle.
- Candidate future work: define an ASCOM/Alpaca telemetry import contract before implementing live device access.

### N.I.N.A. and capture automation

- Sources: https://github.com/isbeorn/nina and https://nighttime-imaging.eu/docs/master/site/advanced/meridianflip/
- Related workflow: Windows capture automation, sequence state, plate solve/framing workflows, meridian flip handling, rotator/camera/mount integration.
- Useful pattern: automation logs and FITS metadata can contain the session state that explains abrupt angle changes, flips, recentering, and image orientation changes.
- Astro Rotator implication: treat N.I.N.A. as an integration/log-import target, not an embedded dependency. Future metadata readers should preserve capture-program fields and event boundaries that explain discontinuities.

### PixInsight StarAlignment

- Source: https://www.pixinsight.com/tutorials/sa-distortion/index.html
- Related workflow: mature star-based registration, distortion correction, and deep-sky image alignment.
- Useful pattern: high-quality registration workflows expose transformation models and diagnostics beyond "angle was found."
- Astro Rotator implication: the report should eventually include transform model class, residuals, inlier counts, rejected matches, and whether the angle is a pure rotation or part of a wider affine/distortion fit.
- Notable boundary: PixInsight is proprietary, so it is a workflow reference rather than open-source code to reuse.

### AutoStakkert and WinJUPOS-style planetary derotation

- Sources: https://www.autostakkert.com/ and https://jupos.org/gh/download.htm
- Related workflow: lucky imaging and planetary rotation compensation.
- Useful pattern: "derotation" can mean planetary surface rotation, channel-time alignment, or field rotation. These are different physical problems.
- Astro Rotator implication: docs and CLI help should use precise wording such as "field derotation" or "altazimuth field-rotation compensation" to avoid implying planetary derotation support.
- Notable boundary: planetary video derotation is not an MVP target.

## Design Implications

- Keep the product boundary narrow: angle evidence, reconciliation, derotation transform, and reportability.
- Treat image registration backends as swappable evidence providers. The current dependency-free estimator remains the deterministic test baseline; Astroalign is the first serious optional backend candidate.
- Treat WCS reprojection separately from WCS-free registration. `reproject` belongs after WCS is trusted or plate-solving output exists.
- Preserve provenance-rich diagnostics. Existing tools often succeed or fail based on star extraction thresholds, bad priors, image scaling, calibration state, hot pixels, and mount/capture state. Astro Rotator's report should capture those reasons.
- Prefer import/export compatibility over direct control. KStars/Ekos, N.I.N.A., ASCOM/Alpaca, Siril, and DeepSkyStacker are workflow neighbors. Direct live integration should wait until the CLI/core evidence path is solid.

## Near-Term Recommendations

1. Keep the next implementation item focused on a minimal `derotate` CLI skeleton over current frame catalog, evidence, and report modules.
2. Add an `astroalign` backend spike after the CLI has a clear evidence-provider interface and the current synthetic registration path is still green.
3. Add a WCS/plate-solving import spike before any serious `reproject` integration.
4. Document transform diagnostics in the report schema before rotating real output frames, including inlier counts, residuals, transform model, preprocessing state, and whether the angle is selected, fallback, or advisory evidence.
