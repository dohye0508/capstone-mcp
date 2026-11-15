# Round 3: supported equal-width double-slit analysis

## Finding and outcome

DEFECT-DIFF10 originally treated interference minima as single-slit diffraction minima and could report a substantially incorrect slit width. Round 2 contained that defect by rejecting double-slit analysis. Round 3 supports a measured equal-width Fraunhofer double-slit profile and estimates slit width `a` and center separation `d` independently. This does not claim support for every optical apparatus or arbitrary double-slit intensity distribution.

## Physical model and required data

The fitted model is

`I(x) = B + A [sin(beta)/beta]^2 cos(alpha)^2`,

where `beta = pi*a*sin(theta)/lambda`, `alpha = pi*d*sin(theta)/lambda`, and `sin(theta) = (x-x0)/hypot(L, x-x0)`.

Inputs must describe two equal-width, parallel rectangular apertures with coherent monochromatic illumination and a linear detector in the far field. Wavelength and screen distance are caller-supplied experimental quantities (existing recipe defaults remain 650 nm and 1 m). Their calibration and uncertainty cannot be inferred from intensity samples. The model assumes a spatially constant background; unequal slit transmission/width, finite-source coherence, Fresnel propagation, detector saturation and variable background require other models. The code does not infer or certify that the apparatus is in the Fraunhofer regime; the experiment must establish propagation distance large compared with the relevant aperture-size-squared/wavelength scale.

Supported geometry has `0.02 < a/d < 0.98`. The scan must include at least 1.05 orders of the diffraction envelope on both sides of the inferred center, resolving both first envelope zeros. At least eight samples per interference fringe are required. Input must contain 41–20,000 finite paired samples with strictly increasing positions. These conservative requirements prevent interpreting a central fringe alone as a resolved slit width.

## Deterministic algorithm and limitations

The nearest minima around the strongest observed peak initialize fringe period. Six width/separation seeds are refined by bounded multiscale coordinate descent over ratio, period and center. Amplitude and background are solved analytically by linear least squares at each candidate. The exact angular coordinate above avoids silently applying a small-angle conversion at the endpoints.

Each seed performs at most 160 sweeps of six coordinate candidates. Fitting uses at most 2,048 uniformly distributed input indices; the retained spacing must still resolve eight samples per fringe, otherwise the caller must supply a resolved central region. Final RMS, amplitude and background are evaluated using **all** original samples. Search cost is therefore bounded independently of the 20,000-row input maximum, apart from linear input validation and final residual evaluation. This is a bounded multistart local optimizer, not a proof of the global optimum. Strong noise, mislabeled center, aliasing or a different optical model may be rejected even when a more specialized fitter could recover parameters.

Acceptance requires normalized RMS no greater than 3% of fitted modulation amplitude, observed bilateral envelope support, positive modulation and no substantially negative fitted background. These are explicit deterministic acceptance thresholds, not confidence intervals or calibrated uncertainty estimates. A failed fit never substitutes nominal slit dimensions. Unrepresentable geometry and unreliable enormous phase arguments raise ValueError, translated by the recipe into `status="failed"`.

## Public result behavior

`SlitDiffractionRecipe.analyze` now accepts `slit_type="double_slit"` with existing `positions_mm` or top-level `positions_m` and intensity arrays. Acquisition output continues to store millimetre positions in its `data` payload. No request schema changes or new dependency are introduced. Explicit zero wavelength/distance is no longer replaced by a default.

Successful double-slit details include:

- `derived_slit_width_mm`, `derived_slit_separation_mm`;
- `central_maximum.position_mm`, fitted `amplitude` and `background`;
- `normalized_rms`, `model`, `wavelength_nm`, `screen_distance_m`, `slit_type`.

There is no invented nominal-error percentage or identification of interference minima as envelope minima. Round-2 clients that always expected double-slit failure should accept a completed result when these conditions are met. Single-slit result fields remain separate and unchanged. Unsupported slit type names fail explicitly.

## Independent validation

`tests/test_double_slit.py` computes reference intensity by numerically integrating complex phase over two rectangular apertures (128 aperture quadrature points). It does not call the production sinc/cos evaluator to generate the reference. Three wavelength/geometry combinations (450, 532 and 650 nm) verify recovered slit width to 0.3% and separation to 0.1%. Further tests cover constant background/amplitude, off-grid center, millimetre/metre recipe input, deterministic small noise, missing envelope, undersampled/flat input, model mismatch, zero/nonfinite geometry, extreme arithmetic and bounded search at 20,000 samples. Numerical tolerances describe these fixtures only, not guaranteed experimental uncertainty.

No GUI, sensor, optical bench, or live acquisition was used. Real detector calibration and physical regime validity remain experimental prerequisites; they are not an unresolved implementation of the original wrong-minimum formula.
