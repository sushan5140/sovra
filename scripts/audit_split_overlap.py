"""Read-only cross-partition identity overlap report. Stdlib only."""
import argparse,csv,json,hashlib
from collections import defaultdict,Counter
from pathlib import Path

def audit(annotations,manifest):
    with open(manifest,encoding='utf-8') as f:splits=json.load(f)
    if not isinstance(splits,dict):raise ValueError('Manifest must map group_key to split')
    by_identity={k:defaultdict(set) for k in ('cluster','ligand_smiles','ligand_ccd_code','entry_pdb_id')}
    group_clusters=defaultdict(set);rows=0;parts=Counter();ident_rows={k:defaultdict(int) for k in by_identity}
    with open(annotations,newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        missing=set(by_identity)|{'group_key'}-set(reader.fieldnames or [])
        if missing:raise ValueError('Missing annotation columns: '+str(sorted(missing)))
        for row in reader:
            rows+=1;g=row['group_key'];sp=splits.get(g)
            if sp not in ('train','val','test'):raise ValueError('Missing or invalid split for group '+g)
            parts[sp]+=1;group_clusters[g].add(row['cluster'])
            for k in by_identity:
                val=row[k].strip()
                if val:
                    by_identity[k][val].add(sp);ident_rows[k][val]+=1
    if any(len(v)>1 for v in group_clusters.values()):raise ValueError('Conflicting group-to-cluster mapping')
    overlaps={}
    for k,groups in by_identity.items():
        cross=[v for v,ps in groups.items() if len(ps)>1]
        overlaps[k]={'cross_split_unique_values':len(cross),'affected_rows':sum(ident_rows[k][v] for v in cross)}
    return {'status':'BLOCK_FREEZE','annotation_rows':rows,'split_row_counts':dict(parts),
            'group_count':len(group_clusters),'overlap':overlaps,
            'caveat':'Overlap is a risk indicator, not proof of inappropriate leakage; protein/pocket sequence/structure similarity and licensing still require review.',
            'manifest_sha256':hashlib.sha256(Path(manifest).read_bytes()).hexdigest()}
def main():
    p=argparse.ArgumentParser();p.add_argument('--annotations',required=True);p.add_argument('--manifest',required=True);p.add_argument('--out');a=p.parse_args()
    result=audit(a.annotations,a.manifest);out=json.dumps(result,indent=2);print(out)
    if a.out:Path(a.out).write_text(out+'\n',encoding='utf-8')
if __name__=='__main__':main()
