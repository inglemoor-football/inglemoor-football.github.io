import sys, os, re, datetime, subprocess, numpy as np
from multiprocessing import Pool
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
S=sys.argv[1]; MODE=sys.argv[2]
REPO="/home/claude/inglemoor-football.github.io"; SRC=f"{S}/v1/src"; CAND=f"{S}/batch1/raw"; OUT=f"{S}/v2/out"; os.makedirs(OUT,exist_ok=True)
HL=[p for p in __import__("glob").glob("/mnt/user-data/attachments/*/33d271bf-hashmark-highlight.mp4")][0]
HEIDI=f"{CAND}/IMG_0431 Heidi Cowan.mov"
W,H,FPS=1920,1080,30
INK=(10,11,13); PANEL=(20,22,26); GOLD=(254,183,46); BONE=(244,241,233); MUTE=(138,146,158); WIN=(92,184,127); LOSS=(196,87,75)
BLACK_F="/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"; COND_F="/usr/share/fonts/opentype/inter/Inter-Bold.otf"
PLEN=int(3.5*FPS); XF=8

def eo(t): t=max(0,min(1,t)); return 1-(1-t)**3
def eio(t): t=max(0,min(1,t)); return t*t*(3-2*t)
_fc={}
def font(p,s):
    if (p,s) not in _fc: _fc[(p,s)]=ImageFont.truetype(p,s)
    return _fc[(p,s)]
def text(t,size,color,path=BLACK_F,track=0.0,squeeze=0.80):
    f=font(path,size); asc,desc=f.getmetrics()
    if track==0:
        im=Image.new("RGBA",(int(f.getlength(t))+8,asc+desc+4),(0,0,0,0)); ImageDraw.Draw(im).text((2,2),t,font=f,fill=color+(255,))
    else:
        ws=[f.getlength(c) for c in t]; im=Image.new("RGBA",(int(sum(ws)+track*size*len(t))+4,asc+desc+4),(0,0,0,0)); d=ImageDraw.Draw(im); x=2
        for c,w in zip(t,ws): d.text((x,2),c,font=f,fill=color+(255,)); x+=w+track*size
    if squeeze!=1: im=im.resize((max(1,int(im.width*squeeze)),im.height),Image.LANCZOS)
    return im.crop(im.getbbox())
def label(t,size=30,color=MUTE,track=0.22): return text(t,size,color,COND_F,track,1.0)
def paste(base,im,x,y,a=1.0,dy=0):
    if a<=0: return
    if a<1: im=im.copy(); im.putalpha(im.getchannel("A").point(lambda v:int(v*a)))
    base.alpha_composite(im,(int(x),int(y+dy)))
def rule(img,x,y,w,t,color=GOLD,h=4):
    ww=int(w*eo(t))
    if ww>0: ImageDraw.Draw(img).rectangle([x,y,x+ww,y+h],fill=color+(255,))
def up(t,t0,d=0.55,dist=24): a=eo((t-t0)/d); return a,dist*(1-a)

def grade(im):
    """Matched colour grade: half-strength auto levels, a touch of contrast, saturation pulled toward a common level."""
    a=np.asarray(im).astype(np.float32)/255; lum=a@np.array([.299,.587,.114],np.float32)
    lo,hi=np.percentile(lum[::4,::4],[0.5,99.5]); hi=max(hi,lo+0.2)
    a=a*0.5+np.clip((a-lo)/(hi-lo),0,1)*0.5; a=np.clip(0.5+(a-0.5)*1.04,0,1)
    g=(a@np.array([.299,.587,.114],np.float32))[...,None]; sat=np.abs(a-g).mean()
    if sat>0.01: a=np.clip(g+(a-g)*np.clip(0.11/sat,0.92,1.12),0,1)
    return Image.fromarray((a*255).astype(np.uint8))
CROP={"545C3F48-EE20-4BEE-93CB-2819873C5035 Shelly Holt.jpeg":(0,560,1179,1600)}   # phone-story screenshot: photo only
def load(p,maxw=2880):
    im=Image.open(p); im.draft("RGB",(maxw,maxw)); im=ImageOps.exif_transpose(im).convert("RGB")
    if os.path.basename(p) in CROP: im=im.crop(CROP[os.path.basename(p)])
    if im.width>maxw: im=im.resize((maxw,int(im.height*maxw/im.width)),Image.LANCZOS)
    return grade(im)
