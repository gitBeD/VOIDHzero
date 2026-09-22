"""Schicht 4 -- Statistikmodell.

RF-D fragt: "Uebersteht ein Umgebungs-Step einen simultanen Fit mit Massen-
und sSFR-Step?" -- diese Funktion implementiert genau diesen simultanen
linearen Fit:

    residual_i = beta0 + beta_env * env_i + beta_mass * (mass_i - mass_ref)
                 + beta_sSFR * (log_sSFR_i - sSFR_ref) + eps_i

per gewichteter kleinster Quadrate (WLS), mit env_i in {0, 1} (wall=0, void=1)
als binaerem Indikator (die vorregistrierte Primaeranalyse, siehe Exposé
Abschnitt 9: "diskret als vorregistrierte Primaeranalyse").

Bewusst ohne statsmodels-Abhaengigkeit: reine numpy-Implementierung der
gewichteten Normalgleichungen, damit die Kernabhaengigkeiten (numpy/scipy)
minimal bleiben.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class StepModelResult:
    """Ergebnis eines simultanen Step-Modell-Fits."""

    param_names: list[str]
    beta: np.ndarray  # geschaetzte Koeffizienten, Reihenfolge wie param_names
    beta_err: np.ndarray  # 1-sigma Standardfehler
    n_obs: int
    dof: int
    chi2: float

    def env_step_mag(self) -> tuple[float, float]:
        """(Wert, 1-sigma-Fehler) des Umgebungs-Step-Koeffizienten beta_env."""
        idx = self.param_names.index("env")
        return float(self.beta[idx]), float(self.beta_err[idx])

    def env_step_significance(self) -> float:
        val, err = self.env_step_mag()
        return abs(val) / err if err > 0 else float("nan")

    def summary(self) -> str:
        lines = [f"Step-Modell-Fit (n={self.n_obs}, dof={self.dof}, chi2={self.chi2:.2f}):"]
        for name, b, e in zip(self.param_names, self.beta, self.beta_err):
            lines.append(f"  {name:>10s} = {b:+.4f} +/- {e:.4f}")
        sig = self.env_step_significance()
        lines.append(f"  --> Umgebungs-Step-Signifikanz: {sig:.2f} sigma")
        return "\n".join(lines)


def fit_environment_step(
    residual_mag: np.ndarray,
    env_indicator: np.ndarray,
    log_mstar: np.ndarray,
    log_sSFR: np.ndarray | None = None,
    sigma_mag: np.ndarray | None = None,
) -> StepModelResult:
    """Simultaner WLS-Fit von Hubble-Residuen auf Umgebung, Masse (, sSFR).

    Parameters
    ----------
    residual_mag : Hubble-Diagramm-Residuen mu_obs - mu_model, in mag.
    env_indicator : binaerer Umgebungsindikator (1 = void, 0 = wall).
    log_mstar : log10(Stellarmasse), wird um den Stichprobenmittelwert zentriert.
    log_sSFR : optional, log10(sSFR); falls None, wird nur nach Umgebung und
        Masse kontrolliert (RF-A: "uebersteht ein LSS-Step eine simultane
        Kontrolle fuer Masse und lokale sSFR" -- Uebergabe von None testet
        den reduzierten Fall).
    sigma_mag : optionale 1-sigma-Messfehler der Residuen fuer WLS-Gewichtung;
        falls None, wird ungewichtet (OLS) gefittet.
    """
    residual_mag = np.asarray(residual_mag, dtype=float)
    env_indicator = np.asarray(env_indicator, dtype=float)
    log_mstar = np.asarray(log_mstar, dtype=float)
    n = len(residual_mag)

    if not (len(env_indicator) == len(log_mstar) == n):
        raise ValueError("Alle Eingabearrays muessen dieselbe Laenge haben")

    mass_c = log_mstar - np.mean(log_mstar)
    columns = [np.ones(n), env_indicator, mass_c]
    param_names = ["intercept", "env", "mass_c"]

    if log_sSFR is not None:
        log_sSFR = np.asarray(log_sSFR, dtype=float)
        if len(log_sSFR) != n:
            raise ValueError("log_sSFR muss dieselbe Laenge wie residual_mag haben")
        sSFR_c = log_sSFR - np.mean(log_sSFR)
        columns.append(sSFR_c)
        param_names.append("sSFR_c")

    X = np.column_stack(columns)

    if sigma_mag is not None:
        sigma_mag = np.asarray(sigma_mag, dtype=float)
        w = 1.0 / sigma_mag**2
    else:
        w = np.ones(n)

    W = np.diag(w)
    XtW = X.T @ W
    cov_beta_unscaled = np.linalg.inv(XtW @ X)
    beta = cov_beta_unscaled @ XtW @ residual_mag

    resid = residual_mag - X @ beta
    dof = n - X.shape[1]
    chi2 = float(np.sum(w * resid**2))

    if sigma_mag is not None:
        # sigma_mag traegt die tatsaechliche Fehlerskala bereits in w = 1/sigma^2,
        # daher ist cov_beta_unscaled direkt die richtige Kovarianz.
        cov_beta = cov_beta_unscaled
    else:
        # Klassischer OLS-Fall: w=1 nimmt implizit sigma=1 an. Die tatsaechliche
        # Rauschskala wird aus den Fit-Residuen geschaetzt (sigma_hat^2 = chi2/dof)
        # und die Kovarianz entsprechend reskaliert: Cov(beta) = sigma_hat^2 * (X'X)^-1.
        sigma_hat2 = chi2 / dof if dof > 0 else np.nan
        cov_beta = cov_beta_unscaled * sigma_hat2

    beta_err = np.sqrt(np.diag(cov_beta))

    return StepModelResult(
        param_names=param_names,
        beta=beta,
        beta_err=beta_err,
        n_obs=n,
        dof=dof,
        chi2=chi2,
    )
