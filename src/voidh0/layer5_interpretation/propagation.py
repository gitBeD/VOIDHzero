"""Schicht 5 -- Interpretation / Propagation auf H0.

RF-E: "Welcher H0-Bias bzw. welche Obergrenze ergibt sich aus Δfvoid und dem
gemessenen Δμenv, unter Beruecksichtigung der proxy-abhaengigen Bandbreite?"

Herleitung der verwendeten Formel
----------------------------------
Der Distanzmodul ist mu = 5 log10(D_L / 10 pc). Fuer eine feste, aus dem
Hubble-Fluss unabhaengig bekannte "wahre" Leuchtkraftdistanz gilt naeherungs-
weise H0 ~ 1 / D_L (bei fixem z, im linearen Hubble-Regime). Eine kleine
Verschiebung des mittleren Distanzmoduls delta_mu zwischen der Kalibrator-
und der Hubble-Flow-Stichprobe (durch unterschiedliche Umgebungszusammen-
setzung) uebersetzt sich daher in eine relative H0-Verschiebung

    delta_H0 / H0 = -(ln 10 / 5) * delta_mu   [siehe z.B. Riess et al. 2016
                                                fuer den analogen Massen-Step]

Der relevante delta_mu ist dabei NICHT der volle gemessene Umgebungs-Step
Δμenv (Unterschied zwischen void- und wand-Objekten), sondern dessen Produkt
mit dem Unterschied im Void-Anteil zwischen Kalibrator- und Hubble-Flow-
Stichprobe, Δfvoid (WP2/RF-C):

    delta_mu = Δμenv * Δfvoid

Fuer eine Rangeschaetzung/Obergrenze (Nullergebnis, Exposé Abschnitt 5) wird
zusaetzlich die aus Abschnitt 3 dokumentierte proxy-abhaengige Bandbreite an
publizierten Δμenv-Werten mitgefuehrt.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

LN10_OVER_5 = np.log(10.0) / 5.0  # ≈ 0.460517


@dataclass
class H0BiasResult:
    delta_mu_env_mag: float
    delta_f_void: float
    delta_mu_effective_mag: float
    relative_H0_bias: float  # dimensionslos, delta_H0 / H0
    H0_ref_km_s_Mpc: float
    absolute_H0_bias_km_s_Mpc: float

    def summary(self) -> str:
        return (
            f"Δμ_env = {self.delta_mu_env_mag:+.4f} mag, "
            f"Δf_void = {self.delta_f_void:+.4f}\n"
            f"-> effektives Δμ = {self.delta_mu_effective_mag:+.5f} mag\n"
            f"-> relativer H0-Bias = {self.relative_H0_bias:+.5f} "
            f"({100 * self.relative_H0_bias:+.3f} %)\n"
            f"-> absoluter H0-Bias = {self.absolute_H0_bias_km_s_Mpc:+.3f} km/s/Mpc "
            f"(bei H0_ref = {self.H0_ref_km_s_Mpc:.2f} km/s/Mpc)"
        )


def propagate_to_H0_bias(
    delta_mu_env_mag: float,
    delta_f_void: float,
    H0_ref_km_s_Mpc: float,
) -> H0BiasResult:
    """Propagiert einen gemessenen Umgebungs-Step + Void-Fraktions-Mismatch auf H0.

    Siehe Moduldocstring fuer die Herleitung. `H0_ref_km_s_Mpc` ist der
    Referenzwert, um den herum die relative Verschiebung linearisiert wird
    (z.B. lokal gemessenes H0, nicht die Schicht-0-Referenzkosmologie).
    """
    delta_mu_eff = delta_mu_env_mag * delta_f_void
    rel_bias = -LN10_OVER_5 * delta_mu_eff
    abs_bias = rel_bias * H0_ref_km_s_Mpc

    return H0BiasResult(
        delta_mu_env_mag=delta_mu_env_mag,
        delta_f_void=delta_f_void,
        delta_mu_effective_mag=delta_mu_eff,
        relative_H0_bias=rel_bias,
        H0_ref_km_s_Mpc=H0_ref_km_s_Mpc,
        absolute_H0_bias_km_s_Mpc=abs_bias,
    )


def propagate_upper_limit(
    delta_mu_env_candidates_mag: list[float],
    delta_f_void: float,
    H0_ref_km_s_Mpc: float,
) -> H0BiasResult:
    """Konservative Obergrenze: nimmt das betragsgroesste Δμ_env aus einer Liste
    publizierter/gemessener Proxy-Werte (Exposé Abschnitt 3, Tabelle) und
    propagiert es. Fuer ein Nullergebnis liefert dies die zu berichtende
    Obergrenze auf den H0-Beitrag (Erfolgskriterium 'Nullergebnis',
    Exposé Abschnitt 5).
    """
    if not delta_mu_env_candidates_mag:
        raise ValueError("delta_mu_env_candidates_mag darf nicht leer sein")
    worst = max(delta_mu_env_candidates_mag, key=abs)
    return propagate_to_H0_bias(worst, delta_f_void, H0_ref_km_s_Mpc)
