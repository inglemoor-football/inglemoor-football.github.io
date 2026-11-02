import sys,os
from PIL import Image, ImageOps, ImageDraw
src,out=sys.argv[1],sys.argv[2]
for g in sorted(os.listdir(src)):
    fs=sorted(f for f in os.listdir(os.path.join(src,g)) if f.lower().endswith('.jpg'))
    cols=4; cw,ch=420,280; rows=(len(fs)+cols-1)//cols
    sh=Image.new('RGB',(cols*cw,rows*(ch+22)),'white'); d=ImageDraw.Draw(sh)
    for i,f in enumerate(fs):
        im=Image.open(os.path.join(src,g,f)); im.draft('RGB',(cw*2,ch*2)); im=ImageOps.exif_transpose(im).convert('RGB'); im.thumbnail((cw-8,ch-8))
        x,y=(i%cols)*cw,(i//cols)*(ch+22); sh.paste(im,(x+(cw-im.width)//2,y+(ch-im.height)//2)); d.text((x+6,y+ch+4),f"{i+1}. {f}",fill='black')
    sh.save(os.path.join(out,f'sheet-{g}.jpg'),quality=80)
