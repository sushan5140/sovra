"""Read-only Runs N' Poses dataset audit; validates real model CSV and TAR schemas."""
import argparse,csv,io,json,tarfile
from collections import Counter,defaultdict
from pathlib import Path

ANN_REQ={'system_id','ligand_instance_chain','group_key','cluster'}
PRED_REQ={'target','ligand_instance_chain','method'}
SAFE_FEATURES={'ranking_score'}

def audit(annotations_path,predictions_path,split_manifest=None,features=None):
    errors=[];warnings=[];features=list(features) if features is not None else ['ranking_score']
    unapproved=set(features)-SAFE_FEATURES
    if unapproved:errors.append(f'Unapproved/reference-derived features: {sorted(unapproved)}')
    annotated=defaultdict(set);group_clusters=defaultdict(set);ann_rows=0
    with open(annotations_path,newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f);missing=ANN_REQ-set(reader.fieldnames or ())
        if missing:errors.append(f'Annotations missing columns: {sorted(missing)}')
        else:
            for row in reader:
                ann_rows+=1
                annotated[(row['system_id'],row['ligand_instance_chain'])].add(row['group_key'])
                group_clusters[row['group_key']].add(row['cluster'])
    conflicts=sum(len(v)>1 for v in annotated.values())
    if conflicts:errors.append(f'{conflicts} annotations map an identity to multiple groups')
    split_counts={}
    if split_manifest:
        with open(split_manifest,encoding='utf-8') as f:splits=json.load(f)
        if not isinstance(splits,dict):errors.append('Split manifest must map group_key to train/val/test')
        else:
            cluster_splits=defaultdict(set)
            for group,clusters in group_clusters.items():
                split=splits.get(group)
                if split not in {'train','val','test'}:errors.append(f'Missing/invalid split for {group}')
                for c in clusters:
                    if not c:errors.append(f'Empty cluster in group {group}')
                    elif split in {'train','val','test'}:cluster_splits[c].add(split)
            if any(len(v)>1 for v in cluster_splits.values()):errors.append('Cluster leakage across splits')
            split_counts=dict(Counter(splits.get(g,'missing') for g in group_clusters))
    else:warnings.append('No split manifest supplied; split leakage safety NOT established')
    summaries=[]
    path=Path(predictions_path)
    def sources():
        if tarfile.is_tarfile(path):
            with tarfile.open(path,'r:*') as t:
                for m in t:
                    if m.isfile() and m.name.lower().endswith('.csv'):
                        stream=t.extractfile(m)
                        if stream:
                            with io.TextIOWrapper(stream,encoding='utf-8-sig',newline='') as f:
                                yield m.name,f
        else:
            with open(path,encoding='utf-8-sig',newline='') as f:yield path.name,f
    for name,f in sources():
        reader=csv.DictReader(f);cols=set(reader.fieldnames or ())
        missing=PRED_REQ-cols
        if missing:
            errors.append(f'{name}: missing {sorted(missing)}');continue
        for feature in features:
            if feature not in cols:warnings.append(f'{name}: selected feature {feature} missing')
        seen=set();unmatched=set();unmatched_rows=0;matched=0;duplicate=0;rows=0;samplekeys=Counter()
        for r in reader:
            rows+=1
            key=(r.get('target',''),r.get('ligand_instance_chain',''))
            if key in annotated:matched+=1
            else:unmatched_rows+=1;unmatched.add(key)
            ident=(r.get('method',''),*key,r.get('seed',''),r.get('sample',''),r.get('model_ligand_ccd_code',''),r.get('model_ligand_chain_rmsd',''))
            if ident in seen:duplicate+=1
            else:seen.add(ident)
            samplekeys[(r.get('method',''),r.get('target',''),r.get('seed',''),r.get('sample',''))]+=1
        if not rows:errors.append(f'{name}: empty prediction file')
        summaries.append(dict(file=name,rows=rows,matched_rows=matched,unmatched_rows=unmatched_rows,
            unmatched_unique_keys=len(unmatched),repeated_extended_identifiers=duplicate,
            multi_ligand_or_repeated_sample_keys=sum(n>1 for n in samplekeys.values()),
            has_seed='seed' in cols,has_sample='sample' in cols,
            has_ranking_score='ranking_score' in cols,has_rmsd='rmsd' in cols))
        if unmatched_rows:warnings.append(f'{name}: {unmatched_rows} unmatched annotation rows')
        if duplicate:warnings.append(f'{name}: {duplicate} repeated extended identifiers; no automatic deduplication')
    if not summaries:errors.append('No prediction CSVs found')
    return dict(status='FAIL' if errors else 'PASS_WITH_WARNINGS' if warnings else 'PASS',
        annotation_rows=ann_rows,annotation_unique_ligands=len(annotated),prediction_files=summaries,
        split_group_counts=split_counts,selected_features=features,errors=errors,warnings=warnings)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--annotations',required=True);p.add_argument('--predictions',required=True)
    p.add_argument('--split-manifest');p.add_argument('--feature',action='append');p.add_argument('--out')
    a=p.parse_args()
    try:result=audit(a.annotations,a.predictions,a.split_manifest,a.feature)
    except (OSError,ValueError,csv.Error,tarfile.TarError) as e:result={'status':'FAIL','errors':[str(e)]}
    output=json.dumps(result,indent=2);print(output)
    if a.out:Path(a.out).write_text(output+'\n',encoding='utf-8')
    return int(result['status']=='FAIL')
if __name__=='__main__':raise SystemExit(main())
