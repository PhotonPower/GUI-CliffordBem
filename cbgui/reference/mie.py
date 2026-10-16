"""Mie-Theorie für eine homogene, unmagnetische Kugel im verlustfreien Außenmedium (Bohren & Huffman, Zeitkonvention
e^{-iωt}, ε = (n + ik)² mit k ≥ 0 für Absorption – dieselbe Konvention wie die Bibliothek).

Dient in der GUI als Überlagerung (Validierung) für Einzelkugeln; die Bibliothek selbst hat ihre Referenz in
``tools/mie*.py`` des Bibliotheksprojekts (dort auch chirale und beschichtete Kugeln).
"""

from __future__ import annotations

import numpy as np


def _riccati(n: int, z: np.ndarray):
    """ψ_n(z) = z j_n(z), ξ_n(z) = z h_n^(1)(z) und Ableitungen (komplexes z)."""
    from scipy.special import spherical_jn, spherical_yn

    j = spherical_jn(n, z)
    jp = spherical_jn(n, z, derivative=True)
    y = spherical_yn(n, z)
    yp = spherical_yn(n, z, derivative=True)
    h = j + 1j * y
    hp = jp + 1j * yp
    psi, dpsi = z * j, j + z * jp
    xi, dxi = z * h, h + z * hp
    return psi, dpsi, xi, dxi


def mie_coefficients(m: complex, x: float, nmax: int | None = None):
    """Koeffizienten a_n, b_n (n = 1..nmax) für das relative Brechungsverhältnis m und den Größenparameter x."""
    if nmax is None:
        nmax = int(np.ceil(x + 4.0 * x ** (1 / 3) + 2.0))
    nmax = max(nmax, 3)
    a = np.zeros(nmax, complex)
    b = np.zeros(nmax, complex)
    for n in range(1, nmax + 1):
        psi_x, dpsi_x, xi_x, dxi_x = _riccati(n, np.asarray(x, complex))
        psi_m, dpsi_m, _, _ = _riccati(n, np.asarray(m * x, complex))
        a[n - 1] = (m * psi_m * dpsi_x - psi_x * dpsi_m) / (m * psi_m * dxi_x - xi_x * dpsi_m)
        b[n - 1] = (psi_m * dpsi_x - m * psi_x * dpsi_m) / (psi_m * dxi_x - m * xi_x * dpsi_m)
    return a, b


def mie_sphere(eps_sphere, n_host: float, radius_nm: float, lam_nm) -> dict:
    """Wirkungsquerschnitte einer Kugel. ``eps_sphere`` und ``lam_nm``: Zahl oder Array gleicher Länge.

    Rückgabe (Arrays): ``q_ext``, ``q_sca``, ``q_abs`` (Wirkungsgrade, bezogen auf πa²) und ``sigma_ext_nm2``,
    ``sigma_sca_nm2``, ``sigma_abs_nm2``.
    """
    lam = np.atleast_1d(np.asarray(lam_nm, float))
    eps = np.broadcast_to(np.atleast_1d(np.asarray(eps_sphere, complex)), lam.shape)
    q_ext = np.zeros(lam.shape)
    q_sca = np.zeros(lam.shape)
    for i, (l, e) in enumerate(zip(lam, eps, strict=False)):
        k = 2 * np.pi * n_host / l
        x = k * radius_nm
        m = np.sqrt(e) / n_host
        if m.imag < 0:  # Wurzel mit Im ≥ 0 (Absorption)
            m = -m
        a, b = mie_coefficients(m, x)
        n = np.arange(1, len(a) + 1)
        q_ext[i] = 2.0 / x**2 * np.sum((2 * n + 1) * (a + b).real)
        q_sca[i] = 2.0 / x**2 * np.sum((2 * n + 1) * (np.abs(a) ** 2 + np.abs(b) ** 2))
    area = np.pi * radius_nm**2
    return {
        "q_ext": q_ext,
        "q_sca": q_sca,
        "q_abs": q_ext - q_sca,
        "sigma_ext_nm2": q_ext * area,
        "sigma_sca_nm2": q_sca * area,
        "sigma_abs_nm2": (q_ext - q_sca) * area,
    }