def kb(src,z,fx,fy,size=(W,H)):
    w,h=size; sw,sh=src.size; k=max(w/sw,h/sh)*z; vw,vh=w/k,h/k
    cx=min(max(fx*sw,vw/2),sw-vw/2); cy=min(max(fy*sh,vh/2),sh-vh/2)
    return src.transform((w,h),Image.AFFINE,(1/k,0,cx-vw/2,0,1/k,cy-vh/2),Image.BICUBIC)
yy,xx=np.mgrid[0:H,0:W]; _r=np.sqrt(((xx-W/2)/(W/2))**2+((yy-H/2)/(H/2))**2)
VIG=Image.fromarray((np.clip((_r-0.55)/0.9,0,1)**1.6*160).astype(np.uint8)); BLK=Image.new("RGB",(W,H),(0,0,0))
def finish(rgb): return Image.composite(BLK,rgb,VIG)
def gleft(alpha=240):
    x=np.linspace(1,0,W); g=np.tile((np.clip(x*1.6-0.15,0,1)**1.2*alpha),(H,1))
    y=np.linspace(0,1,H)[:,None]; g=np.maximum(g,np.clip((y-0.55)/0.45,0,1)**1.5*alpha)
    return Image.merge("RGBA",[Image.new("L",(W,H),0)]*3+[Image.fromarray(g.astype(np.uint8))])

# ---------- data ----------
html=open(f"{REPO}/index.html",encoding="utf-8").read()
GAMES=[]
for m in re.finditer(r'\{ date:"([\d-]+)",\s*time:"[^"]*",\s*opp:"([^"]*)",\s*abbr:"(\w+)",\s*at:"(\w+)"([^}]*?)us:(\d+), them:(\d+)',html):
    GAMES.append(dict(date=m[1],opp=m[2],abbr=("PO" if "round:" in m[5] else m[3]),at=m[4],us=int(m[6]),them=int(m[7])))
for i,g in enumerate(GAMES): g["n"]=i+1
FOLDER={"2026-09-05":"Juanita","2026-09-11":"Highline","2026-09-18":"9-18-MercerIsland","2026-09-25":"Interlake",
        "2026-10-02":"Newport","2026-10-09":"10-9-at-Redmond","2026-10-16":"10-16-at-LW","2026-10-24":"Liberty"}
C=lambda n:f"{CAND}/{n}"
P=lambda n:("photo",[C(n)])
PAIR=lambda a,b:("pair",[C(a),C(b)])
EXTRA={   # parents' candids, after each game's pro photos (agreed Nov 3)
 "2026-09-11":[P("545C3F48-EE20-4BEE-93CB-2819873C5035 Shelly Holt.jpeg")],
 "2026-09-18":[P("IMG_6040 Shelly Holt.jpeg"),("video",[HL,0,None])],
 "2026-09-25":[P("IMG_4065 Karen.jpeg")],
 "2026-10-02":[P("IMG_5779 Shelly Holt.jpeg"),P("IMG_6419 Shelly Holt.jpeg")],
 "2026-10-09":[P("IMG_6092 Heidi Cowan.jpeg")],
 "2026-10-16":[P("IMG_7148 Shelly Holt.jpeg"),PAIR("IMG_6394 Heidi Cowan.jpeg","IMG_7171 Shelly Holt.jpeg")],
 "2026-10-24":[PAIR("IMG_2056 Shelly Holt.jpeg","IMG_6665 Shelly Holt.jpeg"),PAIR("IMG_8707 Shelly Holt.jpeg","IMG_7296 Shelly Holt.jpeg"),("video",[HEIDI,20.0,11.0])]}
SUMMER=[P("IMG_5693 Shelly Holt.jpeg"),P("IMG_5713 Shelly Holt.jpeg")]
MEDIA=[P(f"IMG_{n} Shelly Holt.jpeg") for n in ("6234","6237","6235","6247","6242","6272")]
HUG=C("IMG_6813 Heidi Cowan.jpeg")
SHOW=[g for g in GAMES if g["date"] in FOLDER]
W_,L_=sum(g["us"]>g["them"] for g in GAMES),sum(g["us"]<g["them"] for g in GAMES)
coaches=[dict(team=m[1],first=m[2],last=m[3],photo=m[4],role=m[5]) for m in re.finditer(
    r'\{ team:"([^"]+)", first:"([^"]+)", last:"([^"]+)", photo:"([^"]+)",\s*role:"([^"]+)"',html)]
