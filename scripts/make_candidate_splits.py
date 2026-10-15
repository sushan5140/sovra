"""Deterministic candidate split; NOT proof of leakage-free evaluation."""
import argparse,csv,hashlib,json
from collections import defaultdict,Counter
from pathlib import Path

def assign(path,seed='sovra-v1'):
    clusters=defaultdict(set);groups={}
    with open(path,newline='',encoding='utf-8-sig') as f:
        r=csv.DictReader(f)
        if {'group_key','cluster'}-set(r.fieldnames or ()):raise ValueError('Missing group_key or cluster')
        for row in r:
            g,c=row['group_key'],row['cluster']
            if not g or not c:raise ValueError('Empty group/cluster')
            if g in groups and groups[g]!=c:raise ValueError('Conflicting cluster for group')
            groups[g]=c;clusters[c].add(g)
    if not clusters:raise ValueError('No clusters')
    ordered=sorted(clusters,key=lambda c:(hashlib.sha256((seed+'|'+c).encode()).hexdigest(),c))
    n=len(ordered);t=int(n*.7);v=int(n*.15);out={};counts=Counter()
    for i,c in enumerate(ordered):
        split='train' if i<t else 'val' if i<t+v else 'test'
        counts[split]+=1
        for group in clusters[c]:out[group]=split
    return dict(sorted(out.items())),{'seed':seed,'cluster_counts':dict(counts),'groups':len(out),'caveat':'PROVISIONAL: cross-cluster similarity and license not validated'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--annotations',required=True);p.add_argument('--output',required=True);p.add_argument('--seed',default='sovra-v1');a=p.parse_args()
    splits,meta=assign(a.annotations,a.seed)
    Path(a.output).write_text(json.dumps(splits,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
