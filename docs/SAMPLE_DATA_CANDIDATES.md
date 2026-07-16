# Sample Data Candidates

Candidate external data sources for derotation and registration testing. Do not commit raw downloaded data until license/provenance and size handling are explicit.

## Recommended Starting Set

### Static Tripod Milky Way Stack - PhotographingSpace

- URL: https://www.photographingspace.com/homework-download-stack-data/
- Data shape: 11 Canon 5D Mark III raw frames, 24mm lens, 15 second exposures, static tripod.
- Why it matters: Good candidate for image-to-image rotation/translation registration because the sky moves relative to a fixed camera between frames. It is not telescope/altaz data, but it should exercise rotation estimation in a real noisy DSLR stack.
- Provenance/licensing: Author intentionally provides download links for practice and asks users to share results. Treat as external test data; do not redistribute in this repository unless permission/license is clarified.
- Initial fit: Best first real-world registration smoke test.
- Inspection status: candidate for external local smoke testing only; do not commit raw files.

### AstroPix Practice Files - Jerry Lodriguss

- URL: https://www.astropix.com/html/processing/practice_files.html
- Data shape: Several Canon CR2 light-frame sets: M31, M42, M45, M46/M47, M13, plus darks and bias frames.
- Why it matters: Good DSLR raw workflow coverage with multiple light frames and calibration frames.
- Provenance/licensing: Page says files may be downloaded for practice and results may be posted with credit/link. Treat as external test data; do not redistribute in this repository unless permission/license is clarified.
- Initial fit: Useful for metadata parsing and general registration; probably less useful for field-rotation stress if captured on an equatorial setup.

### Siril Tutorial Data - M8/M20

- URL: https://siril.org/tutorials/tuto-scripts/
- Data shape: Tutorial archive with 15 lights, 15 darks, 15 flats, and 15 bias/dark-flat style frames; DSLR raw or astronomy camera FITS workflows are discussed.
- Why it matters: Canonical open-source astronomy-processing tutorial data with clear folder organization and stacking workflow.
- Provenance/licensing: Tutorial provides an archive for learning. License for the image data is not explicit from the page; treat as external test data only.
- Initial fit: Useful for FITS/raw pipeline shape and compatibility expectations.

### AstroCompress GBI-16-4D - SDSS Time-Series FITS

- URL: https://huggingface.co/datasets/AstroCompress/GBI-16-4D
- Data shape: FITS cubes containing repeated SDSS Stripe 82 observations over time and five filters; tiny split is available.
- Why it matters: MIT dataset wrapper with underlying CC-4.0 data, FITS-native, time-series shaped, and programmatically accessible.
- Provenance/licensing: Hugging Face dataset card lists MIT license and says underlying data is CC-4.0.
- Initial fit: Best public/reproducible candidate for automated tests that need FITS/time-series data, though not hobbyist altaz data and full set is huge.

### NASA FITS Sample Files

- URL: https://fits.gsfc.nasa.gov/fits_samples.html
- Data shape: Small sample FITS files from multiple sources and public archives.
- Why it matters: Good for parser tests and edge-case FITS handling.
- Provenance/licensing: NASA/HEASARC sample page; sample files come from various public archives and may not all conform to latest FITS recommendations.
- Initial fit: Good for metadata and file-format tests, not rotation-stack tests.

## Gap

None of the initial candidates is a perfect altaz telescope field-rotation stack with known location, timestamps, target, and mount/sensor telemetry. We still need either:

- user-provided or community-provided altaz capture sequences with permission;
- a small synthetic star-field generator with known rotation angles;
- or both, which is the sensible answer because apparently reality remains inconvenient.
