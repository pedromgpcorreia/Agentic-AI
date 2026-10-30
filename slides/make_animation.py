import sys,io,os;sys.argv=["x","--gif"];ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path[:0]=[ROOT,ROOT+"/visualization"]
import live
from PIL import Image
A=ROOT+"/slides/assets/"
v=live.LiveView();v.radio.set_active(1);v.setup();D=95;fr=[]
def grab():
    b=io.BytesIO();v.fig.savefig(b,dpi=D,format="png");im=Image.open(b).convert("RGB");W,H=im.size;k=W/1430
    out=Image.new("RGB",(int(1350*k),int(545*k)),"#ffffff")
    out.paste(im.crop((int(110*k),int(38*k),int(660*k),int(583*k))),(0,0))          # network, without the title date
    out.paste(im.crop((int(745*k),int(40*k),int(1410*k),int(385*k))),(int(600*k),int(60*k)))  # shares and prices
    fr.append(out.quantize(64,dither=Image.Dither.NONE))
grab()
for _ in range(48):v.step();grab()
fr[0].save(A+"live_clean.gif",save_all=True,append_images=fr[1:],duration=250,loop=0,optimize=True)
