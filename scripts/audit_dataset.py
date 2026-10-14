"""Sovra Phase 03: read-only schema & split audit. Stdlib only, no downloads."""
import argparse, csv, json, sys
from collections import Counter, defaultdict

REQUIRED_ANNOTATIONS = {'system_id','ligand_instance_chain','group_key','cluster'}
REQUIRED_PREDICTIONS = {'system_id','ligand_instance_chain','seed','sample','ranking_score','rmsd'}
# Any reference-derived metric or post-hoc closest-training label is prohibited as a decision feature.
FORBIDDEN = {'rmsd','lddt_pli','lddt_lp','bb_rmsd','pred_pocket_f1','target_system','target_release_date','num_training_systems_with_similar_ccds'}

def read(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        return set(reader.fieldnames or []), list(reader)

def audit(annotations, predictions, manifest=None, features=None):
    errors, warnings = [], []
    a_cols, ann = read(annotations)
    p_cols, pred = read(predictions)
    for label, cols, required in [('annotations',a_cols,REQUIRED_ANNOTATIONS),
                                  ('predictions',p_cols,REQUIRED_PREDICTIONS)]:
        if required - cols: errors.append(f"{label} missing: {sorted(required-cols)}")
    selected = set(features if features is not None else ['ranking_score'])
    if selected & FORBIDDEN: errors.append(f"Ground-truth leakage features: {sorted(selected & FORBIDDEN)}")
    if selected - p_cols: errors.append(f"Features absent from predictions: {sorted(selected-p_cols)}")
    if not ann or not pred: errors.append('Empty CSV')
    by_key = defaultdict(set)
    for r in ann:
        by_key[(r.get('system_id'),r.get('ligand_instance_chain'))].add(r.get('group_key'))
    if any(len(groups)>1 for groups in by_key.values()): errors.append('Conflicting group_key mapping')
    if any((r.get('system_id'),r.get('ligand_instance_chain')) not in by_key for r in pred):
        errors.append('Predictions without annotation mapping')
    pred_ids = [(r.get('system_id'),r.get('ligand_instance_chain'),r.get('seed'),r.get('sample')) for r in pred]
    if len(set(pred_ids)) != len(pred_ids):
        errors.append('Duplicate prediction identity; handle separate methods independently')
    counts = {}
    if manifest:
        with open(manifest, encoding='utf-8') as f: splits = json.load(f)
        if not isinstance(splits, dict): errors.append('Split manifest must be group_key -> train/val/test')
        else:
            clusters = defaultdict(set)
            for r in ann:
                group, cluster = r.get('group_key'),r.get('cluster')
                split = splits.get(group)
                if not cluster: errors.append(f'Missing cluster for {group}')
                if split not in ('train','val','test'): errors.append(f'Missing/invalid split for {group}')
                if cluster and split: clusters[cluster].add(split)
            if any(len(v)>1 for v in clusters.values()): errors.append('Cluster leakage across splits')
            counts = dict(Counter(splits.get(r.get('group_key'),'missing') for r in ann))
    else: warnings.append('No split manifest supplied; holdout is NOT verified')
    if 'rmsd' in p_cols: warnings.append('RMSD present as label only; never use for inference')
    return dict(status='PASS' if not errors else 'FAIL', annotation_rows=len(ann),
                prediction_rows=len(pred), unique_system_ligands=len(by_key),
                selected_features=sorted(selected), split_counts=counts,
                errors=errors,warnings=warnings)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--annotations',required=True);p.add_argument('--predictions',required=True)
    p.add_argument('--split-manifest');p.add_argument('--feature',action='append')
    p.add_argument('--out')
    a=p.parse_args()
    try: report=audit(a.annotations,a.predictions,a.split_manifest,a.feature)
    except (OSError,ValueError,csv.Error) as err: report={'status':'FAIL','errors':[str(err)]}
    result=json.dumps(report,indent=2);print(result)
    if a.out:
        with open(a.out,'w',encoding='utf-8') as f:f.write(result+'\n')
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':sys.exit(main())
