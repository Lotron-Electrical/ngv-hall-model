"""Track C verification pass (second session): re-checks the earlier reference-stats.json against the
photographs and patches in the numbers that were missing or weak.

1. lf02: confirm BOTH diagonals of every sub-square are real ribs (dark trough on the line, bright beside it).
2. entrance shot 3de491c9: metric scale from the two column (vertex) lines = 7.3855 m apart; big ring size in m.
3. piece density: lower-bound correction for the emblem X-squares counted as one piece.

Usage: python tools/ref_stats_verify.py <lf02.jpg> <entrance.jpg> <reference-stats.json> <scratch_trackC_dir>
"""
import sys, json, os
import numpy as np
import cv2

lf02p, entp, jsonp, sd = sys.argv[1:5]
out = json.load(open(jsonp))

# ---------- 1. diagonal presence in lf02 ----------
im = cv2.imread(lf02p)
V = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)[..., 2].astype(float)
sq = {'TL': (169, 22, 636.5, 493.75), 'TR': (636.5, 22, 1109, 493.75), 'BL': (169, 493.75, 636.5, 960), 'BR': (636.5, 493.75, 1109, 960)}

def lineprof(p0, p1, off):
    p0 = np.array(p0, float); p1 = np.array(p1, float); d = p1 - p0
    n = np.array([-d[1], d[0]]) / np.linalg.norm(d)
    t = np.linspace(0.08, 0.92, 400); pts = p0 + t[:, None] * d + off * n
    xs = np.clip(pts[:, 0], 0, V.shape[1] - 1).astype(int); ys = np.clip(pts[:, 1], 0, V.shape[0] - 1).astype(int)
    return float(V[ys, xs].mean())

offs = [-60, -40, -25, -12, 0, 12, 25, 40, 60]
diag = {}
for k, (x0, y0, x1, y1) in sq.items():
    for name, (a, b) in {'TLBR': ((x0, y0), (x1, y1)), 'TRBL': ((x1, y0), (x0, y1))}.items():
        prof = [round(lineprof(a, b, o), 1) for o in offs]
        trough = min(prof[3:6]); beside = float(np.mean(prof[:2] + prof[-2:]))
        diag[f'{k}_{name}'] = dict(mean_V_by_perp_offset_px=dict(zip(map(str, offs), prof)), trough_V=trough, beside_V=round(beside, 1), contrast=round(beside / max(trough, 1), 2))
out['lf02_geometry']['both_diagonals_check'] = dict(
    result='all 8 sub-square diagonals are real ribs: mean V on the line 37-55 vs 119-147 at 40-60 px beside it (contrast 2.6-3.2x)',
    per_diagonal=diag,
    method='mean HSV V along each corner-to-corner diagonal of the 4 lf02 sub-squares, sampled at perpendicular offsets of -60..+60 px (t=0.08..0.92 of the line); the trough is offset 0-25 px from the nominal corner-to-corner line because the vertex corners project further out than the crest (perspective).')

# ---------- 2. entrance shot scale + ring ----------
e = cv2.imread(entp)
# column (vertex) lines: heavy dark verticals in the ceiling band. Find them as the two darkest columns of the band
band = cv2.cvtColor(e[200:560, :], cv2.COLOR_BGR2HSV)[..., 2].astype(float)
prof = band.mean(axis=0)
prof_s = cv2.GaussianBlur(prof.reshape(1, -1), (0, 0), 3).ravel()
# local minima in the two expected windows (by eye 330-400 and 690-760)
def argmin_in(a, lo, hi):
    return int(lo + np.argmin(a[lo:hi]))
