import sys,glob,os
from PIL import Image, ImageOps
S=sys.argv[1]
def dh(p):
    try: im=ImageOps.exif_transpose(Image.open(p)).convert("L")
    except Exception as e: return None
    im.draft("L",(256,256)); im=im.resize((17,16))
    px=list(im.getdata()); return sum(1<<i for i in range(256) if px[(i//16)*17+i%16]>px[(i//16)*17+i%16+1])
old=[]
for pat in ["v1/src/**/*.*","batch1/raw/*","batch2/raw/*","banquet/*.jpg"]:
    for p in glob.glob(f"{S}/{pat}",recursive=True):
        if p.lower().endswith((".jpg",".jpeg",".png",".heic")):
            h=dh(p); 
            if h is not None: old.append((p,h))
new=[(p,dh(p)) for p in sorted(glob.glob(f"{S}/batch3/raw/Photo*"))]
print("old",len(old),"new",len(new))
for p,h in new:
    best=min(((bin(h^oh).count("1"),op) for op,oh in old),default=(999,""))
    near=[os.path.basename(q) for q,qh in new if q!=p and bin(h^qh).count("1")<=30]
    print(f"{os.path.basename(p)[6:-4]:28s} old:{best[0]:3d} {os.path.relpath(best[1],S)[:45]:45s} same-batch:{near}")
