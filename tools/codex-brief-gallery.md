# Brief: tools/gallery_measure.py (new file, Python 3.12, cv2 + numpy only, no other new deps)

Repo: this directory (ngv-hall-model). Write ONE new file, tools/gallery_measure.py. Do not touch index.html or any other file. No commits.

## Context
The hall has a hall frame: origin O = (-54.907447, -1.43545, 3.040286), axes HU = (0.975681, 0, 0.219196) along the hall (u), HD = (0.219196, 0, -0.975681) across it (d), h = world y minus O.y. A point X (world) has u = (X-O)·HU, d = (X-O)·HD, h = (X-O).y. The hall's north wall face is the plane d = -0.09; the hall is on the d > -0.09 side. Behind that wall (d < -0.09) is a gallery: a long room whose roof is the hall's stained-glass canopy sloping down to an outer wall, vitrines against that outer wall, floor h about 8.34. Twelve openings in the north wall look into it (u ranges in WALLF.openings in index.html lines 1053-1054, openY [8.99, 11.35]). We need its geometry measured from posed 4K video frames.

Posed frames come from tools/underside_geom.py: `import underside_geom as U; cams = U.load_class(cname)` returns {frame_name: (Cam, image_path)}. Cam has .R (3x3 world-to-camera rotation), .center (3, world), .params = [fx, fy, cx, cy, k1, k2, p1, p2] (OPENCV model), .w, .h, and .project(pts Nx3 world) -> (x, y, z) arrays. tools/chain_pose2.py writes shots/pose/chain-<class>-<start>-<end>.json: a list of {frame, cname, R, C, ...} for frames without a register pose; treat those the same (R, C=center; the camera params come from cams of the first record's frame). Study tools/chain_pixel.py, tools/chain_project.py and tools/chain_pose2.py for the conventions (undistortPoints with K and dist, ray D = R.T @ [nx, ny, 1]).

## What the tool does
```
python tools/gallery_measure.py <class> [--chain shots/pose/chain-....json] [--frames f1,f2,...] [--u-range 20 30] [--out DIR]
```
1. Collect the posed frames (register poses, plus chain poses if --chain given; --frames limits to a list; default all).
2. Sort by frame index. For every pair of frames within 6 indices of each other whose baseline (distance between centres) is between 0.10 and 2.0 m: SIFT (4000 features on a half-size grey image, coordinates scaled back), ratio test 0.75, cross-check, undistort both sides, triangulate with cv2.triangulatePoints on P = K[R | -R C] (undistorted pixels, so K without distortion), keep points with positive depth in both cameras, reprojection error under 3 px in both, and triangulation angle over 1.5 degrees.
3. Convert to (u, d, h). Keep only points behind the north wall: d < -0.09 - 0.2 (clearly inside the gallery), and inside --u-range if given.
4. Report, all in metres, on stdout and to <out>/gallery-<class>.json:
   - count of gallery points and of frame pairs used;
   - outer wall depth: histogram of d in 0.05 m bins over the points with 8.5 < h < 11; the deepest strong peak (a bin with at least 3 % of the points, the most negative such d); also the d of the densest bin;
   - floor: the densest 0.05 m bin of h over points with h < 9.0;
   - the canopy: over points with h > 10.0, RANSAC a line h = a + b*d (inlier threshold 0.08 m, 500 iterations); print a, b, the inlier count and the h where it meets the hall face d = -0.09 and the outer wall d;
   - vitrines: over points with 8.5 < h < 10.5 and d between the outer wall and outer wall + 1.5, print the densest 0.1 m bin of d (the vitrine front) and its h span.
   - a scatter image <out>/gallery-<class>-dh.png (cv2 only): d on the x axis (-6 to 0 m), h on the y (7 to 14 m), 100 px per metre, points as 1 px dots, the fitted canopy line, the outer wall and vitrine verticals, the hall face d = -0.09, with labels.
   - a second image <out>/gallery-<class>-ud.png: u (0-52 m) against d (-6 to 0), 40 px per metre, for the plan.
5. Default --out is E:/sitecapture-captures/ngv-site/agent-ref-walls/shots/pose. Every printed number carries its unit and its source count. If fewer than 200 gallery points are found, say so and still write the images.

## Verification
`python tools/gallery_measure.py b1` must run without error from the repo root (class b1 has 59 posed frames and no gallery view: expect few or zero gallery points and the "fewer than 200" message). Run it and paste the output. Keep the file under 200 lines, comments in plain English saying what each block measures.
