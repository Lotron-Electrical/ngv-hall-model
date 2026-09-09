# 2026-09-09: give the far-edge collector a POLARITY, because the feature it is now being pointed at has
# the opposite one and its own feasibility test said so before a single line was fitted.
#
# tools/west_far.py was written for the top of a LIT front: bright below, dark above. That is right for the
# balcony front edge it measured on 9.799 west and 9.865 east. It is wrong for the top of the SOLID
# UPSTAND underneath it, and the pooled brightness profile is unambiguous about which way round that one
# is: over the east upstand band the face gets BRIGHTER going up, +7.1 standard deviations per metre at
# the drawn 9.110, while the steepest fall anywhere in the band is 0.27 and the tool refused on it.
#
# THE PHYSICS SAYS THE SAME THING. From a lens on the hall floor the solid upstand presents a face that
# looks into the hall, away from the stained glass overhead, so it sits in its own shade; above it the open
# rail is see-through and what shows through it is the lit gallery ceiling behind. Dark below, bright
# above. Detector parity names the feature, and a detector told to find one cannot find the other, so
# running the old polarity here would have been asking the wrong question and getting a refusal for it.
import io

target = 'tools/west_far.py'
s = io.open(target, encoding='utf-8').read()
if 'POLARITY' in s:
    print('already has a polarity')
    raise SystemExit(0)

s = s.replace("TAG = os.environ.get('TAG', '')",
              "TAG = os.environ.get('TAG', '')\n"
              "# POLARITY names which feature is being looked for, see tools/patch_far_polarity.py.\n"
              "# 'lit' is the top of a lit front, bright below and dark above. 'shade' is the top of a\n"
              "# shaded solid with something see-through and lit above it, which is the upstand.\n"
              "POLARITY = os.environ.get('POLARITY', 'lit')\n"
              "PSIGN = 1.0 if POLARITY == 'lit' else -1.0")

s = s.replace("            dstep = float(v[i - HWIN:i].mean() - v[i + 1:i + 1 + HWIN].mean())",
              "            dstep = PSIGN * float(v[i - HWIN:i].mean() - v[i + 1:i + 1 + HWIN].mean())")

s = s.replace("k = int(np.argmin(grad))                       # the steepest FALL going up",
              "k = int(np.argmin(PSIGN * grad))               # the steepest step of the chosen polarity")

s = s.replace(
    "print('   the steepest fall in brightness going up the face plane is between h %.3f and %.3f'\n"
    "      % (hs[max(0, k - 1)], hs[min(len(hs) - 1, k + 1)]))",
    "print('   the steepest %s in brightness going up the face plane is between h %.3f and %.3f'\n"
    "      % ('fall' if POLARITY == 'lit' else 'rise', hs[max(0, k - 1)],\n"
    "         hs[min(len(hs) - 1, k + 1)]))")

io.open(target, 'w', encoding='utf-8', newline='\n').write(s)
print('west_far.py now takes POLARITY=lit or POLARITY=shade')
