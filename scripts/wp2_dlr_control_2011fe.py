import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u


# ------------------------------------------------------------
# Kontrollfall SN 2011fe / NSAID 259087
# ------------------------------------------------------------

# SN position from Pantheon+
sn = SkyCoord(
    ra=210.77400000 * u.deg,
    dec=54.27370000 * u.deg,
    frame="icrs",
)

# NSA galaxy center
galaxy = SkyCoord(
    ra=210.8068073277288 * u.deg,
    dec=54.261829083411826 * u.deg,
    frame="icrs",
)

# NSA Sérsic parameters
a = 115.638275 * u.arcsec
ba = 0.4712229
pa = 94.09836 * u.deg

# Minor-axis half-light radius
b = a * ba


# ------------------------------------------------------------
# Sky geometry
# ------------------------------------------------------------

separation = galaxy.separation(sn)

# Position angle from galaxy -> SN:
# measured from North through East
position_angle = galaxy.position_angle(sn)

# Difference relative to Sérsic major axis.
# Ellipse geometry is invariant under 180° rotation.
phi = (position_angle - pa).wrap_at(180 * u.deg)


# ------------------------------------------------------------
# Directional Light Radius
# ------------------------------------------------------------

phi_rad = phi.to_value(u.rad)
a_arcsec = a.to_value(u.arcsec)
b_arcsec = b.to_value(u.arcsec)

dlr_arcsec = (
    a_arcsec * b_arcsec
    / np.sqrt(
        (a_arcsec * np.sin(phi_rad)) ** 2
        + (b_arcsec * np.cos(phi_rad)) ** 2
    )
)

d_dlr = separation.to_value(u.arcsec) / dlr_arcsec


# ------------------------------------------------------------
# Output
# ------------------------------------------------------------

print("=== 2011fe DLR control ===")
print(f"SN RA/DEC:             {sn.ra.deg:.8f}, {sn.dec.deg:.8f}")
print(f"Galaxy RA/DEC:         {galaxy.ra.deg:.8f}, {galaxy.dec.deg:.8f}")
print()
print(f"Separation:            {separation.to_value(u.arcsec):.6f} arcsec")
print(f"SN position angle:     {position_angle.to_value(u.deg):.6f} deg")
print(f"Sersic major-axis PA:  {pa.to_value(u.deg):.6f} deg")
print(f"Relative angle phi:    {phi.to_value(u.deg):.6f} deg")
print()
print(f"a = TH50:              {a_arcsec:.6f} arcsec")
print(f"b = a * BA:            {b_arcsec:.6f} arcsec")
print(f"Directional DLR:       {dlr_arcsec:.6f} arcsec")
print(f"d_DLR:                 {d_dlr:.6f}")