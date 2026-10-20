#!/usr/bin/env python3
"""Compare zHD/zCMB/zHEL for the curated 43 WP2 calibrators without overwriting existing outputs."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from scipy.integrate import quad

ROOT = Path.cwd()
PANTHEON = ROOT / 'Pantheon+SH0ES.dat'
HOSTS = ROOT / 'data/external/wp2_sh0es_cid_resolved_corrected.csv'
OUT_CSV = ROOT / 'data/external/wp2_sh0es_redshift_variant_comparison.csv'
OUT_MD = ROOT / 'docs/wp2_redshift_variant_comparison.md'
OM, H, C = 0.26, 1.0, 299792.458
VARIANTS = ('zHD', 'zCMB', 'zHEL')

def col(df, names):
    m = {str(c).strip().lower(): c for c in df.columns}
    for n in names:
        if n.lower() in m: return m[n.lower()]
    raise ValueError(f'Column missing ({names}); available: {list(df.columns)}')

def distance(z):
    if not np.isfinite(z) or z < 0: raise ValueError(f'Invalid redshift {z}')
    if z == 0: return 0.0
    a0 = 1.0 / (1.0 + float(np.float32(z)))
    ol = 1.0 - OM
    f = lambda a: 1.0 / np.sqrt(OM*a + ol*a**4)
    integ, _ = quad(f, a0, 1.0, epsabs=1.49e-8, epsrel=1.49e-8, limit=50)
    return C / 100.0 * integ  # Mpc/h, VAST scale convention

def xyz(ra_deg, dec_deg, r):
    ra, dec = np.deg2rad(ra_deg), np.deg2rad(dec_deg)
    return (r*np.cos(ra)*np.cos(dec), r*np.sin(ra)*np.cos(dec), r*np.sin(dec))

def main():
    if not PANTHEON.exists() or not HOSTS.exists():
        raise FileNotFoundError(f'Run from repo root; need {PANTHEON} and {HOSTS}')
    p = pd.read_csv(PANTHEON, sep=r'\s+', comment='#', engine='python')
    h = pd.read_csv(HOSTS)
    pcid, hcid = col(p, ['CID','SN','name']), col(h, ['CID','cid'])
    ra, dec = col(p, ['RA','ra']), col(p, ['DEC','Dec','dec'])
    missing_cols = [v for v in VARIANTS if v not in p.columns]
    if missing_cols: raise ValueError(f'Missing redshift columns {missing_cols}; columns={list(p.columns)}')
    target = h[hcid].astype(str).str.strip().drop_duplicates()
    if len(target) != 43: raise ValueError(f'Expected 43 curated CIDs, found {len(target)}')
    p[pcid] = p[pcid].astype(str).str.strip()

    if "IS_CALIBRATOR" not in p.columns:
        raise ValueError("Pantheon file has no IS_CALIBRATOR column")

    p["IS_CALIBRATOR"] = pd.to_numeric(
        p["IS_CALIBRATOR"], errors="coerce"
    )

    p[pcid] = p[pcid].astype(str).str.strip()

    p = p[
        p[pcid].isin(set(target))
        & (p["IS_CALIBRATOR"] == 1)
        ].copy()

    geometry_fields = [ra, dec, *VARIANTS]

    for cid, group in p.groupby(pcid):
        for field in geometry_fields:
            if group[field].nunique(dropna=False) > 1:
                raise ValueError(
                    f"Conflicting {field} values for duplicate CID {cid}"
                )

    p = p.drop_duplicates(subset=pcid, keep="first")

    if len(p) != 43 or p[pcid].nunique() != 43:
        raise ValueError(
            f"Expected 43 unique calibrators; got {len(p)} rows "
            f"and {p[pcid].nunique()} unique CIDs"
        )

    if p[pcid].duplicated().any() or p[pcid].nunique() != 43:
        raise ValueError(
            f"Expected one calibrator row per curated CID; "
            f"found {len(p)} rows and {p[pcid].nunique()} unique CIDs"
        )
    for c in [ra, dec, *VARIANTS]: p[c] = pd.to_numeric(p[c], errors='coerce')
    if p[[ra,dec,*VARIANTS]].isna().any().any(): raise ValueError('Missing/non-numeric RA/DEC/redshift in matched sample')
    rows=[]
    for _, row in p.sort_values(pcid).iterrows():
        d={'CID':row[pcid], 'RA_deg':row[ra], 'DEC_deg':row[dec]}
        vals={}
        for v in VARIANTS:
            r=distance(float(row[v])); x,y,z=xyz(float(row[ra]),float(row[dec]),r)
            vals[v]={'redshift':float(row[v]),'r':r,'x':x,'y':y,'z':z}
            for k,val in vals[v].items(): d[f'{v}_{k}']=val
        for v in ('zCMB','zHEL'):
            for k in ('r','x','y','z'):
                d[f'delta_{k}_{v}_minus_zHD']=vals[v][k]-vals['zHD'][k]
        rows.append(d)
    out=pd.DataFrame(rows)
    summaries=[]
    for v in ('zCMB','zHEL'):
        dr=out[f'delta_r_{v}_minus_zHD'].abs()
        dxyz=np.sqrt(sum(out[f'delta_{k}_{v}_minus_zHD']**2 for k in ('x','y','z')))
        summaries.append((v,dr.max(),dr.median(),dxyz.max(),dxyz.median(),int((out[f'{v}_redshift']!=out['zHD_redshift']).sum())))
    OUT_CSV.parent.mkdir(parents=True,exist_ok=True); OUT_MD.parent.mkdir(parents=True,exist_ok=True)
    out.to_csv(OUT_CSV,index=False,float_format='%.10g')
    lines=['# WP2: Sensitivitätsvergleich der Pantheon+-Redshift-Spalten','',
      'Vergleich von `zHD`, `zCMB` und `zHEL` für dieselben 43 kuratierten CIDs. Bestehende XYZ-Dateien werden nicht überschrieben.', '',
      f'Konvention: flache Lambda-CDM-Distanz, Omega_M={OM}, h={H}, VAST-Skalierung Mpc/h; identische RA/DEC für alle Varianten.', '',
      'Referenz für die Differenzen ist `zHD`. Dieser Vergleich ist eine Sensitivitätsanalyse, keine automatische Entscheidung über die wissenschaftlich passende Spalte.', '',
      '| Variante vs. zHD | max. |Δr| (Mpc/h) | median |Δr| (Mpc/h) | max. XYZ-Verschiebung (Mpc/h) | mediane XYZ-Verschiebung (Mpc/h) | CIDs mit abweichendem z |',
      '|---|---:|---:|---:|---:|---:|']
    for v,a,b,c,d,n in summaries: lines.append(f'| `{v}` | {a:.6g} | {b:.6g} | {c:.6g} | {d:.6g} | {n}/43 |')
    lines += ['', '## Interpretation und Grenzen','',
      '- Bei festen RA/DEC liegen alle Varianten auf derselben Sichtlinie; die XYZ-Verschiebung entspricht dem Betrag der radialen Verschiebung.',
      '- Der Vergleich isoliert den Einfluss der Redshift-Spalte bei festgehaltener Distanzkonvention.',
      '- Messfehler, Pekuliargeschwindigkeiten, Host-Positionsunsicherheit und Survey-Maske sind nicht eingerechnet.',
      '- Die Distanzfunktion nutzt die VAST-nahe Skalenkonvention; vor einer finalen wissenschaftlichen Verwendung sollte die numerische Ausgabe stichprobenweise direkt gegen die installierte VAST-Funktion geprüft werden.', '',
      '## Ausgaben','',f'- Detail-CSV: `{OUT_CSV.relative_to(ROOT)}`',f'- Bericht: `{OUT_MD.relative_to(ROOT)}`','',
      'Die Detail-CSV enthält für jede CID alle drei Redshifts, Radien und XYZ-Koordinaten sowie Differenzen von `zCMB` und `zHEL` gegenüber `zHD`.']
    OUT_MD.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Compared {len(out)} CIDs')
    print(pd.DataFrame(summaries,columns=['variant','max_abs_dr','median_abs_dr','max_xyz_shift','median_xyz_shift','n_redshift_changed']).to_string(index=False))
    print(f'CSV: {OUT_CSV}\nReport: {OUT_MD}')
if __name__=='__main__':
    try: main()
    except Exception as e:
        print(f'ERROR: {e}',file=sys.stderr); sys.exit(2)
