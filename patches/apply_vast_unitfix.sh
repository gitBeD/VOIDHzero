#!/usr/bin/env bash
# Distanz-Einheitenkorrektur fuer VAST (Mpc/h statt zusaetzlicher 1/h-Skalierung).
# Aufruf: bash patches/apply_vast_unitfix.sh /pfad/zu/VAST
set -euo pipefail
V="${1:?Pfad zur VAST-Kopie angeben}"
D="$V/python/vast/voidfinder/distance.pyx"
F="$V/python/vast/voidfinder/voidfinder.py"
sed -i '/cdef DTYPE_F32_t H0 = 100.0\*h/d' "$D"
sed -i 's|out_dists_array\[idx\] = \(.*\)\*(c/H0)|out_dists_array[idx] = \1*(c/100.0)|' "$D"
sed -i "s|r_gal = c\*galaxy_table\['redshift'\].data/(100\*h)|r_gal = c*galaxy_table['redshift'].data/100.0|" "$F"
grep -n "/100.0" "$D" "$F"
