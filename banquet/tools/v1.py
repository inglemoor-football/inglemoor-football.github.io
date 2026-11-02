import sys, os, re, math, json, datetime, subprocess, numpy as np
from multiprocessing import Pool
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageFilter
S=sys.argv[1]; MODE=sys.argv[2]
REPO="/home/claude/inglemoor-football.github.io"; SRC=f"{S}/v1/src"; OUT=f"{S}/v1/out"; os.makedirs(OUT,exist_ok=True)
W,H,FPS=1920,1080,30
INK=(10,11,13); PANEL=(20,22,26); GOLD=(254,183,46); BONE=(244,241,233); MUTE=(138,146,158); WIN=(92,184,127); LOSS=(196,87,75)
BLACK_F="/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"; COND_F="/usr/share/fonts/opentype/inter/Inter-Bold.otf"; SEMI_F="/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
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
def load(p,maxw=2880):
    im=Image.open(p); im.draft("RGB",(maxw,maxw)); im=ImageOps.exif_transpose(im).convert("RGB")
    if im.width>maxw: im=im.resize((maxw,int(im.height*maxw/im.width)),Image.LANCZOS)
    return im
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
def up(t,t0,d=0.55,dist=24): a=eo((t-t0)/d); return a,dist*(1-a)

# ---------- data ----------
html=open(f"{REPO}/index.html",encoding="utf-8").read()
GAMES=[]
for m in re.finditer(r'\{ date:"([\d-]+)", time:"[^"]*", opp:"([^"]*)"[^}]*?at:"(\w+)"[^}]*?us:(\d+), them:(\d+)',html):
    GAMES.append(dict(date=m[1],opp=m[2],at=m[3],us=int(m[4]),them=int(m[5])))
for i,g in enumerate(GAMES): g["n"]=i+1
FOLDER={"2026-09-05":"Juanita","2026-09-11":"Highline","2026-09-18":"9-18-MercerIsland","2026-09-25":"Interlake","2026-10-02":"Newport",
        "2026-10-09":"10-9-at-Redmond","2026-10-16":"10-16-at-LW","2026-10-24":"Liberty"}
SHOW=[g for g in GAMES if g["date"] in FOLDER]          # Newport and the play-in are skipped, as agreed
W_,L_=sum(g["us"]>g["them"] for g in GAMES),sum(g["us"]<g["them"] for g in GAMES)
coaches=[dict(team=m[1],first=m[2],last=m[3],photo=m[4],role=m[5]) for m in re.finditer(
    r'\{ team:"([^"]+)", first:"([^"]+)", last:"([^"]+)", photo:"([^"]+)",\s*role:"([^"]+)"',html)]
sponsors=[dict(name=m[1],tier=m[2],logo=m[3]) for m in re.finditer(r'\{ name:"([^"]+)",\s*tier:"(\w+)",\s*logo:"([^"]+)"',html)]
def gdesc(g):
    d=datetime.date.fromisoformat(g["date"]); day=d.strftime("%a").upper(); mon=d.strftime("%b").upper()
    vs=("AT " if g["at"]=="away" else "VS ")+g["opp"].upper()
    res=("W" if g["us"]>g["them"] else "L" if g["us"]<g["them"] else "T")
    return f"GAME {g['n']}  ·  {day} {mon} {d.day}", vs, res, f"{g['us']}–{g['them']}"
def photos_for(g):
    d=f"{SRC}/{FOLDER[g['date']]}"; return [f"{d}/{f}" for f in sorted(os.listdir(d)) if f.lower().endswith(".jpg")]

# ---------- scenes ----------
logo=Image.open(f"{REPO}/images/viking-v-original.png").convert("RGBA")
def sc_logo(f,ctx):
    t=f/FPS; img=Image.new("RGBA",(W,H),INK+(255,))
    s=0.86+0.14*eo(t/0.9); lh=int(430*s); lg=logo.resize((int(logo.width*lh/logo.height),lh),Image.LANCZOS)
    paste(img,lg,(W-lg.width)/2,(H-lg.height)/2-60,eo(t/0.7)); rule(img,W/2-260,H/2+215,520,(t-0.5)/0.7)
    ft=ctx["foot"]; a,dy=up(t,0.9); paste(img,ft,(W-ft.width)/2,H/2+250,a,dy); return img
