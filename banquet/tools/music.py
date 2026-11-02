# Original instrumental for the banquet loop. 120 BPM, generated here, no samples.
import sys, numpy as np, wave
from scipy.signal import lfilter
SR=44100; BPM=120; B=60/BPM; BAR=4*B
DUR=float(sys.argv[2]); N=int(SR*DUR); L=np.zeros(N); R=np.zeros(N); rng=np.random.default_rng(11)
def add(sig,start,gain=1.0,pan=0.0):
    i=int(start*SR)
    if i>=N: return
    j=min(N,i+len(sig)); s=sig[:j-i]*gain; L[i:j]+=s*(1-max(pan,0)); R[i:j]+=s*(1+min(pan,0))
def lp(x,a): return lfilter([a],[1,a-1],x)
def kick(): n=int(.45*SR); t=np.arange(n)/SR; return np.sin(2*np.pi*np.cumsum(45+110*np.exp(-t*28))/SR)*np.exp(-t*7)
def clap(): n=int(.25*SR); t=np.arange(n)/SR; return np.diff(rng.normal(0,1,n),prepend=0)*np.exp(-t*18)*.5
def hat(): n=int(.06*SR); t=np.arange(n)/SR; return np.diff(np.diff(rng.normal(0,1,n),prepend=0),prepend=0)*np.exp(-t*60)*.18
def crash(): n=int(2.2*SR); t=np.arange(n)/SR; return np.diff(rng.normal(0,1,n),prepend=0)*np.exp(-t*2.2)*.25
def saw(f,n): t=np.arange(n)/SR; return 2*((t*f)%1)-1
def sq(f,n): t=np.arange(n)/SR; return np.sign(np.sin(2*np.pi*f*t))
hz=lambda m:440*2**((m-69)/12)
PROG={"A":[(57,[57,60,64]),(53,[53,57,60]),(48,[48,52,55]),(55,[55,59,62])],     # Am F C G
      "C":[(53,[53,57,60]),(55,[55,59,62]),(57,[57,60,64]),(52,[52,55,59])]}     # F G Am Em
# section plan, in bars: (kind, bars). Repeats to fill the length.
PLAN=[("intro",2),("A",16),("A+lead",16),("B",8),("C",16),("C+arp",16),("A+lead",16),("B",8)]
def section(kind,bars,t0):
    base="C" if kind.startswith("C") else "A"; prog=PROG[base]
    for k in range(bars):
        tb=t0+k*BAR
        if tb>=DUR: return
        root,ch=prog[k%4]; n=int(BAR*SR)
        pad=sum(saw(hz(m),n)+saw(hz(m)*1.004,n) for m in ch)/6
        env=np.minimum(1,np.arange(n)/(.3*SR))*np.minimum(1,(n-np.arange(n))/(.2*SR))
        add(lp(pad,.05 if kind!="B" else .03)*env,tb,.22 if kind in("intro","B") else .30)
        if kind=="intro":
            for b in range(4):
                if b%2==0: add(kick(),tb+b*B,.55)
                add(hat(),tb+b*B+B/2,.6,.3)
            continue
        if kind=="B":                       # breakdown: half-time, open, airy
            add(kick(),tb,.8); add(clap(),tb+2*B,.6)
            for b in range(4): add(hat(),tb+b*B+B/2,.5,.3)
            m=ch[2]+12; nn=int(BAR*SR); add(lp(sq(hz(m),nn),.06)*np.exp(-np.arange(nn)/SR*1.2)*.5,tb,.12,-.2)
            continue
        for b8 in range(8):                 # driving bass
            nn=int(B/2*SR*.9); add(lp(saw(hz(root-24),nn),.12)*np.exp(-np.arange(nn)/SR*6),tb+b8*B/2,.55)
        for b in range(4):
            if b%2==0: add(kick(),tb+b*B,.95)
            else: add(clap(),tb+b*B,.8)
            if b==3 and k%2==1: add(kick(),tb+b*B+B*.75,.35)
            for h in range(2): add(hat(),tb+b*B+h*B/2,1.0,.35 if h else -.35)
        if "lead" in kind:                  # simple brassy hook over the chords
            hook=[0,2,1,0,2,1,2,3]; notes=ch+[ch[0]+12]
            for s,idx in enumerate(hook[:4] if k%2==0 else hook[4:]):
                nn=int(B*SR*.95); f=hz(notes[idx]+12); tt=np.arange(nn)/SR
                tone=(saw(f,nn)+.5*saw(f*1.006,nn))*np.minimum(1,tt/.02)*np.exp(-tt*2.5)
                add(lp(tone,.09),tb+s*B,.16,.15)
        if "arp" in kind:
            notes=ch+[ch[0]+12,ch[1]+12]
            for s in range(16):
                nn=int(B/4*SR*.9); f=hz(notes[s%len(notes)]+12)
                add(lp(sq(f,nn),.15)*np.exp(-np.arange(nn)/SR*14),tb+s*B/4,.09,-.3 if s%2 else .3)
    # riser + crash into the next section
    tr=t0+bars*BAR
    if tr<DUR:
        n=int(2*SR); tt=np.arange(n)/SR; add(lp(rng.normal(0,1,n)*(tt/2)**2*.25,.15)*3,tr-2,.55); add(crash(),tr,1.0); add(kick(),tr,1.1)
t=0.0; i=0
while t<DUR:
    kind,bars=PLAN[i%len(PLAN)]
    if i>0 and kind=="intro": kind="B"
    section(kind,bars,t); t+=bars*BAR; i+=1
mix=np.stack([L,R],1); mix=np.tanh(mix/np.abs(mix).max()*1.6)/np.tanh(1.6)*.92     # gentle glue/limit
fade=np.minimum(1,(N-np.arange(N))/(1.5*SR))[:,None]; fin=np.minimum(1,np.arange(N)/(.05*SR))[:,None]; mix*=fade*fin
with wave.open(sys.argv[1],"wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix*32767).astype(np.int16).tobytes())
print("music",DUR,"s")
