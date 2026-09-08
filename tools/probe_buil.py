# The 1968 drawings on the NGV image API sit on consecutive BUIL ids (5490, 5492, 5494, 5496 = the four floor
# plans). This probes the ids around them for a section or elevation of the Great Hall, keeping what answers.
import sys, urllib.request, os
OUT = 'E:/sitecapture-captures/ngv-site/agent-ref-walls/online/buil'
os.makedirs(OUT, exist_ok=True)
lo, hi = int(sys.argv[1]), int(sys.argv[2])
for n in range(lo, hi + 1):
    url = 'https://content.ngv.vic.gov.au/col-images/api/BUIL%06d/1920' % n
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=20)
        b = r.read()
        open('%s/BUIL%06d.jpg' % (OUT, n), 'wb').write(b)
        print(n, len(b), r.headers.get('Content-Type'))
    except Exception as e:
        print(n, 'no', str(e)[:60])