def ctx_logo(): return dict(foot=label("INGLEMOOR VIKING FOOTBALL  ·  2026",30,MUTE,0.24))
def ctx_hero():
    return dict(src=load(f"{S}/banquet/hero.jpg"),gl=gleft(),eb=label("2026 SEASON",34,GOLD,0.32),
        ing=text("INGLEMOOR",215,BONE),vf=text("VIKING FOOTBALL",104,GOLD),rec=text(f"{W_}–{L_}",200,BONE),lab=label("KINGCO MOUNTAIN 3A"))
def sc_hero(f,c):
    t=f/FPS; bg=kb(c["src"],1.22+0.07*eio(t/6),0.40,0.42).convert("RGBA"); bg.alpha_composite(c["gl"])
    a,dy=up(t,0.3); paste(bg,c["eb"],120,300,a,dy); rule(bg,120,350,90,(t-0.3)/0.5)
    a,dy=up(t,0.7); paste(bg,c["ing"],112,385,a,dy); a,dy=up(t,1.1); paste(bg,c["vf"],118,585,a,dy)
    a,dy=up(t,2.2); paste(bg,c["rec"],116,735,a,dy); paste(bg,c["lab"],124,925,a,dy); return bg
def ctx_team():
    tp=Image.open(f"{REPO}/images/team-2026.jpg").convert("RGB")
    bgr=tp.resize((W,int(tp.height*W/tp.width))).resize((W,H)).filter(ImageFilter.GaussianBlur(30))
    bgr=Image.blend(bgr,Image.new("RGB",(W,H),INK),0.72)
    return dict(tp=tp,bg=bgr,eb=label("THE 2026 INGLEMOOR VIKINGS",34,GOLD,0.32))
def sc_team(f,c):
    t=f/FPS; img=c["bg"].convert("RGBA"); pw=int(W*0.86); ph=int(pw*c["tp"].height/c["tp"].width)
    z=1.0+0.04*eio(t/6); shot=kb(c["tp"],z,0.5,0.5,(pw,ph)).convert("RGBA")
    a,dy=up(t,0.0,0.8,30); y0=(H-ph)/2+40
    ImageDraw.Draw(img).rectangle([(W-pw)/2-1,y0-3+dy,(W+pw)/2,y0+dy],fill=GOLD+(int(255*a),)) if a>0 else None
    paste(img,shot,(W-pw)/2,y0,a,dy); a2,dy2=up(t,0.6); paste(img,c["eb"],(W-c["eb"].width)/2,y0-80,a2,dy2); return img
LINES=Image.new("RGBA",(W,H),(0,0,0,0)); _d=ImageDraw.Draw(LINES)
for _x in range(0,W,96): _d.line([(_x,0),(_x,H)],fill=(254,183,46,20))
def ctx_card(g):
    eb,vs,res,sc=gdesc(g); first=load(photos_for(g)[0],1400).resize((W,H)).filter(ImageFilter.GaussianBlur(18))
    vst=text(vs,170 if len(vs)<14 else 140,BONE)
    return dict(bg=Image.blend(first,Image.new("RGB",(W,H),INK),0.62).convert("RGBA"),eb=label(eb,34,GOLD,0.32),vs=vst,
                r=text(res,300,WIN if res=="W" else LOSS if res=="L" else GOLD),s=text(sc,300,BONE))
