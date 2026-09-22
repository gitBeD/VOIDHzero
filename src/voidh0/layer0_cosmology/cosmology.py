"""Schicht 0 -- Kosmologie.

Zentrale Designregel des Projekts (Exposé Abschnitt 6):
"Kein Analyseschritt oberhalb von Schicht 2 darf ... alles Survey-Spezifische
lebt in Schicht 1 und 2." Schicht 0 selbst kennt gar keine Surveys -- sie
stellt ausschliesslich eine einzige, explizit gesetzte Referenzkosmologie und
die daraus abgeleiteten Distanzmasse bereit, mit denen alle hoeheren Schichten
rechnen.

Bewusst ohne astropy-Abhaengigkeit implementiert: eine flache LambdaCDM-
Kosmologie ist mit einer einfachen numerischen Integration des Hubble-Parameters
vollstaendig und reproduzierbar beschrieben. Das haelt die Referenzkosmologie
diff-bar im Repository (configs/cosmology.yaml) statt implizit von einer
astropy-Version abzuhaengen. Wer moechte, kann optional gegen astropy
cross-checken (siehe tests/test_cosmology.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math

import numpy as np
from scipy import integrate
import yaml

# Lichtgeschwindigkeit in km/s
C_KM_S = 299_792.458

_DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[3] / "configs" / "cosmology.yaml"
)


@dataclass(frozen=True)
class ReferenceCosmology:
    """Die eine, eingefrorene Referenzkosmologie (Schicht 0).

    Alle Laengen, die aus dieser Klasse berechnet werden, sind in h^-1 Mpc
    (siehe Exposé Abschnitt 6: "alle Laengen in h⁻¹ Mpc"), sofern nicht anders
    angegeben. H0 selbst wird in km/s/Mpc gefuehrt, weil es die Normierung
    *dieser Referenzkosmologie* ist -- nicht das H0, das im Projekt gemessen
    werden soll (siehe docs/architecture.md, Abschnitt "Zirkularitaet").

    Instanzen sind unveraenderlich (frozen dataclass): eine Aenderung der
    Referenzkosmologie ist ein Analyseplan-Ereignis, kein Laufzeitzustand.
    """

    name: str
    H0_km_s_Mpc: float
    Om0: float
    Ob0: float = 0.0
    Tcmb0_K: float = 2.7255
    Neff: float = 3.046

    def __post_init__(self) -> None:
        if not (0.0 < self.Om0 < 1.5):
            raise ValueError(f"Om0={self.Om0} ausserhalb eines plausiblen Bereichs")
        if self.H0_km_s_Mpc <= 0:
            raise ValueError("H0_km_s_Mpc muss positiv sein")

    # -- abgeleitete Groessen -------------------------------------------------

    @property
    def hubble_distance_Mpc(self) -> float:
        """c / H0 in Mpc."""
        return C_KM_S / self.H0_km_s_Mpc

    @property
    def OLambda0(self) -> float:
        """Dunkle-Energie-Dichteparameter, aus Flachheit: OLambda0 = 1 - Om0."""
        return 1.0 - self.Om0

    def E(self, z: np.ndarray | float) -> np.ndarray | float:
        """Dimensionsloser Hubble-Parameter E(z) = H(z)/H0 fuer flaches LambdaCDM."""
        z = np.asarray(z, dtype=float)
        return np.sqrt(self.Om0 * (1.0 + z) ** 3 + self.OLambda0)

    def comoving_distance_Mpc(self, z: np.ndarray | float) -> np.ndarray | float:
        """Line-of-sight comoving distance D_C(z) in Mpc (nicht h^-1 Mpc)."""
        z = np.atleast_1d(np.asarray(z, dtype=float))
        out = np.empty_like(z)
        for i, zi in enumerate(z):
            if zi < 0:
                raise ValueError("z muss >= 0 sein")
            integral, _ = integrate.quad(lambda zp: 1.0 / self.E(zp), 0.0, zi)
            out[i] = self.hubble_distance_Mpc * integral
        return out if out.size > 1 else float(out[0])

    def comoving_distance_h1Mpc(self, z: np.ndarray | float) -> np.ndarray | float:
        """Comoving distance in h^-1 Mpc, dem im Projekt verbindlichen Laengenmass.

        h = H0 / (100 km/s/Mpc); D_C[h^-1 Mpc] = D_C[Mpc] * h.
        """
        h = self.H0_km_s_Mpc / 100.0
        return self.comoving_distance_Mpc(z) * h

    def luminosity_distance_Mpc(self, z: np.ndarray | float) -> np.ndarray | float:
        """Luminosity distance D_L(z) = (1+z) * D_C(z), in Mpc."""
        z_arr = np.atleast_1d(np.asarray(z, dtype=float))
        d_c = np.atleast_1d(self.comoving_distance_Mpc(z_arr))
        d_l = (1.0 + z_arr) * d_c
        return d_l if d_l.size > 1 else float(d_l[0])

    def distance_modulus(self, z: np.ndarray | float) -> np.ndarray | float:
        """Distanzmodul mu(z) = 5 log10(D_L / 10 pc), D_L in Mpc -> pc via *1e6."""
        d_l_pc = np.atleast_1d(self.luminosity_distance_Mpc(z)) * 1.0e6
        mu = 5.0 * np.log10(d_l_pc / 10.0)
        return mu if mu.size > 1 else float(mu[0])

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "H0_km_s_Mpc": self.H0_km_s_Mpc,
            "Om0": self.Om0,
            "OLambda0": self.OLambda0,
            "Ob0": self.Ob0,
            "Tcmb0_K": self.Tcmb0_K,
            "Neff": self.Neff,
        }


def load_reference_cosmology(path: str | Path | None = None) -> ReferenceCosmology:
    """Laedt die Referenzkosmologie aus configs/cosmology.yaml (Schicht 0).

    Dies ist der einzige vorgesehene Einstiegspunkt, um an die Projekt-
    Referenzkosmologie zu kommen -- so bleibt sichergestellt, dass wirklich
    ueberall dieselbe (eine!) Kosmologie verwendet wird.
    """
    cfg_path = Path(path) if path is not None else _DEFAULT_CONFIG_PATH
    with open(cfg_path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if raw.get("model") != "FlatLambdaCDM":
        raise NotImplementedError(
            f"Nur FlatLambdaCDM ist implementiert, config sagt model={raw.get('model')!r}"
        )

    return ReferenceCosmology(
        name=raw["name"],
        H0_km_s_Mpc=float(raw["H0_km_s_Mpc"]),
        Om0=float(raw["Om0"]),
        Ob0=float(raw.get("Ob0", 0.0)),
        Tcmb0_K=float(raw.get("Tcmb0_K", 2.7255)),
        Neff=float(raw.get("Neff", 3.046)),
    )
