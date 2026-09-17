from __future__ import annotations
import numpy as np

POP=64
STEPS=220
COMM=0.38
SIGMA=0.14
SCALE=0.012
MAX_STEP=0.016
CONNECTIVITY=0.15
OVERCROWD=0.025
GROUP_RADIUS=0.05
REP_RADIUS=0.05
DENSITY_RADIUS=0.10

def clip(x,lo,hi):
    if x < lo: return lo
    if x > hi: return hi
    return x

def safe_div(a,b):
    if abs(b) <= 1e-12: return 0.0
    return a/b

def linker_weights(cohesion_magnitude, group_cohesion_magnitude,
                   nearest_neighbor_distance, local_density, noise_rms):
    d = 0.03 + 0.02 * (local_density + noise_rms)
    r = d / (nearest_neighbor_distance + d)
    return (0.2 * (1.0 - r), 0.8 * (1.0 - r), r)

def core(p,dirs,interaction,noise, observer=None):
    n=p.shape[0]; s2=2.0*SIGMA*SIGMA
    if observer is not None: observer(0, p.copy())
    for t in range(STEPS):
        coh=np.zeros((n,2)); den=np.zeros(n); rep=np.zeros((n,2)); dist=np.full((n,n),1e9); density=np.zeros(n)
        for i in range(n):
            xi=p[i,0]; yi=p[i,1]
            for j in range(n):
                if i==j: continue
                dx=p[j,0]-xi; dy=p[j,1]-yi; d2=dx*dx+dy*dy
                if d2<=1e-24: continue
                d=np.sqrt(d2); dist[i,j]=d; ux=dx/d; uy=dy/d
                if interaction and d<=COMM:
                    w=np.exp(-d2/s2); coh[i,0]+=w*ux; coh[i,1]+=w*uy; den[i]+=w
                if d<REP_RADIUS:
                    rw=(REP_RADIUS-d)/REP_RADIUS; rep[i,0]-=rw*ux; rep[i,1]-=rw*uy
                if d<DENSITY_RADIUS:
                    density[i]+=1.0
        cvec=np.zeros((n,2)); cmag=np.zeros(n); dmin=np.full(n,1e9)
        for i in range(n):
            if interaction and den[i]>1e-12:
                cvec[i,0]=coh[i,0]/den[i]; cvec[i,1]=coh[i,1]/den[i]
            cmag[i]=np.sqrt(cvec[i,0]*cvec[i,0]+cvec[i,1]*cvec[i,1])
            for j in range(n):
                if dist[i,j]<dmin[i]: dmin[i]=dist[i,j]
            density[i]/=(n-1.0)

        # Spacing-connected local components for consensus cohesion.
        label=np.full(n,-1); comp=0; stack=np.empty(n,np.int64)
        for start in range(n):
            if label[start]>=0: continue
            top=0; stack[top]=start; top+=1; label[start]=comp
            while top>0:
                top-=1; i=stack[top]
                for j in range(n):
                    if label[j]<0 and dist[i,j]<GROUP_RADIUS:
                        label[j]=comp; stack[top]=j; top+=1
            comp+=1
        group=np.zeros((comp,2)); count=np.zeros(comp)
        for i in range(n):
            c=label[i]; group[c,0]+=cvec[i,0]; group[c,1]+=cvec[i,1]; count[c]+=1.0
        for c in range(comp):
            if count[c]>0:
                group[c,0]/=count[c]; group[c,1]/=count[c]

        for i in range(n):
            rx=rep[i,0]; ry=rep[i,1]; rn=np.sqrt(rx*rx+ry*ry)
            if rn>1e-12: rx/=rn; ry/=rn
            gx=group[label[i],0]; gy=group[label[i],1]
            gmag=np.sqrt(gx*gx+gy*gy)
            if interaction:
                ws,wg,wr=linker_weights(cmag[i],gmag,dmin[i],density[i],noise)
                if not np.isfinite(ws): ws=0.0
                if not np.isfinite(wg): wg=0.0
                if not np.isfinite(wr): wr=0.0
                ws=clip(ws,0.0,3.0); wg=clip(wg,0.0,3.0); wr=clip(wr,0.0,3.0)
                dx=SCALE*(ws*cvec[i,0]+wg*gx+wr*rx)
                dy=SCALE*(ws*cvec[i,1]+wg*gy+wr*ry)
            else:
                # Mandatory baseline is independent of candidate: repulsion-only safety.
                dx=SCALE*rx if dmin[i]<0.05 else 0.0
                dy=SCALE*ry if dmin[i]<0.05 else 0.0
            dn=np.sqrt(dx*dx+dy*dy)
            if dn>MAX_STEP:
                dx*=MAX_STEP/dn; dy*=MAX_STEP/dn
            p[i,0]+=dx+noise*dirs[t,i,0]; p[i,1]+=dy+noise*dirs[t,i,1]
            if p[i,0]<0: p[i,0]=0
            elif p[i,0]>1: p[i,0]=1
            if p[i,1]<0: p[i,1]=0
            elif p[i,1]>1: p[i,1]=1
        if observer is not None: observer(t+1, p.copy())
    return p

