from __future__ import annotations

import json
from pathlib import Path
import numpy as np

from .navigation_r1 import policy as frozen_navigation_policy
from .compiler_m77 import (
    BUDGET, MAX_NAV_GAIN, causal_homeostasis_request,
    _allocate_strict, _allocate_deadline_relaxed,
)
from .compiler_m79 import allocate_contract_margin_step_v2
from .compiler_m710 import allocate_viability_debt_step_v3
from .runtime_m7 import (
    N_CELLS, STEPS, TARGET_RADIUS, FORBIDDEN_THRESHOLD, SENSE_B_THRESHOLD,
    HOMEOSTASIS_NOISE_SIGMA, NATURAL_RELAXATION, UNSAFE_LOW, UNSAFE_HIGH,
    RECOVERY_DEADLINE,
)

MEASURE_START=10


def load_cases(root):
    root=Path(root)
    return (
        json.loads((root/'blind_worlds.json').read_text())['worlds'],
        json.loads((root/'blind_disturbances.json').read_text())['disturbances'],
    )


def gaussian_value(x,y,cx,cy,sigma):
    return np.exp(-((x-cx)**2+(y-cy)**2)/(2.0*sigma*sigma))


def unit_to_center(x,y,cx,cy):
    dx=cx-x; dy=cy-y; norm=np.sqrt(dx*dx+dy*dy)
    return np.stack([
        np.divide(dx,norm,out=np.zeros_like(dx),where=norm>1e-12),
        np.divide(dy,norm,out=np.zeros_like(dy),where=norm>1e-12),
    ],axis=-1)


def normalized_random_vectors(rng):
    v=rng.normal(size=(STEPS,N_CELLS,2)); norm=np.linalg.norm(v,axis=2)
    return np.divide(v,norm[...,None],out=np.zeros_like(v),where=norm[...,None]>1e-12)


