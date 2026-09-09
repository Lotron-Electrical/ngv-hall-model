# 2026-09-09: give each balcony clip its own matches, which it has never had.
# Reasoning in tools/clip_pairs.py. The features are already in the database from the original register;
# only the intra-clip PAIRS are missing, so this is one matches_importer run over a few thousand pairs
# rather than a re-extraction. The keyframe matching that already ran cost 139,482 pairs; this adds about
# 2,600 per clip.
#   python tools/clip_selfmatch.py <prefix> [<prefix> ...]
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"C:/Users/Lloyd Gibbs/Claude Projects/sitecapture/pipeline")
import relocalise_frames as R  # noqa: E402

WS = Path('E:/sitecapture-captures/ngv-video/balcony2-register')
WORK = WS / 'work'
DB = WORK / 'database.db'

sys.path.insert(0, 'tools')

for prefix in sys.argv[1:]:
    listing = WORK / ('selfpairs-' + prefix + '.txt')
    r = subprocess.run([sys.executable, '-u', 'tools/clip_pairs.py', prefix, str(listing)],
                       capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr[-800:])
        continue
    R.run_colmap(['matches_importer', '--database_path', str(DB), '--match_list_path', str(listing),
                  '--match_type', 'pairs', '--FeatureMatching.use_gpu', '1'],
                 'selfmatch-' + prefix, WORK)
    print(prefix, 'intra-clip matches imported')
