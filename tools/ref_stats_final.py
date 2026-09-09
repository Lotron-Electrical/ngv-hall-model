"""Track C final: assemble reference-stats.json from the step outputs, plus a few last measurements
(lf02 per-quadrant brightness, piece orientation vs ribs, rim-highlight metric on the 4K still,
lattice pitch vs rosette ring in the entrance shot, cu2-based transmission estimate).

Usage: python tools/ref_stats_final.py <scratch_trackC_dir> <lf02.jpg> <b001.jpg> <entrance.jpg> <out_json>
"""
import sys, os, json
import numpy as np
import cv2

sd, lf02p, balcp, entp, outp = sys.argv[1:6]
J = lambda n: json.load(open(os.path.join(sd, n)))
grid, P, D, X, G, M = J('grid.json'), J('pieces.json'), J('derived.json'), J('extra.json'), J('geomcheck.json'), J('more.json')
mm = P['mm_per_px']; ppm = P['px_per_m']
pieces = P['pieces']
sq = P['squares']

# ---------- lf02 per-quadrant (each quadrant is a sub-square of a DIFFERENT bay) ----------
quad = {}
for k, (x0, y0, x1, y1) in sq.items():
    ps = [p for p in pieces if x0 <= p['cx'] < x1 and y0 <= p['cy'] < y1]
    col = [p for p in ps if not (p['sat'] < 0.25 and p['val'] > 0.78)]
    clr = [p for p in ps if (p['sat'] < 0.25 and p['val'] > 0.78)]
    quad[k] = dict(n=len(ps), coloured_val_p50=float(np.median([p['val'] for p in col])),
                   coloured_sat_p50=float(np.median([p['sat'] for p in col])),
                   clear_share_count=len(clr) / len(ps), clear_clipped_frac=float(np.mean([p['clipped_frac'] > 0.5 for p in clr])))

# ---------- piece orientation relative to the ribs (lf02 mask) ----------
mask = np.load(os.path.join(sd, 'mask.npy'))
n, lab, st, ce = cv2.connectedComponentsWithStats(mask, connectivity=4)
angs, areas = [], []
for i in range(1, n):
    x, y, w, h, a = st[i]
    if a < 40:
        continue
    comp = (lab[y:y + h, x:x + w] == i).astype(np.uint8)
    cnt, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cnt, key=cv2.contourArea)
    (rx, ry), (rw, rh), ang = cv2.minAreaRect(c)
    if max(rw, rh) / max(1, min(rw, rh)) < 1.15:
        continue   # near-square: orientation meaningless
    if rw < rh:
        ang += 90
    angs.append(ang % 90); areas.append(a)
angs = np.array(angs); areas = np.array(areas)
axis = (angs <= 12) | (angs >= 78)
diag = np.abs(angs - 45) <= 12
orient = dict(n_elongated=int(len(angs)), axis_aligned_frac=float(axis.mean()), diagonal_aligned_frac=float(diag.mean()),
              other_frac=float(1 - axis.mean() - diag.mean()), area_weighted_axis=float(areas[axis].sum() / areas.sum()),
              area_weighted_diag=float(areas[diag].sum() / areas.sum()),
              method='minAreaRect long-axis angle mod 90 for lf02 pieces with aspect >= 1.15; axis = within 12 deg of the ridge/cross '
                     'directions, diagonal = within 12 deg of 45 deg (the panel diagonals). Uniform random would give 0.27 / 0.27.')