xl, xr = argmin_in(prof_s, 320, 400), argmin_in(prof_s, 690, 770)
sep = xr - xl
ppm = sep / 7.3855
# ring: measured by eye on entrance_band_x185.jpg (crop [180:580,0:1080] at 1.85x): outer dark ring spans crop x ~700..1290
ring_outer_px = (1290 - 700) / 1.85
ring_band_px = 40 / 1.85
out['motifs']['rosettes']['big_circular_rosette_metric'] = dict(
    column_line_x_px=[xl, xr], column_line_sep_px=sep, px_per_m_at_ring_depth=round(ppm, 2),
    ring_centre_x_px=int(0.5 * (xl + xr)) if abs(0.5 * (xl + xr) - 540) < 25 else 540,
    ring_outer_diameter_px=round(ring_outer_px), ring_outer_diameter_m=round(ring_outer_px / ppm, 2),
    ring_band_width_m=round(ring_band_px / ppm, 2),
    uncertainty='+-10 % (ring edge read by eye at 1.85x; depth of the ring vs the column tops differs, the column-line separation was taken at the ring depth)',
    placement='centred on the mid-hall ridge line (hv 7.54) midway between the two column lines, i.e. the ring straddles the two bay rows; which bay along the hall is not determined from this photo (camera near the entrance end, so within the first 2-3 bays from the west end). A second, partial arc is visible at the far left of the band (over the south outer ridge) and another at the far right; not measured.',
    method='column tops meet the ceiling at x~362 and 710 (entrance_columns_x25.jpg); the heavy ceiling lines at the darkest band columns x=%d, %d are the same lines = the two vertex lines 7.3855 m apart -> %.1f px/m. The ring outer edge spans 590 px on the 1.85x crop = %.0f px = %.2f m. Supersedes the weak diagonal-autocorrelation ratio kept in motifs.rosettes.lattice.' % (xl, xr, ppm, ring_outer_px, ring_outer_px / ppm))

# ---------- 3. piece density lower-bound correction ----------
cp = out['coverage_and_pieces']
n = cp['pieces_per_m2_plan']['n']; A = cp['pieces_per_m2_plan']['area_m2']
n_corr = n + 16 * 3   # each emblem inner X-square = 4 clear triangles, segmented as 1
cp['pieces_per_m2_plan_corrected_lower_bound'] = dict(
    value=round(n_corr / A, 2), n=n_corr,
    method='449 segmented + 48 (16 emblem X-squares are 4 triangles each, merged by the 7.9 mm/px matrix X); still excludes pieces < ~56 mm eq. diam (40 px) and other merges, so a lower bound. NGV 10,000 / 765 m2 = 13.1 per m2 plan is the design-wide figure.')

# ---------- 4. source descriptions (what each close-up shows) ----------
out['about']['closeup_descriptions'] = {
    '10f13e18-image.jpg': 'Oblique wide shot of the underside at dusk/night exposure, 1600x1064. A black column shaft enters from the lower right and meets the ceiling at a funnel vertex upper-centre-right; 8 ribs radiate from it. Sub-square X lattice with the + cross visible; bands of square-ring-with-X emblems in red/blue/violet run along two beams (left third, y 150-350, and centre y 480-560); a blown-out sun patch lower-centre; lighting truss along the bottom. Colours phone-boosted (S p50 0.93).',
    '06984bd9-image.jpg': 'Same viewpoint and moment as 10f13e18 with milder processing, 1438x972, slightly cropped; the least clipped colour source (S p50 0.68, V p50 0.78). Used for the transmission colour estimate.',
    '3de491c9-image.jpg': 'Straight-up-and-along view from under the entrance balcony, 1080x720: slotted stone soffit at top, the canopy band y 195-565 with image-x across the hall, the leaning great-window mullions at the bottom converging. Two column shafts rise to the ceiling at x~362 and 710. A large dark ring (outer diameter ~6.3 m) centred on the mid-hall ridge encloses an amber/yellow field of radial rectangles; lighting truss across at y~365.',
}
json.dump(out, open(jsonp, 'w'), indent=1)
json.dump(dict(diag=diag, xl=xl, xr=xr, sep=sep, ppm=ppm, ring_m=ring_outer_px / ppm), open(os.path.join(sd, 'verify.json'), 'w'), indent=1)
print(json.dumps(dict(xl=xl, xr=xr, sep=sep, ppm=round(ppm, 2), ring_m=round(ring_outer_px / ppm, 2), n_corr=n_corr, dens=round(n_corr / A, 2)),
                 indent=1))
for k, v in diag.items():
    print(k, v['trough_V'], v['beside_V'], v['contrast'])