sponsors=[dict(name=m[1],tier=m[2],logo=m[3]) for m in re.finditer(r'\{ name:"([^"]+)",\s*tier:"(\w+)",\s*logo:"([^"]+)"',html)]
def res(g): return "W" if g["us"]>g["them"] else "L" if g["us"]<g["them"] else "T"
def gdesc(g):
    d=datetime.date.fromisoformat(g["date"])
    return (f"GAME {g['n']}  ·  {d.strftime('%a').upper()} {d.strftime('%b').upper()} {d.day}",
            ("AT " if g["at"]=="away" else "VS ")+g["opp"].upper(), res(g), f"{g['us']}–{g['them']}")
def items_for(g):
    d=f"{SRC}/{FOLDER[g['date']]}"; return [("photo",[f"{d}/{f}"]) for f in sorted(os.listdir(d)) if f.lower().endswith(".jpg")]+EXTRA.get(g["date"],[])
# season numbers, straight from the scores
PF=sum(g["us"] for g in GAMES); streak=best=0
for g in GAMES: streak=streak+1 if res(g)=="W" else 0; best=max(best,streak)
AWAY=[g for g in GAMES if g["at"]=="away"]; aw=sum(res(g)=="W" for g in AWAY)
NUMBERS=[(f"{W_}–{L_}","2026 RECORD",None),(str(PF),"POINTS SCORED",PF),(str(best),"STRAIGHT WINS",best),(f"{aw}–{len(AWAY)-aw}","ON THE ROAD",None)]

logo=Image.open(f"{REPO}/images/viking-v-original.png").convert("RGBA")
MARK=logo.resize((int(logo.width*62/logo.height),62),Image.LANCZOS); MARK.putalpha(MARK.getchannel("A").point(lambda v:int(v*.55)))
# ---------- simple scenes (as v1) ----------
def ctx_logo(): return dict(foot=label("INGLEMOOR VIKING FOOTBALL  ·  2026",30,MUTE,0.24))
def sc_logo(f,c):
    t=f/FPS; img=Image.new("RGBA",(W,H),INK+(255,))
    s=0.86+0.14*eo(t/0.9); lh=int(430*s); lg=logo.resize((int(logo.width*lh/logo.height),lh),Image.LANCZOS)
    paste(img,lg,(W-lg.width)/2,(H-lg.height)/2-60,eo(t/0.7)); rule(img,W/2-260,H/2+215,520,(t-0.5)/0.7)
    a,dy=up(t,0.9); paste(img,c["foot"],(W-c["foot"].width)/2,H/2+250,a,dy); return img
def ctx_hero():
    return dict(src=load(f"{S}/banquet/hero.jpg"),gl=gleft(),eb=label("2026 SEASON",34,GOLD,0.32),
        ing=text("INGLEMOOR",215,BONE),vf=text("VIKING FOOTBALL",104,GOLD),rec=text(f"{W_}–{L_}",200,BONE),lab=label("KINGCO MOUNTAIN 3A"))
def sc_hero(f,c):
    t=f/FPS; bg=kb(c["src"],1.22+0.07*eio(t/6),0.40,0.42).convert("RGBA"); bg.alpha_composite(c["gl"])
    a,dy=up(t,0.3); paste(bg,c["eb"],120,300,a,dy); rule(bg,120,350,90,(t-0.3)/0.5)
    a,dy=up(t,0.7); paste(bg,c["ing"],112,385,a,dy); a,dy=up(t,1.1); paste(bg,c["vf"],118,585,a,dy)
    a,dy=up(t,2.2); paste(bg,c["rec"],116,735,a,dy); paste(bg,c["lab"],124,925,a,dy); return bg
def ctx_team():
    tp=grade(Image.open(f"{REPO}/images/team-2026.jpg").convert("RGB"))
    bgr=Image.blend(tp.resize((W,H)).filter(ImageFilter.GaussianBlur(30)),Image.new("RGB",(W,H),INK),0.72)
    return dict(tp=tp,bg=bgr,eb=label("THE 2026 INGLEMOOR VIKINGS",34,GOLD,0.32))
def sc_team(f,c):
    t=f/FPS; img=c["bg"].convert("RGBA"); pw=int(W*0.86); ph=int(pw*c["tp"].height/c["tp"].width)
    shot=kb(c["tp"],1.0+0.04*eio(t/6),0.5,0.5,(pw,ph)).convert("RGBA"); a,dy=up(t,0.0,0.8,30); y0=(H-ph)/2+40
    if a>0: ImageDraw.Draw(img).rectangle([(W-pw)/2,y0-3+dy,(W+pw)/2,y0+dy],fill=GOLD+(int(255*a),))
    paste(img,shot,(W-pw)/2,y0,a,dy); a2,dy2=up(t,0.6); paste(img,c["eb"],(W-c["eb"].width)/2,y0-80,a2,dy2); return img