def sc_card(f,c):
    t=f/FPS; img=c["bg"].copy(); img.alpha_composite(LINES)
    a,dy=up(t,0.0,0.45,22); paste(img,c["eb"],(W-c["eb"].width)/2,250,a,dy)
    a,dy=up(t,0.2,0.45,22); paste(img,c["vs"],(W-c["vs"].width)/2,315+(170-c["vs"].height)//3,a,dy)
    rule(img,W/2-300,515,600,(t-0.35)/0.5)
    a,dy=up(t,0.6,0.45,22); sw=c["r"].width+50+c["s"].width; x0=(W-sw)/2
    paste(img,c["r"],x0,580,a,dy); paste(img,c["s"],x0+c["r"].width+50,580,a,dy); return img
# Ken Burns moves cycle so consecutive photos never move the same way
MOVES=[(1.00,1.10,(0.5,0.42),(0.5,0.38)),(1.12,1.02,(0.56,0.42),(0.48,0.45)),(1.02,1.12,(0.44,0.45),(0.56,0.40)),
       (1.10,1.00,(0.5,0.36),(0.5,0.45)),(1.03,1.11,(0.58,0.44),(0.44,0.42))]
def ctx_photos(g):
    eb,vs,res,sc=gdesc(g); srcs=[load(p) for p in photos_for(g)]
    tag=label(f"{vs}  ·  {res} {sc}",30,BONE); box=Image.new("RGBA",(tag.width+48,tag.height+30),INK+(200,))
    ImageDraw.Draw(box).rectangle([0,0,4,box.height],fill=GOLD+(255,)); box.alpha_composite(tag,(28,15))
    fills=[ (Image.blend(s.resize((W,H)).filter(ImageFilter.GaussianBlur(28)),Image.new("RGB",(W,H),INK),0.55) if s.width/s.height<1.3 else None) for s in srcs]
    return dict(srcs=srcs,fills=fills,tag=box,n=len(srcs),names=[os.path.basename(p) for p in photos_for(g)])
# per-photo moves where the default would show something we don't want
OVERRIDE={"0T6A3593.jpg":(1.16,1.22,(0.45,0.62),(0.42,0.64)),   # blown-out video board, top right
          "0T6A3597.jpg":(1.16,1.22,(0.42,0.64),(0.46,0.62))}
def ph_frame(c,i,f):
    s=c["srcs"][i]; z0,z1,(ax,ay),(bx,by)=OVERRIDE.get(c["names"][i],MOVES[i%len(MOVES)]); u=f/(PLEN+XF)
    if c["fills"][i] is not None:        # portrait: whole photo over a blurred fill
        img=c["fills"][i].copy(); ph=int(H*0.92*(1+0.04*u)); pw=int(ph*s.width/s.height)
        img.paste(s.resize((pw,ph),Image.BICUBIC),((W-pw)//2,(H-ph)//2)); return img
    return kb(s,z0+(z1-z0)*u,ax+(bx-ax)*u,ay+(by-ay)*u)
def sc_photos(f,c):
    i=min(f//PLEN,c["n"]-1); g=f-i*PLEN; img=ph_frame(c,i,g)
    if i>0 and g<XF: img=Image.blend(ph_frame(c,i-1,g+PLEN),img,eio(g/XF))
    img=img.convert("RGBA"); t=f/FPS; T=c["n"]*PLEN/FPS
    a=eo(t/0.5)*(1-eio((t-(T-0.5))/0.5)); paste(img,c["tag"],80,H-80-c["tag"].height,a); return img
def ctx_coaches(team):
    cs=[c for c in coaches if c["team"]==team]; cards=[]
    for c in cs:
        ph=Image.open(f"{REPO}/{c['photo']}").convert("RGB").resize((300,300),Image.LANCZOS)
        role=re.split(r",",c["role"])[0]
        rl=label(role.upper(),20,GOLD,0.14)
        if rl.width>340 and " / " in role:     # two lines rather than run into the next coach
            a_,b_=role.upper().split(" / ",1); l1=label(a_+" /",20,GOLD,0.14); l2=label(b_,20,GOLD,0.14)
            rl=Image.new("RGBA",(max(l1.width,l2.width),l1.height+l2.height+8),(0,0,0,0))
            rl.alpha_composite(l1,((rl.width-l1.width)//2,0)); rl.alpha_composite(l2,((rl.width-l2.width)//2,l1.height+8))
        if rl.width>350: rl=rl.resize((350,int(rl.height*350/rl.width)),Image.LANCZOS)
        cards.append((ph,text(f"{c['first']} {c['last']}".upper(),56,BONE),rl))
    return dict(cards=cards,eb=label("THANK YOU, COACHES",34,GOLD,0.32),tt=text(team.upper()+" STAFF",120,BONE))
def sc_coaches(f,c):
    t=f/FPS; img=Image.new("RGBA",(W,H),INK+(255,)); img.alpha_composite(LINES)
    a,dy=up(t,0.0); paste(img,c["eb"],(W-c["eb"].width)/2,90,a,dy); a,dy=up(t,0.2); paste(img,c["tt"],(W-c["tt"].width)/2,140,a,dy)
    n=len(c["cards"]); rows=[c["cards"][:4],c["cards"][4:]] if n>4 else [c["cards"]]
    cw=380; y=330 if len(rows)>1 else 420
    k=0
    for row in rows:
        x0=(W-cw*len(row))/2
        for j,(ph,nm,rl) in enumerate(row):
            a,dy=up(t,0.45+0.12*k,0.5,30); cx=x0+cw*j+cw/2
            if a>0:
                fr=Image.new("RGBA",(306,306),GOLD+(255,)); fr.paste(ph,(3,3)); ff=fr.resize((226,226),Image.LANCZOS)
                paste(img,ff,cx-113,y,a,dy)
                nm2=nm if nm.width<=cw-30 else nm.resize((cw-30,int(nm.height*(cw-30)/nm.width)),Image.LANCZOS)
                paste(img,nm2,cx-nm2.width/2,y+244,a,dy); paste(img,rl,cx-rl.width/2,y+244+nm2.height+12,a,dy)
            k+=1
        y+=360
    return img
def ctx_thanks():
    tiles=[]
    for s in sponsors:
        big=s["tier"]=="gold"; tw,th=(380,200) if big else (250,130)
        tl=Image.new("RGBA",(tw,th),BONE+(255,)); lg=Image.open(f"{REPO}/{s['logo']}").convert("RGBA"); lg.thumbnail((tw-36,th-30),Image.LANCZOS)
        tl.alpha_composite(lg,((tw-lg.width)//2,(th-lg.height)//2)); tiles.append((s["tier"],tl))
    return dict(tiles=tiles,eb=label("THANK YOU",34,GOLD,0.32),tt=text("BOOSTERS & SPONSORS",120,BONE),
                ft=label("IHS VIKING GRIDIRON BOOSTER CLUB  ·  INGLEMOORFOOTBALL.COM",28,MUTE,0.22))
def sc_thanks(f,c):
    t=f/FPS; img=Image.new("RGBA",(W,H),INK+(255,)); img.alpha_composite(LINES)
    a,dy=up(t,0.0); paste(img,c["eb"],(W-c["eb"].width)/2,70,a,dy); a,dy=up(t,0.2); paste(img,c["tt"],(W-c["tt"].width)/2,118,a,dy)
    gold=[x for tr,x in c["tiles"] if tr=="gold"]; rest=[x for tr,x in c["tiles"] if tr!="gold"]
    rows=[gold,rest[:6],rest[6:]]; ys=[300,530,690]; k=0
    for row,y in zip(rows,ys):
        if not row: continue
        gap=24; tot=sum(x.width for x in row)+gap*(len(row)-1); x=(W-tot)/2
        for tl in row:
            a,dy=up(t,0.5+0.07*k,0.45,26); paste(img,tl,x,y,a,dy); x+=tl.width+gap; k+=1
    a,dy=up(t,0.6+0.07*k); paste(img,c["ft"],(W-c["ft"].width)/2,900,a,dy); return img
def ctx_close(): return dict(lg=logo.resize((int(logo.width*150/logo.height),150),Image.LANCZOS),one=text("ONE TEAM.",210,BONE),all=text("ALL IN.",210,GOLD))
def sc_close(f,c):
    t=f/FPS; img=Image.new("RGBA",(W,H),INK+(255,))
    a,dy=up(t,0.0,0.6); paste(img,c["lg"],(W-c["lg"].width)/2,190,a,dy)
    a,dy=up(t,0.35,0.6); paste(img,c["one"],(W-c["one"].width)/2,390,a,dy)
    a,dy=up(t,0.8,0.6); paste(img,c["all"],(W-c["all"].width)/2,600,a,dy); rule(img,W/2-200,850,400,(t-1.2)/0.6)
    fade=eio((t-4.4)/0.6)
    if fade>0: img=Image.blend(img,Image.new("RGBA",(W,H),INK+(255,)),fade)
    return img

def plan():
    P=[("000_logo",3*FPS,"logo",None),("010_hero",6*FPS,"hero",None),("020_team",6*FPS,"team",None)]
    for k,g in enumerate(SHOW):
        P.append((f"{100+k*10:03d}_card_{g['date']}",3*FPS,"card",g))
        P.append((f"{105+k*10:03d}_photos_{g['date']}",len(photos_for(g))*PLEN,"photos",g))
    P+=[("800_coaches_v",9*FPS,"coaches","Varsity"),("810_coaches_c",7*FPS,"coaches","C Team"),
        ("900_thanks",10*FPS,"thanks",None),("990_close",5*FPS,"close",None)]
    return P
CTX={"logo":lambda a:ctx_logo(),"hero":lambda a:ctx_hero(),"team":lambda a:ctx_team(),"card":ctx_card,"photos":ctx_photos,
     "coaches":ctx_coaches,"thanks":lambda a:ctx_thanks(),"close":lambda a:ctx_close()}
SC={"logo":sc_logo,"hero":sc_hero,"team":sc_team,"card":sc_card,"photos":sc_photos,"coaches":sc_coaches,"thanks":sc_thanks,"close":sc_close}

def render(item):
    name,nf,kind,arg=item; final=f"{OUT}/{name}.mp4"
    if os.path.exists(final): return name+" (kept)"
    c=CTX[kind](arg); tmp=f"{OUT}/{name}.tmp.mp4"
    p=subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
        "-vf","noise=alls=3:allf=t","-c:v","libx264","-preset","fast","-crf","20","-pix_fmt","yuv420p","-g","60","-threads","1",tmp],stdin=subprocess.PIPE)
    for f in range(nf): p.stdin.write(finish(SC[kind](f,c).convert("RGB")).tobytes())
    p.stdin.close(); assert p.wait()==0; os.replace(tmp,final); return f"{name} {nf}f"

if __name__=="__main__":
    P=plan(); total=sum(x[1] for x in P)/FPS
    if MODE=="plan":
        for x in P: print(f"{x[0]:28} {x[1]/FPS:6.1f}s")
        print("TOTAL", round(total,1),"s =",f"{int(total//60)}:{int(total%60):02d}"); print("games:",[(g['opp'],g['us'],g['them']) for g in SHOW]); print(len(coaches),"coaches",len(sponsors),"sponsors")
    elif MODE=="crops":   # end-of-move crop for every landscape photo, to catch cut-off heads
        for g in SHOW:
            c=ctx_photos(g); ims=[]
            for i in range(c["n"]):
                a=ph_frame(c,i,0).resize((384,216)); b=ph_frame(c,i,PLEN+XF-1).resize((384,216)); ims.append((a,b))
            sh=Image.new("RGB",(4*790,((len(ims)+3)//4)*230),"white")
            for j,(a,b) in enumerate(ims): x=(j%4)*790; y=(j//4)*230; sh.paste(a,(x,y)); sh.paste(b,(x+390,y))
            sh.save(f"{OUT}/crops_{g['date']}.jpg",quality=78)
        print("crops ok")
    elif MODE=="stills":
        for name,nf,kind,arg in P:
            if kind in ("team","coaches","thanks") or name.startswith("100_card") or name.startswith("120_card"):
                c=CTX[kind](arg); finish(SC[kind](int(nf*0.8),c).convert("RGB")).save(f"{OUT}/still_{name}.jpg",quality=86)
        print("stills ok")
    elif MODE=="render":
        with Pool(2) as pool:
            for r in pool.imap_unordered(render,sorted(P,key=lambda x:-x[1])): print(r,flush=True)