# ---------- rim highlight metric on the 4K balcony still ----------
bl = cv2.imread(balcp)[0:1100, 400:2160]
hsv = cv2.cvtColor(bl, cv2.COLOR_BGR2HSV); V = hsv[..., 2]
rgb = cv2.cvtColor(bl, cv2.COLOR_BGR2RGB).astype(np.float32)
Lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
m = cv2.morphologyEx((V > 70).astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
n, lab, st, ce = cv2.connectedComponentsWithStats(m, connectivity=4)
dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
rimmax, rimw, lowedge = [], [], []
for i in range(1, n):
    x, y, w, h, a = st[i]
    if a < 1500 or x <= 2 or y <= 2 or x + w >= bl.shape[1] - 2 or y + h >= bl.shape[0] - 2:
        continue
    comp = lab == i
    px = rgb[comp]
    if (px.max(axis=1) >= 250).mean() > 0.1:
        continue
    med = np.median(px[dt[comp] >= 8], axis=0) if (dt[comp] >= 8).sum() > 50 else None
    if med is None:
        continue
    hs = cv2.cvtColor(np.uint8([[med]]), cv2.COLOR_RGB2HSV)[0, 0]
    if hs[1] / 255 < 0.25:
        continue
    d = dt[comp]; l = Lum[comp]
    inner = l[d >= 8].mean()
    ring = l[(d >= 1) & (d < 5)]
    rimmax.append(float(np.percentile(ring, 95) / inner))
    # fraction of the rim ring brighter than 1.15 x interior (glinting chipped facets)
    rimw.append(float((ring > 1.15 * inner).mean()))
look_extra = dict(n=len(rimmax), rim_p95_over_interior_p25_p50_p75=[float(np.percentile(rimmax, q)) for q in (25, 50, 75)],
                  rim_bright_fraction_p25_p50_p75=[float(np.percentile(rimw, q)) for q in (25, 50, 75)],
                  method='b001 unclipped coloured pieces (>1500 px): p95 luminance of the 1-5 px edge ring over the interior mean '
                         '(dt>=8 px), and the share of that ring above 1.15 x interior. Rim glints are local, not a continuous bevel line.')

# ---------- entrance shot: lattice pitch vs rosette ring ----------
ent = cv2.imread(entp)
c = ent[200:560, 250:850]
V = cv2.cvtColor(c, cv2.COLOR_BGR2HSV)[..., 2].astype(np.float32)
dark = 1.0 - V / 255.0
dark -= dark.mean()
# autocorrelation along the 45-degree directions (the X lattice): rotate 45 deg and take the column profile
Mr = cv2.getRotationMatrix2D((c.shape[1] / 2, c.shape[0] / 2), 45, 1.0)
rot = cv2.warpAffine(dark, Mr, (c.shape[1], c.shape[0]))
prof = rot[100:260, 150:450].mean(axis=0)
prof -= prof.mean()
ac = np.correlate(prof, prof, 'full')[len(prof) - 1:]
ac /= ac[0]
pk = [i for i in range(8, len(ac) - 2) if ac[i] > ac[i - 1] and ac[i] >= ac[i + 1] and ac[i] > 0.1]
lattice = dict(diag_line_pitch_px_candidates=pk[:4], autocorr_values=[float(ac[i]) for i in pk[:4]],
               rosette_ring_by_eye_px=dict(centre_crop_xy=[292, 192], outer_diameter_px=165, note='entrance_centre_x2.jpg coords / 2'),
               method='dark-line autocorrelation along the 45-deg diagonals of the central crop of 3de491c9 (no metric scale in this photo; '
                      'the rosette is given only relative to the local diagonal pitch)')

# ---------- transmission estimate from the least-clipped close-up (cu2) ----------
def srgb_to_lin(cc):
    cc = np.asarray(cc, np.float64) / 255.0
    return np.where(cc <= 0.04045, cc / 12.92, ((cc + 0.055) / 1.055) ** 2.4)
fam2 = M['closeup_colour']['closeup2_06984bd9']['families']
lin = {f: srgb_to_lin(v['median_srgb']) for f, v in fam2.items() if v.get('count', 0) and f != 'clear'}
k2 = max(max(v) for f, v in lin.items() if f != 'pink') / 0.62
trans2 = {f: [float(min(0.9, x / k2)) for x in v] for f, v in lin.items()}
trans2['clear'] = [0.85, 0.85, 0.85]

# ---------- assemble ----------
S = D['sizes']; C = D['colour']; L = D['look']; SY = D['symmetry']
heavy_mm = P['heavy_w_px'] * mm; light_mm = P['light_w_px'] * mm
main_mm = P['main_diag_w_px'] * mm; anti_mm = P['anti_diag_w_px'] * mm
cov = P['coverage']
out = {
 'about': {
  'sources': {
   'lf02.jpg': 'Rory Hyde 2004 straight-up shot, 1280x990, 2x2 full 3.7 m sub-squares + partial strips; heavily overexposed (clear pieces clipped, coloured V p50 0.99)',
   '10f13e18-image.jpg': 'close-up 1, 1600x1064, oblique, night/dusk exposure, phone-processed (S p50 0.93); a column crosses the right third; red/purple emblem bands, the sun-lit clear patch mid-lower',
   '06984bd9-image.jpg': 'close-up 2, 1438x972, the same viewpoint as close-up 1 but a different (milder) processing: S p50 0.68, V p50 0.78, the least clipped source; used for the transmission colour estimate',
   '3de491c9-image.jpg': 'entrance shot, 1080x720, looking up along the hall from the great-window end: stone soffit above, whole ceiling in perspective, two big circular rosettes in the central bays, lighting truss across',
   'b0cefe7f-image.webp': 'whole-hall oblique 4199x5249 by day from the balcony end; used for facet brightness',
   'gh03.jpg / bc0.jpg': 'wide oblique shots used for the clear/coloured ratio',
   'balcony4k b001.jpg': "Lloyd's 4K phone still from the balcony, 2160x3840; top strip used for the piece look (pieces 48-106 px eq. diam.)",
  },
  'coordinate_note': 'all lf02 pixel coordinates are in the 1280x990 image; x right, y down. The heavy crossing is at (636.5, 493.75).',
 },
 'lf02_geometry': {
  'member_identification': {
   'result': 'heavy members (x=636.5 and y=493.75, both 60 px wide) are BAY RIDGE beams in both directions; light members (x=169, 1109; y=22, 960; 27-33 px) are the 3.7 m cross members; the heavy crossing is a bay corner (crest node), the four light-light crossings at the photo corners are funnel vertices (column heads). Each of the four sub-squares in lf02 belongs to a different bay.',
   'evidence': [
    'both heavy members have the same width (60 vs 61 px) and darkness; the pattern is mirror-symmetric about both (mask NCC 0.80 / 0.82 vs 0.35 / 0.41 unmirrored)',
    'straightness (ref_stats_geomcheck.py): the two heavy members deviate < 1.1 px from straight; all four light members bow 7-16 px TOWARD the image centre at their middle (v0 +15.6, v2 -12.5, h2 -11.3, h0 +6.9 px). A member that stays at one height projects straight; a cross member rises 0.86 m from the vertex to the ridge midpoint and projects with a kink toward the principal point, expected ~30-40 px; the observed sign matches, magnitude is about half (trace noise rms 7-12 px).',
    'the 60 px = 477 mm heavy width matches the 450 mm crest band (2 x 0.225 m) in the canopy relief model; the light members at 231-260 mm are too narrow for the ridge',
    'square-ring-with-X emblems cluster in the two triangles that touch the heavy members of every sub-square (a band along the crest), as in gh03 where the emblem band runs along the crest beam away from the column head; the radial fans of clear pieces sit at the light-light corners = around the column heads (gh03_colhead_crop.jpg)',
   ],
   'conflict': 'the task brief called the heavy vertical the 3.7 m cross; the measurements above say it is a ridge. Consumers of the mirror-symmetry statement must use the assignment given here.',
  },
  'scale': dict(sub_square_pitch_px=P['pitch_px'], px_per_m=ppm, mm_per_px=mm,
                method='mean of the 4 member spacings (467.5, 472.5, 471.75, 466.25 px) / 3.7035 m (mean of PU/2 and PV/2). Perspective: the vertex corners of each sub-square are 0.86 m lower than the crest, so the local scale varies ~+-3 % across a sub-square; widths measured at the image centre (ridges) carry the crest scale.'),
  'members_px': dict(vertical=[(m_['centre'], m_['w_p50']) for m_ in grid['vertical']],
                     horizontal=[(m_['centre'], m_['w_p50']) for m_ in grid['horizontal'] if m_['w_p50'] > 20],
                     note='(centre px, median dark-run width px); horizontals at 246.5 and 736.5 in grid.json are emblem rows, not beams'),
 },
 'rib_widths_mm_as_seen_from_below': {
  'bay_ridge_beam': dict(value=round(heavy_mm), p25_p50_p75_px=[57, 60, 61], method='median dark run (V<72 % darkness) across the heavy members at 2 px steps; both pass through the image centre so no side face is visible: this is the soffit width'),
  'cross_member_3p7m': dict(value=round(light_mm), p25_p50_px=[(v['p25'], v['p50']) for k_, v in P['axis_w'].items() if k_ in ('v0', 'v2', 'h0', 'h2')], method='same, on the four light members (467 px off-centre, so the beam side face adds up to ~d*0.28 to the dark width, d = beam depth; true soffit is narrower, likely 150-200 mm)'),
  'diagonal_main_hip': dict(value=round(main_mm), method='median over the 4 vertex-to-corner diagonals (through the image centre)'),
  'diagonal_anti': dict(value=round(anti_mm), method='median over the 4 edge-midpoint diagonals'),
  'diagonal_mean': round(0.5 * (main_mm + anti_mm)),
  'per_line_px_p50': [(d['square'], d['kind'], d['p50']) for d in P['diag_lines']],
 },
 'coverage_and_pieces': {
  'glass_frac_of_sub_square_plan': dict(value=float(np.mean([c_['glass_frac_of_square'] for c_ in cov.values()])), per_square={k_: c_['glass_frac_of_square'] for k_, c_ in cov.items()},
                                        method='glass mask V>110 after 3x3 opening, components >= 40 px, over the full 3.7 m sub-square incl. rib bands'),
  'glass_frac_of_field_excl_ribs': dict(value=float(np.mean([c_['glass_frac_of_field'] for c_ in cov.values()])), rib_band_frac_of_square=float(np.mean([c_['rib_frac_of_square'] for c_ in cov.values()])),
                                        method='same glass area over (square - rib bands drawn at the measured projected widths: 60/29/31/35 px). The rib bands take 36 % of the plan at projected width; with true soffit widths the field is larger and this fraction lower (~50 %).'),
  'pieces_per_m2_plan': dict(value=S['pieces_per_m2_plan'], n=S['n_pieces'], area_m2=S['plan_area_m2'], method='449 detected pieces / 54.9 m2 (4 sub-squares). Undercount: at 7.9 mm/px pieces < ~56 mm and touching pieces merge (the emblem X-squares often count as 1). NGV states 10,000 pieces / 765 m2 = 13.1 per m2 plan.'),
  'pieces_per_m2_field_excl_ribs': S['pieces_per_m2_field'],
  'eq_diam_mm_p10_p50_p90': S['eq_diam_mm_p10_p50_p90'],
  'eq_diam_mm_area_weighted_p10_p50_p90': S['eq_diam_mm_area_weighted_p10_p50_p90'],
  'eq_diam_mm_mean': S['eq_diam_mm_mean'],
  'minrect_long_mm_p10_p50_p90': S['minrect_long_mm_p10_p50_p90'], 'minrect_short_mm_p10_p50_p90': S['minrect_short_mm_p10_p50_p90'],
  'aspect_p10_p50_p90': S['aspect_p10_p50_p90'],
  'area_mm2_p10_p50_p90': S['area_mm2_p10_p50_p90'],
  'shape_share_count': S['shape_share_count'], 'shape_share_area': S['shape_share_area'],
  'shape_method': 'rect: minAreaRect fill > 0.80 and 4 approx vertices; tri: 3 vertices or (fill < 0.62, solidity > 0.9, <= 4 vertices); else irregular. At 7.9 mm/px rounded rectangles and chipped edges blur the classes; treat +-10 %.',
  'orientation_vs_ribs': orient,
  'balcony_4k_eq_diam_px_p10_p50_p90': M['balcony_b001_look']['eqd_px_p10_p50_p90'],
 },
 'colour': {
  'lf02': dict(hue_buckets_30deg_area=C['hue_buckets_30deg'], families=C['families'],
               coloured_sat_p10_p50_p90=C['coloured_sat_p10_p50_p90'], coloured_val_p10_p50_p90=C['coloured_val_p10_p50_p90'],
               clear_area_frac=C['clear_area_frac'], clear_count_frac=C['clear_count_frac'], clear_hard_clipped_frac=C['clear_hard_clipped_frac'],
               method='per piece median RGB of the interior (>= 2 px from the edge); clear = HSV S < 0.25 and V > 0.78; buckets are 30 deg wide centred on 0,30,...330, area-weighted, clear excluded; lf02 is overexposed so hues are pastel-shifted and 51 % of the area reads clear'),
  'closeups': M['closeup_colour'],
  'pooled_hue_buckets_area': None,
  'regional_note': 'the palette is regional: lf02 area = pastel blue/lilac/amber with 45-51 % clear; close-ups 1-2 (same spot) = red 15-22 %, magenta/violet 14-15 %, 25-28 % clear; entrance central bays = amber+yellow 36 %, blue 11-15 %, 36 % clear. A tracer should sample the local photo, not a single global histogram.',
  'transmission_estimate': dict(
     from_lf02=C['transmission_estimate'],
     from_closeup2=dict(exposure_gain_k=float(k2), values=trans2,
                        method='same construction as lf02 (family median sRGB -> linear, scaled so the brightest coloured channel = 0.62, clear fixed 0.85) but on close-up 2, the least clipped source. Recommended for the shader; lf02 values are bleached.'),
     saturation_note='camera saturation of coloured pieces: lf02 S p50 0.58, close-up1 0.93 (phone-boosted), close-up2 0.68, entrance 0.34 (daylight overexposed), balcony 4K unclipped pieces 0.60. Real slab glass 25 mm thick is strongly saturated: aim for linear chroma like close-up2/1, not lf02.'),
 },
 'piece_look': {
  'lf02_7p9mm_per_px': L,
  'balcony_4k': M['balcony_b001_look'],
  'balcony_4k_rim': look_extra,
  'summary': {
   'edge_darkening': 'luminance falls to 0.36 x interior at 1 px from the mask edge, 0.62 at 2 px, 0.77 at 3 px, 0.91 at 4 px, 0.97 at 5 px, 1.0 from 6 px (4K, pieces ~68 px eq. diam.) = a soft dark edge over ~6 % of the piece diameter, roughly 10-15 mm at the 194 mm median size; part of this is lens blur. lf02 (7.9 mm/px): 0.85 / 0.96 / 0.99 at 1/2/3 px = the same ~8-15 mm band.',
   'rim_highlight': 'no continuous bright bevel line: the median 1-5 px ring p95 is only slightly above the interior (see balcony_4k_rim); bright rim glints appear as short blobs along an edge (chipped facets catching the sky), typically along one edge of a piece (balc_b001_piece_tiles.jpg, orange and blue tiles).',
   'internal_variation': 'luminance std / mean inside a piece: p10 0.03, p50 0.08-0.09, p90 0.14-0.17 (both sources); p10/p90 of interior luminance = 0.91 / 1.11 of the mean; the variation is mottled/streaky (hand-chipped slab), not a gradient.',
   'matrix': 'reads as neutral near-black, slightly cool in lf02 (33,34,37) and neutral-warm in the 4K still (29,26,28); luminance p10/p50/p90 = 16/27/37 (4K) and 21/34/57 (lf02) on 0-255 under daylight-through-glass exposure. In linear terms ~1-2 % of a clipped clear piece. Not brown.',
  },
 },
 'facet_brightness_by_day': {
  'b0_bays': M['b0_facets'],
  'lf02_quadrants': quad,
  'clear_over_coloured_after_clipping': dict(lf02=X['clear_vs_coloured']['lf02'], gh03=X['clear_vs_coloured']['gh03'], bc0=X['clear_vs_coloured']['bc0'], b0=X['clear_vs_coloured']['b0'],
     closeup1_srgb=float(0.965 / M['closeup_colour']['closeup1_10f13e18']['coloured_val_p10_p50_p90'][1]),
     closeup2_srgb=float(0.953 / M['closeup_colour']['closeup2_06984bd9']['coloured_val_p10_p50_p90'][1]),
     summary='sRGB V ratio of the median clear piece to the median coloured piece: 1.02 (lf02, everything clipped), 1.05 (gh03), 1.12 (bc0), 1.13-1.23 (close-ups), 1.37 (b0, best exposed). Linear: 1.05 / 1.12 / 1.29 / 1.3-1.6 / 2.03. Unclipped physics would be 2-8x; the photographs compress it to 1.0-1.4 in sRGB.'),
  'summary': 'b0 bay A (mid-hall): per-glass median V far 232 / near 233 / left 243 / right 246 (all within 6 %), but the right facet is 83 % clear pieces vs 33-48 % for the others, so its coloured pieces read darker (137 vs ~200). b0 bay C (near the wall): far 231 / left 202 / right 152 / near 123 = the facet whose underside faces away from the camera is 1.9x darker in sRGB (~4x linear). lf02 quadrants (four different bays, straight up): coloured V p50 and clear share nearly equal in all four. Conclusion: no consistent sun-facing/opposite ratio is measurable from these photos; facet differences of up to ~2x sRGB occur but are confounded by viewing angle, local clear share and lens flare. Which facet is north-facing is not determined here (b0 camera orientation unknown; hall frame: hv S->N per CLOUD_CENSUS, so the facet on the south side of each vertex faces north).',
 },
 'motifs': {
  'square_ring_with_X': dict(
     inner_X_square_m=[0.33, 0.35], ring_outer_m=[0.87, 0.91, 0.73, 0.75],
     ring_pieces='2 stacks of 3 vertical rectangles (~95 x 240 mm) on the left and right, 2-3 horizontal rectangles top and bottom; the inner square is 4 clear triangles split by a matrix X (~40 mm arms)',
     count_per_sub_square=4, placement='2 in each of the two triangles that touch the ridge beams; 16 around every bay corner (crest node) in the lf02 area',
     centres_m_from_node_along_ridge=[1.47, 2.45], centre_m_off_ridge_axis=[0.58, 0.66],
     colours='ring: red/orange (4), blue/cyan (3), lilac/violet (4), pink/peach (3), white (1) of 16 measured; inner triangles: clear/white (13 of 16), amber (3)',
     method='by hand on crop_motifs_x4.jpg / emblem_montage_x2.jpg at 7.89 mm/px and from the 16 emblem centres in extra.json (centres read on the overlay, mirrored across the ridge)',
     per_emblem=X['emblems']),
  'bands_of_rectangles': 'rows of 3-6 similar rectangles (~90 x 200-260 mm) laid parallel to a rib, 100-150 mm off it, along cross members (yellow row left of x=169, y~420) and along diagonals ("brick courses"); orientation stats: see coverage_and_pieces.orientation_vs_ribs',
  'rosettes': dict(
     fan_around_column_head='at the light-light corners (funnel vertices) the clear pieces are laid as radial fans (lf02 corners, gh03_colhead_crop.jpg bottom centre)',
     big_circular_rosettes='the entrance shot shows two large circular rosettes (concentric rings of radial rectangles round a dark ring) in the central bays; no metric scale in that photo: ring outer diameter 165 px vs local diagonal-line pitch (see lattice) - reported as a ratio only',
     lattice=lattice),
  'mirror_symmetry': dict(
     evidence=SY,
     cross_member_strips=X['cross_member_mirror'],
     statement='In the lf02 area the pattern is mirror-symmetric across both ridge beams (mask NCC 0.80/0.82 vs 0.35/0.41 unmirrored, colour 0.82/0.83) and across the main diagonals through the bay corner (transpose NCC 0.75-0.88 vs 0.12 for the anti-diagonal control). So the 8 triangles round a crest node are mirror copies of ONE ridge-triangle design, and the 8 non-ridge triangles round the same node are copies of a second design; adjacent triangles across a ridge or a hip ARE mirror images, adjacent triangles across the anti-diagonal are NOT. Across the cross members the test is weak (strips 157 px wide: NCC 0.28 mirrored vs 0.12-0.18 plain, favouring mirror but inconclusive). The ceiling is not globally periodic: the entrance shot shows different big rosettes in the central bays.'),
 },
}
# pooled hue histogram (equal weight per source)
srcs = [C['hue_buckets_30deg']] + [v['hue_buckets_30deg'] for v in M['closeup_colour'].values()]
pooled = {}
for k_ in srcs[0]:
    pooled[k_] = float(np.mean([s_[k_]['area_frac'] for s_ in srcs]))
out['colour']['pooled_hue_buckets_area'] = dict(values=pooled, method='equal-weight mean of lf02, close-up 1, close-up 2 and the entrance crop; a coarse global prior only')
json.dump(out, open(outp, 'w'), indent=1)
print(json.dumps(dict(quad=quad, orient=orient, look_extra=look_extra, lattice=lattice, k2=k2, trans2=trans2, pooled=pooled), indent=1))