# ---------- cards: gold wipe in, season tracker ----------
def wipe(img,t,d=0.42):
    if t>=d: return img
    x=int(-260+(W+520)*eio(t/d)); dr=ImageDraw.Draw(img)
    if x<W: dr.rectangle([max(x,0),0,W,H],fill=INK+(255,))
    dr.polygon([(x-60,0),(x+120,0),(x+60,H),(x-120,H)],fill=GOLD+(255,))
    return img
def tracker(g):
    """All nine games: played ones filled in result colour, this one ringed in gold, later ones hollow."""
    n=len(GAMES); sp=170; im=Image.new("RGBA",(sp*n,140),(0,0,0,0)); d=ImageDraw.Draw(im)
    for i,x in enumerate(GAMES):
        cx=sp*i+sp//2; cy=40; r=26 if x is g else 17
        if i+1<g["n"] or x is g:
            col=WIN if res(x)=="W" else LOSS if res(x)=="L" else GOLD
            d.ellipse([cx-r,cy-r,cx+r,cy+r],fill=col+(255,))
            if x is g: d.ellipse([cx-r-7,cy-r-7,cx+r+7,cy+r+7],outline=GOLD+(255,),width=4)
        else: d.ellipse([cx-r,cy-r,cx+r,cy+r],outline=(70,76,86,255),width=3)
        lb=label(x["abbr"],26,BONE if x is g else MUTE,0.14); im.alpha_composite(lb,(cx-lb.width//2,92))
        if i<n-1: d.line([(cx+34,cy),(cx+sp-34,cy)],fill=(60,64,72,255),width=3)
    return im
def ctx_card(g):
    eb,vs,r,sc=gdesc(g); first=load(items_for(g)[0][1][0],1400).resize((W,H)).filter(ImageFilter.GaussianBlur(18))
    return dict(bg=Image.blend(first,Image.new("RGB",(W,H),INK),0.62).convert("RGBA"),eb=label(eb,34,GOLD,0.32),
        vs=text(vs,170 if len(vs)<14 else 140,BONE),r=text(r,300,WIN if r=="W" else LOSS if r=="L" else GOLD),s=text(sc,300,BONE),tr=tracker(g))
def sc_card(f,c):
    t=f/FPS; img=c["bg"].copy(); T=lambda x:x+0.25
    a,dy=up(t,T(0.0),0.45,22); paste(img,c["eb"],(W-c["eb"].width)/2,200,a,dy)
    a,dy=up(t,T(0.15),0.45,22); paste(img,c["vs"],(W-c["vs"].width)/2,262+(170-c["vs"].height)//3,a,dy)
    rule(img,W/2-300,462,600,(t-T(0.3))/0.5)
    a,dy=up(t,T(0.45),0.45,22); sw=c["r"].width+50+c["s"].width; x0=(W-sw)/2
    paste(img,c["r"],x0,520,a,dy); paste(img,c["s"],x0+c["r"].width+50,520,a,dy)
    a,dy=up(t,T(0.9),0.5,14); paste(img,c["tr"],(W-c["tr"].width)/2,850,a,dy)
    return wipe(img,t)
def ctx_section(eb,title,first):
    bg=load(first,1400).resize((W,H)).filter(ImageFilter.GaussianBlur(18))
    return dict(bg=Image.blend(bg,Image.new("RGB",(W,H),INK),0.62).convert("RGBA"),eb=label(eb,34,GOLD,0.32),tt=text(title,200,BONE))
def sc_section(f,c):
    t=f/FPS; img=c["bg"].copy()
    a,dy=up(t,0.25,0.45,22); paste(img,c["eb"],(W-c["eb"].width)/2,370,a,dy)
    a,dy=up(t,0.4,0.45,22); paste(img,c["tt"],(W-c["tt"].width)/2,430,a,dy); rule(img,W/2-200,680,400,(t-0.55)/0.5)
    return wipe(img,t)
# ---------- photo chapters: photos, pairs and clips ----------
def bug_game(g):
    """TV-style score bug: INGLEMOOR 56 | REDMOND 14 | FINAL."""
    won=res(g)=="W"; parts=[label("INGLEMOOR",26,BONE,0.12),text(str(g["us"]),46,BONE,squeeze=0.85),
        label(g["opp"].upper(),26,MUTE,0.12),text(str(g["them"]),46,MUTE,squeeze=0.85)]
    chip=label("FINAL",20,INK,0.2); lg=logo.resize((int(logo.width*44/logo.height),44),Image.LANCZOS)
    hgt=72; wid=6+18+lg.width+22+parts[0].width+16+parts[1].width+34+parts[2].width+16+parts[3].width+26+chip.width+28+22
    b=Image.new("RGBA",(wid,hgt),INK+(225,)); d=ImageDraw.Draw(b); d.rectangle([0,0,5,hgt],fill=GOLD+(255,))
    x=24; b.alpha_composite(lg,(x,(hgt-lg.height)//2)); x+=lg.width+22
    for k,p in enumerate(parts):
        b.alpha_composite(p,(x,(hgt-p.height)//2)); x+=p.width+(16 if k%2==0 else 0)
        if k==1: d.line([(x+17,16),(x+17,hgt-16)],fill=(70,76,86,255),width=2); x+=34
    x+=26; cw=chip.width+28; d.rectangle([x,(hgt-34)//2,x+cw,(hgt+34)//2],fill=(WIN if won else LOSS)+(255,))
    b.alpha_composite(chip,(x+14,(hgt-chip.height)//2)); return b
def bug_tag(t):
    tg=label(t,28,BONE); b=Image.new("RGBA",(tg.width+48,72),INK+(225,)); ImageDraw.Draw(b).rectangle([0,0,5,72],fill=GOLD+(255,))
    b.alpha_composite(tg,(26,(72-tg.height)//2)); return b
class Clip:
    def __init__(s,path,start,dur):
        s.path,s.start=path,start
        if dur is None: dur=float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",path],capture_output=True,text=True).stdout)-0.1
        s.n=int(dur*FPS); s.p=None; s.i=-1; s.last=None
    def frame(s,i):
        i=min(i,s.n-1)
        if s.p is None:
            s.p=subprocess.Popen(["ffmpeg","-loglevel","error","-ss",str(s.start),"-i",s.path,"-t",str(s.n/FPS+0.2),"-an","-vf",
                f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS}","-f","rawvideo","-pix_fmt","rgb24","-"],stdout=subprocess.PIPE)
        while s.i<i:
            buf=s.p.stdout.read(W*H*3)
            if len(buf)<W*H*3: break
            s.last=Image.frombytes("RGB",(W,H),buf); s.i+=1
        return s.last
def fill_of(s): return Image.blend(s.resize((W,H)).filter(ImageFilter.GaussianBlur(28)),Image.new("RGB",(W,H),INK),0.55)
def prep(item):
    kind,a=item
    if kind=="video": c=Clip(*a); return dict(kind="video",clip=c,n=c.n)
    srcs=[load(p) for p in a]; names=[os.path.basename(p) for p in a]
    if kind=="pair": return dict(kind="pair",srcs=srcs,fill=fill_of(srcs[0]),n=PLEN,names=names)
    s=srcs[0]; port=s.width/s.height<1.3
    return dict(kind="portrait" if port else "photo",src=s,fill=fill_of(s) if port else None,n=PLEN,name=names[0])
MOVES=[(1.00,1.10,(0.5,0.42),(0.5,0.38)),(1.12,1.02,(0.56,0.42),(0.48,0.45)),(1.02,1.12,(0.44,0.45),(0.56,0.40)),
       (1.10,1.00,(0.5,0.36),(0.5,0.45)),(1.03,1.11,(0.58,0.44),(0.44,0.42))]
OVERRIDE={"0T6A3593.jpg":(1.16,1.22,(0.45,0.62),(0.42,0.64)),"0T6A3597.jpg":(1.16,1.22,(0.42,0.64),(0.46,0.62))}
def it_frame(it,k,f):
    u=f/(it["n"]+XF)
    if it["kind"]=="video": return it["clip"].frame(f)
    if it["kind"]=="photo":
        z0,z1,(ax,ay),(bx,by)=OVERRIDE.get(it["name"],MOVES[k%len(MOVES)])
        return kb(it["src"],z0+(z1-z0)*u,ax+(bx-ax)*u,ay+(by-ay)*u)
    img=it["fill"].copy()
    if it["kind"]=="portrait":
        s=it["src"]; ph=int(H*0.9*(1+0.04*u)); pw=int(ph*s.width/s.height)
        if pw>W*0.9: pw=int(W*0.9*(1+0.04*u)); ph=int(pw*s.height/s.width)
        img.paste(s.resize((pw,ph),Image.BICUBIC),((W-pw)//2,(H-ph)//2)); return img
    # pair: two photos side by side, each fitted to its half, gentle drift apart
    gap=40; boxw=(W-160-gap)//2; boxh=int(H*0.80); dx=int(10*u)
    for j,s in enumerate(it["srcs"]):
        sc=min(boxw/s.width,boxh/s.height); pw,ph=int(s.width*sc),int(s.height*sc)
        x=80+j*(boxw+gap)+(boxw-pw)//2+(dx if j else -dx); y=(H-ph)//2
        img.paste(Image.new("RGB",(pw+6,ph+6),GOLD),(x-3,y-3)); img.paste(s.resize((pw,ph),Image.LANCZOS),(x,y))
    return img
def ctx_chapter(items,bug):
    its=[prep(x) for x in items]; starts=[]; t=0
    for it in its: starts.append(t); t+=it["n"]
    return dict(its=its,starts=starts,total=t,bug=bug)
def nframes_chapter(items):
    t=0
    for kind,a in items: t+=Clip(*a).n if kind=="video" else PLEN
    return t
def sc_chapter(f,c):
    k=max(i for i,s in enumerate(c["starts"]) if s<=f); it=c["its"][k]; g=f-c["starts"][k]; img=it_frame(it,k,g)
    if k>0 and g<XF and it["kind"]!="video" and c["its"][k-1]["kind"]!="video":
        pv=c["its"][k-1]; img=Image.blend(it_frame(pv,k-1,g+pv["n"]),img,eio(g/XF))
    img=img.convert("RGBA")
    if it["kind"]!="video":       # clips carry their own graphics; keep ours off them
        t=f/FPS; T=c["total"]/FPS; a=eo(t/0.5)*(1-eio((t-(T-0.5))/0.5))
        paste(img,c["bug"],72,H-72-c["bug"].height,a); paste(img,MARK,W-MARK.width-64,52,a)
    return img
# ---------- numbers, hug, coaches, thanks, close ----------
def ctx_numbers():
    return dict(eb=label("2026 SEASON",34,GOLD,0.32),tt=text("BY THE NUMBERS",150,BONE),labs=[label(l,26,MUTE,0.2) for _,l,_ in NUMBERS])
def sc_numbers(f,c):
    t=f/FPS; img=Image.new("RGBA",(W,H),INK+(255,))
    a,dy=up(t,0.0); paste(img,c["eb"],(W-c["eb"].width)/2,170,a,dy); a,dy=up(t,0.2); paste(img,c["tt"],(W-c["tt"].width)/2,225,a,dy)
    tw,th,gap=380,360,36; x0=(W-(4*tw+3*gap))/2; y=470
    for k,((val,_,num),lb) in enumerate(zip(NUMBERS,c["labs"])):
        a,dy=up(t,0.6+0.18*k,0.5,30)
        if a<=0: continue
        x=x0+k*(tw+gap); tile=Image.new("RGBA",(tw,th),PANEL+(255,)); ImageDraw.Draw(tile).rectangle([0,0,tw,4],fill=GOLD+(255,))
        shown=val if num is None else str(int(round(num*eio((t-0.6-0.18*k)/1.3))))
        v=text(shown,170,GOLD if k==0 else BONE); tile.alpha_composite(v,((tw-v.width)//2,70)); tile.alpha_composite(lb,((tw-lb.width)//2,280))
        paste(img,tile,x,y,a,dy)
    return img
def ctx_hug(): s=load(HUG); return dict(s=s,fill=fill_of(s))
def sc_hug(f,c):
    t=f/FPS; u=t/6; img=c["fill"].copy(); s=c["s"]; ph=int(H*0.9*(1+0.05*eio(u))); pw=int(ph*s.width/s.height)
    img.paste(s.resize((pw,ph),Image.BICUBIC),((W-pw)//2,(H-ph)//2))
    k=eio(t/0.8)*(1-eio((t-5.2)/0.8)); return Image.blend(Image.new("RGB",(W,H),INK),img,k).convert("RGBA")
def ctx_coaches(team):
    cards=[]
    for cc in [x for x in coaches if x["team"]==team]:
        ph=Image.open(f"{REPO}/{cc['photo']}").convert("RGB").resize((300,300),Image.LANCZOS); role=cc["role"].split(",")[0]
        rl=label(role.upper(),20,GOLD,0.14)
        if rl.width>340 and " / " in role:
            a_,b_=role.upper().split(" / ",1); l1=label(a_+" /",20,GOLD,0.14); l2=label(b_,20,GOLD,0.14)
            rl=Image.new("RGBA",(max(l1.width,l2.width),l1.height+l2.height+8),(0,0,0,0)); rl.alpha_composite(l1,((rl.width-l1.width)//2,0)); rl.alpha_composite(l2,((rl.width-l2.width)//2,l1.height+8))
        if rl.width>350: rl=rl.resize((350,int(rl.height*350/rl.width)),Image.LANCZOS)
        cards.append((ph,text(f"{cc['first']} {cc['last']}".upper(),56,BONE),rl))
    return dict(cards=cards,eb=label("THANK YOU, COACHES",34,GOLD,0.32),tt=text(team.upper()+" STAFF",120,BONE))
def sc_coaches(f,c):
    t=f/FPS; img=Image.new("RGBA",(W,H),INK+(255,))
    a,dy=up(t,0.0); paste(img,c["eb"],(W-c["eb"].width)/2,90,a,dy); a,dy=up(t,0.2); paste(img,c["tt"],(W-c["tt"].width)/2,140,a,dy)
    rows=[c["cards"][:4],c["cards"][4:]] if len(c["cards"])>4 else [c["cards"]]; cw=380; y=330 if len(rows)>1 else 420; k=0
    for row in rows:
        x0=(W-cw*len(row))/2
        for j,(ph,nm,rl) in enumerate(row):
            a,dy=up(t,0.45+0.12*k,0.5,30); cx=x0+cw*j+cw/2
            if a>0:
                fr=Image.new("RGBA",(306,306),GOLD+(255,)); fr.paste(ph,(3,3)); ff=fr.resize((226,226),Image.LANCZOS); paste(img,ff,cx-113,y,a,dy)
                nm2=nm if nm.width<=cw-30 else nm.resize((cw-30,int(nm.height*(cw-30)/nm.width)),Image.LANCZOS)
                paste(img,nm2,cx-nm2.width/2,y+244,a,dy); paste(img,rl,cx-rl.width/2,y+244+nm2.height+12,a,dy)
            k+=1
        y+=360
    return img
def ctx_thanks():
    tiles=[]
    for s in sponsors:
        tw,th=(380,200) if s["tier"]=="gold" else (250,130)
        tl=Image.new("RGBA",(tw,th),BONE+(255,)); lg=Image.open(f"{REPO}/{s['logo']}").convert("RGBA"); lg.thumbnail((tw-36,th-30),Image.LANCZOS)
        tl.alpha_composite(lg,((tw-lg.width)//2,(th-lg.height)//2)); tiles.append((s["tier"],tl))
    return dict(tiles=tiles,eb=label("THANK YOU",34,GOLD,0.32),tt=text("BOOSTERS & SPONSORS",120,BONE),ft=label("IHS VIKING GRIDIRON BOOSTER CLUB  ·  INGLEMOORFOOTBALL.COM",28,MUTE,0.22))
def sc_thanks(f,c):
    t=f/FPS; img=Image.new("RGBA",(W,H),INK+(255,))
    a,dy=up(t,0.0); paste(img,c["eb"],(W-c["eb"].width)/2,70,a,dy); a,dy=up(t,0.2); paste(img,c["tt"],(W-c["tt"].width)/2,118,a,dy)
    gold=[x for tr,x in c["tiles"] if tr=="gold"]; rest=[x for tr,x in c["tiles"] if tr!="gold"]; k=0
    for row,y in zip([gold,rest[:6],rest[6:]],[300,530,690]):
        gap=24; tot=sum(x.width for x in row)+gap*(len(row)-1); x=(W-tot)/2
        for tl in row: a,dy=up(t,0.5+0.07*k,0.45,26); paste(img,tl,x,y,a,dy); x+=tl.width+gap; k+=1
    a,dy=up(t,0.6+0.07*k); paste(img,c["ft"],(W-c["ft"].width)/2,900,a,dy); return img
def ctx_close(): return dict(lg=logo.resize((int(logo.width*150/logo.height),150),Image.LANCZOS),one=text("ONE TEAM.",210,BONE),all=text("ALL IN.",210,GOLD))
def sc_close(f,c):
    t=f/FPS; img=Image.new("RGBA",(W,H),INK+(255,))
    a,dy=up(t,0.0,0.6); paste(img,c["lg"],(W-c["lg"].width)/2,190,a,dy); a,dy=up(t,0.35,0.6); paste(img,c["one"],(W-c["one"].width)/2,390,a,dy)
    a,dy=up(t,0.8,0.6); paste(img,c["all"],(W-c["all"].width)/2,600,a,dy); rule(img,W/2-200,850,400,(t-1.2)/0.6)
    fade=eio((t-4.4)/0.6)
    return Image.blend(img,Image.new("RGBA",(W,H),INK+(255,)),fade) if fade>0 else img

def plan():
    P_=[("000_logo",3*FPS,"logo",None),("010_hero",6*FPS,"hero",None),("020_team",6*FPS,"team",None),
        ("030_sec_summer",3*FPS,"section",("BEFORE THE SEASON","SUMMER",SUMMER[0][1][0])),
        ("035_ch_summer",nframes_chapter(SUMMER),"chapter",(SUMMER,"tag:SUMMER 2026")),
        ("040_sec_media",3*FPS,"section",("AUGUST 19","MEDIA DAY",MEDIA[0][1][0])),
        ("045_ch_media",nframes_chapter(MEDIA),"chapter",(MEDIA,"tag:MEDIA DAY  ·  AUG 19"))]
    for k,g in enumerate(SHOW):
        it=items_for(g); P_.append((f"{100+k*10:03d}_card_{g['date']}",3*FPS,"card",g))
        P_.append((f"{105+k*10:03d}_ch_{g['date']}",nframes_chapter(it),"chapter",(it,g)))
    P_+=[("700_numbers",8*FPS,"numbers",None),("750_hug",6*FPS,"hug",None),("800_coaches_v",9*FPS,"coaches","Varsity"),
         ("810_coaches_c",7*FPS,"coaches","C Team"),("900_thanks",10*FPS,"thanks",None),("990_close",5*FPS,"close",None)]
    return P_
def mkctx(kind,arg):
    if kind=="chapter":
        items,b=arg; return ctx_chapter(items,bug_tag(b[4:]) if isinstance(b,str) else bug_game(b))
    if kind=="section": return ctx_section(*arg)
    return {"logo":ctx_logo,"hero":ctx_hero,"team":ctx_team,"numbers":ctx_numbers,"hug":ctx_hug,"thanks":ctx_thanks,"close":ctx_close}[kind]() if arg is None else \
           {"card":ctx_card,"coaches":ctx_coaches}[kind](arg)
SC={"logo":sc_logo,"hero":sc_hero,"team":sc_team,"section":sc_section,"chapter":sc_chapter,"card":sc_card,"numbers":sc_numbers,
    "hug":sc_hug,"coaches":sc_coaches,"thanks":sc_thanks,"close":sc_close}
def render(item):
    name,nf,kind,arg=item; final=f"{OUT}/{name}.mp4"
    if os.path.exists(final): return name+" (kept)"
    c=mkctx(kind,arg); tmp=f"{OUT}/{name}.tmp.mp4"
    p=subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
        "-vf","noise=alls=3:allf=t","-c:v","libx264","-preset","fast","-crf","20","-pix_fmt","yuv420p","-g","60","-threads","1",tmp],stdin=subprocess.PIPE)
    for f in range(nf): p.stdin.write(finish(SC[kind](f,c).convert("RGB")).tobytes())
    p.stdin.close(); assert p.wait()==0; os.replace(tmp,final); return f"{name} {nf}f"
if __name__=="__main__":
    PL=plan(); total=sum(x[1] for x in PL)/FPS
    if MODE=="plan":
        for x in PL: print(f"{x[0]:24} {x[1]/FPS:6.1f}s")
        print("TOTAL",round(total,1),f"= {int(total//60)}:{int(total%60):02d}","| numbers:",NUMBERS)
    elif MODE=="stills":
        want=sys.argv[3].split(",")
        for name,nf,kind,arg in PL:
            for w in want:
                nm,_,fr=w.partition("@")
                if name.startswith(nm):
                    c=mkctx(kind,arg); f=int(float(fr)*FPS) if fr else int(nf*0.8)
                    finish(SC[kind](f,c).convert("RGB")).save(f"{OUT}/still_{name}_{fr or 'x'}.jpg",quality=85)
        print("stills ok")
    elif MODE=="render":
        with Pool(2) as pool:
            for r in pool.imap_unordered(render,sorted(PL,key=lambda x:-x[1])): print(r,flush=True)