def disturbance_trace(spec,seed):
    rng=np.random.default_rng(seed+20_000_000);d=np.zeros(STEPS,float)
    fam=spec['family'];start=int(spec['start']);end=int(spec['end']);n=max(end-start,1)
    if fam=='quadratic_ramp_reversal':
        sw=int(spec['switch']);pa=float(spec['positive_amplitude']);na=float(spec['negative_amplitude'])
        n1=max(sw-start,1);u=np.linspace(0,1,n1,endpoint=False);d[start:sw]=pa*u*u
        n2=max(end-sw,1);v=np.linspace(0,1,n2,endpoint=False);d[sw:end]=-na*(1-v)**2
    elif fam=='pulse_packet_jitter':
        count=int(spec['pulse_count']);wmin=int(spec['width_min']);wmax=int(spec['width_max']);amin=float(spec['amplitude_min']);amax=float(spec['amplitude_max'])
        centers=np.sort(rng.choice(np.arange(start+8,end-8),size=count,replace=False))
        for c in centers:
            width=int(rng.integers(wmin,wmax+1));amp=float(rng.uniform(amin,amax));sgn=-1.0 if int(rng.integers(0,2))==0 else 1.0
            lo=max(start,c-width//2);hi=min(end,c+width//2+1);u=np.linspace(-1,1,hi-lo);d[lo:hi]+=sgn*amp*(1-u*u)
    elif fam=='biexponential_recovery':
        amp=float(spec['amplitude'])*float(spec['sign']);tf=float(spec['tau_fast']);ts=float(spec['tau_slow']);k=np.arange(n,dtype=float)
        wave=np.exp(-k/ts)-np.exp(-k/tf);m=np.max(np.abs(wave));wave=wave/m if m>1e-12 else wave;d[start:end]=amp*wave
    elif fam=='ar1_colored_pressure':
        phi=float(spec['phi']);sigma=float(spec['sigma']);cap=float(spec['clip']);x=0.0
        for t in range(start,end):
            x=phi*x+float(rng.normal(0,sigma));x=float(np.clip(x,-cap,cap));d[t]=x
    elif fam=='multifrequency_beat':
        amp=float(spec['amplitude']);c1=float(spec['cycles1']);c2=float(spec['cycles2']);u=np.linspace(0,1,n,endpoint=False);window=np.sin(np.pi*u)**2
        d[start:end]=amp*window*.5*(np.sin(2*np.pi*c1*u)+np.sin(2*np.pi*c2*u))
    elif fam=='delayed_plateau_notch':
        ns=int(spec['notch_start']);ne=int(spec['notch_end']);p=float(spec['plateau']);q=float(spec['notch']);d[start:end]=p;d[ns:ne]=-q
    else: raise ValueError(f'Unknown M7.18 disturbance family: {fam}')
    return d


def prepare_streams(disturbance,seeds):
    S=len(seeds); positions=np.empty((S,N_CELLS,2)); H=np.empty((S,N_CELLS)); nav=np.empty((S,STEPS,N_CELLS,2)); hn=np.empty((S,STEPS,N_CELLS)); dt=np.empty((S,STEPS))
    for i,seed in enumerate(seeds):
        nr=np.random.default_rng(seed); positions[i,:,0]=nr.uniform(5,18,N_CELLS); positions[i,:,1]=nr.uniform(43,57,N_CELLS); nav[i]=normalized_random_vectors(nr)
        hr=np.random.default_rng(seed+10_000_000); H[i]=hr.uniform(.44,.56,N_CELLS); hn[i]=hr.normal(0,HOMEOSTASIS_NOISE_SIGMA,size=(STEPS,N_CELLS)); dt[i]=disturbance_trace(disturbance,seed)
    return positions,H,nav,hn,dt


def run_pair(mode,world,disturbance,seeds, observer=None):
    positions,H,nav_random,h_noise,dtrace=prepare_streams(disturbance,seeds); S=len(seeds)
    tx,ty,a_sigma=map(float,world['A']); bx,by,b_sigma=map(float,world['B']); world_noise=float(world['noise'])
    forbidden_ever=np.zeros((S,N_CELLS),bool); inband=np.zeros((S,STEPS,N_CELLS),bool); unsafe=np.zeros_like(inband)
    budget=np.zeros(S,int); relaxed=np.zeros(S,int); contention=np.zeros(S,int); debt=np.zeros((S,N_CELLS),bool)
    if observer is not None: observer(0, positions.copy(), H.copy())
    for t in range(STEPS):
        x=positions[:,:,0]; y=positions[:,:,1]
        A=gaussian_value(x,y,tx,ty,a_sigma); B=gaussian_value(x,y,bx,by,b_sigma); forbidden_ever |= B>=FORBIDDEN_THRESHOLD
        toward,away=frozen_navigation_policy(A,B); toward=np.clip(np.asarray(toward,float),0,3); away=np.clip(np.asarray(away,float),0,3); away=np.where(B>=SENSE_B_THRESHOLD,away,0)
        current_distance=np.sqrt((x-tx)**2+(y-ty)**2); goal_satisfied=current_distance<=TARGET_RADIUS
        d_goal=np.clip(toward/MAX_NAV_GAIN,0,1); d_safety=np.clip(away/MAX_NAV_GAIN,0,1); _hc,d_inv,inv_res=causal_homeostasis_request(H)
        g0,s0,_=_allocate_strict(d_goal,d_safety,d_inv,inv_res); g1,s1,_=_allocate_deadline_relaxed(d_goal,d_safety,d_inv,inv_res)
        gd=unit_to_center(x,y,tx,ty); hd=unit_to_center(x,y,bx,by)
        def b_upper(g,s):
            gs=np.divide(g,d_goal,out=np.zeros_like(g),where=d_goal>1e-15); ss=np.divide(s,d_safety,out=np.zeros_like(s),where=d_safety>1e-15)
            det=positions+(toward*gs)[...,None]*gd-(away*ss)[...,None]*hd
            rdet=np.sqrt((det[:,:,0]-bx)**2+(det[:,:,1]-by)**2); rmin=np.maximum(rdet-world_noise,0.0)
            return np.exp(-(rmin*rmin)/(2.0*b_sigma*b_sigma))
        relaxed_upper=b_upper(g1,s1); strict_upper=b_upper(g0,s0)
        if mode=='contract_margin_linker_v2':
            toward_exec,away_exec,homeo_exec,audit,_=allocate_contract_margin_step_v2(
                t=t,A=A,B=B,H=H,toward_gain=toward,away_gain=away,goal_satisfied=goal_satisfied,forbidden_ever=forbidden_ever,
                relaxed_B_upper_bound=relaxed_upper,strict_B_upper_bound=strict_upper)
        elif mode=='viability_debt_linker_v3':
            toward_exec,away_exec,homeo_exec,audit,debt,_=allocate_viability_debt_step_v3(
                t=t,A=A,B=B,H=H,toward_gain=toward,away_gain=away,goal_satisfied=goal_satisfied,forbidden_ever=forbidden_ever,
                intentional_risk_debt=debt,relaxed_B_upper_bound=relaxed_upper,strict_B_upper_bound=strict_upper)
        else: raise ValueError(mode)
        budget += np.sum(audit.budget_violation,axis=1).astype(int); relaxed += np.sum(audit.relaxed_mask,axis=1).astype(int); contention += np.sum(audit.contention,axis=1).astype(int)
        positions += world_noise*nav_random[:,t]+toward_exec[...,None]*gd-away_exec[...,None]*hd
        positions[:,:,0]=np.clip(positions[:,:,0],0,100); positions[:,:,1]=np.clip(positions[:,:,1],0,100)
        H=np.clip(H+NATURAL_RELAXATION*(.5-H)+homeo_exec+dtrace[:,t,None]+h_noise[:,t],0,1)
        if observer is not None: observer(t+1, positions.copy(), H.copy())
        inband[:,t]=(H>=.40)&(H<=.60); unsafe[:,t]=(H<=UNSAFE_LOW)|(H>=UNSAFE_HIGH)
    final_dist=np.linalg.norm(positions-np.array([tx,ty])[None,None,:],axis=2); end=int(disturbance['end']); deadline=min(end+RECOVERY_DEADLINE,STEPS-1)
    rows=[]
    for i,seed in enumerate(seeds):
        target=float(np.mean(final_dist[i]<=TARGET_RADIUS)); forb=float(np.mean(forbidden_ever[i])); band=float(np.mean(inband[i,MEASURE_START:])); uns=float(np.mean(unsafe[i])); occ=np.mean(inband[i,end:deadline+1],axis=1); rec=float(np.max(occ)>=.90)
        joint=float(target>=.80 and forb<=.10 and band>=.80 and uns<=.05 and rec>=.80 and budget[i]==0)
        rows.append({'mode':mode,'world':world['id'],'world_stratum':world['stratum'],'disturbance':disturbance['id'],'disturbance_family':disturbance['family'],'seed':int(seed),'target_occupancy':target,'forbidden_entry_fraction':forb,'band_occupancy':band,'unsafe_state_fraction':uns,'recovery_fraction':rec,'joint_pass':joint,'mean_final_distance':float(np.mean(final_dist[i])),'budget_violations':int(budget[i]),'relaxed_cell_steps':int(relaxed[i]),'contention_cell_steps':int(contention[i]),'final_risk_debt_cells':int(np.sum(debt[i])) if mode=='viability_debt_linker_v3' else 0})
    return rows


def summarize(raw):
    pairs=[]
    keys=sorted(set((r['world'],r['disturbance']) for r in raw))
    for key in keys:
        rr=[r for r in raw if (r['world'],r['disturbance'])==key]
        pairs.append({'world':key[0],'world_stratum':rr[0]['world_stratum'],'disturbance':key[1],'disturbance_family':rr[0]['disturbance_family'],'target_occupancy':float(np.mean([x['target_occupancy'] for x in rr])),'forbidden_entry_fraction':float(np.mean([x['forbidden_entry_fraction'] for x in rr])),'band_occupancy':float(np.mean([x['band_occupancy'] for x in rr])),'unsafe_state_fraction':float(np.mean([x['unsafe_state_fraction'] for x in rr])),'recovery_rate':float(np.mean([x['recovery_fraction'] for x in rr])),'joint_task_pass_rate':float(np.mean([x['joint_pass'] for x in rr])),'budget_violations':int(sum(x['budget_violations'] for x in rr))})
    agg={'target_occupancy':float(np.mean([r['target_occupancy'] for r in raw])),'forbidden_entry_fraction':float(np.mean([r['forbidden_entry_fraction'] for r in raw])),'band_occupancy':float(np.mean([r['band_occupancy'] for r in raw])),'unsafe_state_fraction':float(np.mean([r['unsafe_state_fraction'] for r in raw])),'recovery_rate':float(np.mean([r['recovery_fraction'] for r in raw])),'joint_task_pass_rate':float(np.mean([r['joint_pass'] for r in raw])),'worst_pair_joint_pass_rate':float(min(p['joint_task_pass_rate'] for p in pairs)),'budget_violations':int(sum(r['budget_violations'] for r in raw)),'run_count':len(raw),'pass_count':int(sum(r['joint_pass'] for r in raw))}
    agg['feasible']=bool(agg['target_occupancy']>=.80 and agg['forbidden_entry_fraction']<=.10 and agg['band_occupancy']>=.85 and agg['unsafe_state_fraction']<=.05 and agg['recovery_rate']>=.90 and agg['joint_task_pass_rate']>=.90 and agg['worst_pair_joint_pass_rate']>=.80 and agg['budget_violations']==0)
    return agg,pairs
