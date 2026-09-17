import numpy as np

N=64; STEPS=190; SCALE=.01; TR=.16; FORB=.70


N=64; STEPS=190; SCALE=.01; TR=.16; FORB=.70


N=64; STEPS=190; SCALE=.01; TR=.16; FORB=.70


N=64; STEPS=190; SCALE=.01; TR=.16; FORB=.70


N=64; STEPS=190; SCALE=.01; TR=.16; FORB=.70


def gv(x,y,cx,cy,s): return np.exp(-((x-cx)**2+(y-cy)**2)/(2*s*s))


def gg(x,y,cx,cy,s):
    v=gv(x,y,cx,cy,s); gx=v*(cx-x)/(s*s); gy=v*(cy-y)/(s*s); n=np.sqrt(gx*gx+gy*gy); ox=np.zeros_like(gx); oy=np.zeros_like(gy); m=n>1e-12; ox[m]=gx[m]/n[m]; oy[m]=gy[m]/n[m]; return ox,oy


def gains(A,B):
    A=np.clip(A,0,1); B=np.clip(B,0,1); A25=A**2.5; lim=.34+.66*A25; t=3*np.clip(1-(B/lim)**2,0,1); th=.018+.42*A25; a=3*np.clip((B-th)/.18,0,1)**1.15; return t,a


def ru(rng,n):
    v=rng.normal(size=(n,2)); q=np.linalg.norm(v,axis=1); m=q>1e-12; v[m]/=q[m,None]; v[~m]=0; return v


def runA(w,seed, observer=None):
    rng=np.random.default_rng(seed); p=np.column_stack([rng.uniform(.05,.18,N),rng.uniform(.43,.57,N)]); hit=np.zeros(N,bool); tx,ty,sa=w['A']; hx,hy,sb=w['B']
    if observer is not None: observer(0, p.copy())
    for _ in range(STEPS):
        x,y=p[:,0],p[:,1]; A=gv(x,y,tx,ty,sa); B=gv(x,y,hx,hy,sb); hit|=B>=FORB; t,a=gains(A,B); ax,ay=gg(x,y,tx,ty,sa); bx,by=gg(x,y,hx,hy,sb); noise=w['random_motion_rms_per_tick']*ru(rng,N); p[:,0]+=noise[:,0]+SCALE*(t*ax-a*bx); p[:,1]+=noise[:,1]+SCALE*(t*ay-a*by); p=np.clip(p,0,1)
        if observer is not None: observer(_+1, p.copy())
    d=np.linalg.norm(p-np.array([tx,ty]),axis=1); target=float(np.mean(d<=TR)); forb=float(np.mean(hit)); return {'world':w['id'],'stratum':w['stratum'],'seed':seed,'target_occupancy':target,'forbidden_entry_fraction':forb,'mean_final_distance':float(np.mean(d)),'task_pass':bool(target>=.8 and forb<=.1),'runtime_integrity':True,'cell_count':64}


