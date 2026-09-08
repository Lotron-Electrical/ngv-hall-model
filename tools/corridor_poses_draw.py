# 2026-09-09: the pose census as a plan. Every registered camera in the archive plotted in the hall's own
# frame, with the north wall, the reveal and the corridor as the model draws them, so the answer is visible
# rather than argued: the dots stop at the wall.
#   python tools/corridor_poses_draw.py <corridor-poses.csv> <out.png>
import sys, csv
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

src, out = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(src)))
COL = {'walk': '#4da3ff', 'night': '#8f7dff', 'day4k': '#ffd24d', 'b1': '#ff5f5f', 'b3': '#5fff8f', 'b6g': '#ff8fd6'}
fig, ax = plt.subplots(figsize=(11, 5.2), dpi=150)
fig.patch.set_facecolor('#101216'); ax.set_facecolor('#101216')

# the wall and what is behind it
ax.axhspan(-0.99, -0.09, color='#3a3f4a', zorder=1)                      # the reveal / wall thickness
ax.axhspan(-2.99, -0.99, color='#242a36', zorder=1)                      # the corridor as drawn
ax.axhline(-0.09, color='#ffffff', lw=1.2, zorder=3)
ax.axhline(-0.99, color='#9aa4b2', lw=1.0, ls='--', zorder=3)
ax.axhline(-2.99, color='#9aa4b2', lw=1.0, ls='--', zorder=3)
ax.text(4.6, -0.62, 'the openings (reveal 0.9)', color='#c8cfda', fontsize=8, va='center')
ax.text(4.6, -2.05, 'THE CORRIDOR as drawn, width 2.0: ZERO cameras have ever stood here',
        color='#ff9f9f', fontsize=9, va='center', weight='bold')

for r in rows:
    ax.plot(float(r['u']), float(r['d']), '.', ms=3.2, color=COL.get(r['class'], '#888'), zorder=4)
for k, c in COL.items():
    n = sum(1 for r in rows if r['class'] == k)
    if n: ax.plot([], [], '.', ms=8, color=c, label='%s (%d)' % (k, n))

deep = sorted(rows, key=lambda r: float(r['d']))[0]
ax.annotate('deepest camera: b1 %s, d %.2f\n0.36 m past the wall face, 0.54 m short of the reveal'
            % (deep['frame'].split('_')[1], float(deep['d'])),
            xy=(float(deep['u']), float(deep['d'])), xytext=(23.5, 5.6), color='#ffd24d', fontsize=8,
            arrowprops=dict(arrowstyle='->', color='#ffd24d', lw=1))
ax.set_xlim(2, 52); ax.set_ylim(-3.4, 15.6); ax.invert_yaxis()
ax.set_xlabel('u, along the hall (m)', color='#c8cfda'); ax.set_ylabel('d, across the hall (m)', color='#c8cfda')
ax.set_title('1,116 registered cameras vs the wall they are meant to measure behind (2026-09-09)',
             color='#ffffff', fontsize=11)
ax.tick_params(colors='#8b93a1'); [sp.set_color('#2a2f3a') for sp in ax.spines.values()]
ax.grid(color='#1c2028', lw=0.6)
lg = ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=6,
               facecolor='#171a20', edgecolor='#2a2f3a', fontsize=8)
for t in lg.get_texts(): t.set_color('#c8cfda')
fig.tight_layout(); fig.savefig(out, facecolor=fig.get_facecolor()); print('wrote', out)