def random_units(rng):
    v=rng.normal(size=(STEPS,POP,2)); q=np.linalg.norm(v,axis=2); q[q<=1e-12]=1.0; return v/q[:,:,None]

def init_positions(kind,rng):
    n=POP
    if kind=='uniform_cloud': return np.column_stack([rng.uniform(.18,.82,n),rng.uniform(.18,.82,n)])
    if kind=='bimodal_horizontal':
        a=rng.normal(loc=(.32,.50),scale=(.055,.075),size=(n//2,2)); b=rng.normal(loc=(.68,.50),scale=(.055,.075),size=(n-n//2,2)); return np.clip(np.vstack([a,b]),.03,.97)
    if kind=='bimodal_diagonal':
        a=rng.normal(loc=(.36,.36),scale=(.060,.060),size=(n//2,2)); b=rng.normal(loc=(.64,.64),scale=(.060,.060),size=(n-n//2,2)); return np.clip(np.vstack([a,b]),.03,.97)
    if kind=='ring':
        ang=np.linspace(0,2*np.pi,n,endpoint=False)+rng.normal(0,.055,n); rad=.255+rng.normal(0,.025,n); return np.clip(np.column_stack([.5+rad*np.cos(ang),.5+rad*np.sin(ang)]),.03,.97)
    if kind=='boundary_biased': return np.column_stack([rng.uniform(.05,.48,n),rng.uniform(.18,.82,n)])
    raise ValueError(kind)

def metrics(p):
    c=np.mean(p,axis=0); rg=float(np.sqrt(np.mean(np.sum((p-c)**2,axis=1))))
    d=np.linalg.norm(p[None,:,:]-p[:,None,:],axis=2); np.fill_diagonal(d,np.inf)
    over=float(np.mean(np.min(d,axis=1)<OVERCROWD)); adj=d<=CONNECTIVITY
    n=len(p); seen=np.zeros(n,bool); best=0
    for s in range(n):
        if seen[s]: continue
        stack=[s]; seen[s]=True; cnt=0
        while stack:
            i=stack.pop(); cnt+=1
            for j in np.where(adj[i]&(~seen))[0]: seen[j]=True; stack.append(int(j))
        best=max(best,cnt)
    return best/n,rg,over

def run_case(kind,noise,seed,interaction=True):
    rng=np.random.default_rng(seed); p=init_positions(kind,rng).astype(np.float64); dirs=random_units(rng).astype(np.float64)
    p=core(p,dirs,bool(interaction),float(noise)); g,rg,o=metrics(p)
    passed=(g>=0.85 and rg<=0.18 and o<=0.10)
    return float(g),float(rg),float(o),bool(passed)

