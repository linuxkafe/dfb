"""Module A — connectome co-processor for the fly-brain chatbot.

Implements the biological engine that drives a chatbot's temperament:

* ``EPGRingAttractor`` — E-PG ring (heading) attractor: a circular network with
  lateral inhibition that holds a single activity bump. The bump's angular
  position encodes the topic orientation (0..360 deg) and its displacement
  between turns measures topic rotation/drift.
* ``MushroomBody`` — sparse Kenyon cells projecting to MBONs, with DAN-driven
  reward/punishment plasticity (``++`` / ``--``). The MBON balance is a scalar
  topic affinity/aversion.
* ``NeuromodulatoryPool`` — octopamine fire-rate integrator with exponential
  decay (habituation): novelty drives activity up, repetition lets it leak down.

Only numpy is required. All heavy math is vectorised.
"""

from dataclasses import dataclass

import numpy as np


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def circular_distance(a_deg: float, b_deg: float) -> float:
    """Signed shortest angular distance a->b in degrees, in [-180, 180)."""
    return (b_deg - a_deg + 180.0) % 360.0 - 180.0


@dataclass
class ConnectomeState:
    """Snapshot of the connectome after a step."""

    orientation_deg: float
    epg_jump_deg: float
    affinity: float
    octopamine: float
    kc_active_fraction: float
    mbon: np.ndarray


# ---------------------------------------------------------------------------
# E-PG ring attractor
# ---------------------------------------------------------------------------

class EPGRingAttractor:
    """Circular heading ring: lateral inhibition holds a single activity bump.

    The bump centre (circular mean of activity) is the encoded angle. On each
    step the ring is driven by a bell-shaped injection centred on the current
    topic angle, so a persistent topic pins the bump while a new one makes it
    rotate. The rotation magnitude per step is ``epg_jump_deg``.
    """

    def __init__(self, n: int = 64, sigma_in: float = 2.0, seed: int = 42):
        self.n = n
        self.sigma_in = sigma_in
        self.orientation_deg = 0.0
        self.activity = np.zeros(n)
        idx = np.arange(n)
        dist = np.minimum(
            (idx[:, None] - idx[None, :]) % n,
            (idx[None, :] - idx[:, None]) % n,
        )
        w = np.exp(-(dist**2) / (2 * 1.6**2)) - 0.55 * np.exp(-(dist**2) / (2 * 8.0**2))
        np.fill_diagonal(w, 0.0)
        row = np.abs(w).sum(axis=1, keepdims=True)
        self.kernel = w / np.maximum(row, 1e-9)
        rng = np.random.RandomState(seed)
        self.activity = rng.uniform(0.0, 0.05, size=n)
        self._angles = 2.0 * np.pi * idx / n

    def _bell(self, center_deg: float) -> np.ndarray:
        c = center_deg % 360.0
        d = np.abs((self._angles - np.radians(c) + np.pi) % (2 * np.pi) - np.pi)
        return np.exp(-(d**2) / (2 * self.sigma_in**2))

    @staticmethod
    def _circular_mean(activity, angles) -> float:
        total = float(activity.sum())
        if total <= 0.0:
            return 0.0
        x = float((activity * np.cos(angles)).sum())
        y = float((activity * np.sin(angles)).sum())
        return np.degrees(np.arctan2(y, x)) % 360.0

    def step(self, target_deg: float, amplitude: float = 1.0, n_solve: int = 20) -> float:
        """Inject a bump at ``target_deg`` and relax the ring; returns orientation.

        Returns
        -------
        float
            New orientation in degrees (0..360).
        """
        out = self._bell(target_deg) * float(amplitude)
        a = self.activity.copy()
        k = self.kernel
        for _ in range(n_solve):
            a = np.maximum(a + 0.5 * (-a + k @ a + out), 0.0)
        self.activity = a
        new = self._circular_mean(a, self._angles)
        self._last_jump = circular_distance(self.orientation_deg, new)
        self.orientation_deg = new
        return new

    @property
    def last_jump(self) -> float:
        """Signed angle travelled by the bump on the last step (degrees)."""
        return getattr(self, "_last_jump", 0.0)


# ---------------------------------------------------------------------------
# Mushroom body
# ---------------------------------------------------------------------------

class MushroomBody:
    """Sparse Kenyon cells -> MBONs, with DAN reward/punishment plasticity.

    Sensory input is sparse-coded into Kenyon cells (random binary projections).
    MBONs are valenced: some encode approach (positive affinity), others
    avoidance (negative affinity). Dopaminergic neurons (DANs) fire on ``++`` /
    ``--`` feedback and update the KC->MBON weights Hebbian-style, biasing the
    net affinity in the rewarded direction.
    """

    def __init__(
        self,
        n_sensory: int = 8,
        n_kc: int = 160,
        n_mbon: int = 8,
        kc_density: float = 0.12,
        seed: int = 42,
    ):
        self.n_sensory = n_sensory
        self.n_kc = n_kc
        self.n_mbon = n_mbon
        rng = np.random.RandomState(seed)
        self._proj = (rng.rand(n_sensory, n_kc) < kc_density).astype(float)
        self.wkc = rng.normal(0.0, 1.0, size=(n_kc, n_mbon))
        self.valence = np.zeros(n_mbon)
        self.valence[: n_mbon // 2] = 1.0
        self.valence[n_mbon // 2 :] = -1.0
        self.kc = np.zeros(n_kc)
        self.mbon = np.zeros(n_mbon)
        self.dan = 0.0
        self.affinity = 0.0

    def _update_affinity(self):
        self.mbon = np.tanh(self.kc @ self.wkc)
        self.affinity = float(np.dot(self.mbon, self.valence)) / self.n_mbon

    def inject_sensory(self, sensory: np.ndarray) -> None:
        """Feed current into MB sensory cells; sparse-code into Kenyon cells."""
        s = np.asarray(sensory, dtype=float)
        if s.size < self.n_sensory:
            s = np.resize(s, self.n_sensory)
        kc_in = s[: self.n_sensory] @ self._proj
        self.kc = np.maximum(kc_in - 1.0, 0.0)  # sparse threshold
        self._update_affinity()

    def reinforce(self, reward: float, lr: float = 0.2) -> None:
        """DAN-driven Hebbian update on reward (+1) or punishment (-1)."""
        act = self.kc[:, None]
        drive = float(np.clip(reward, -1.0, 1.0))
        delta = lr * drive * (act * self.valence[None, :])
        self.wkc = np.clip(self.wkc + delta, -3.0, 3.0)
        self.dan = drive
        self._update_affinity()


# ---------------------------------------------------------------------------
# Neuromodulatory pool
# ---------------------------------------------------------------------------

class NeuromodulatoryPool:
    """Octopamine: novelty integrator with exponential decay (habituation).

    ``drive`` (0..1) is the novelty signal from the semantic encoder. The
    octopamine pool integrates it and leaks exponentially, so sustained
    repetition habituates it toward baseline.
    """

    def __init__(self, tau: float = 3.0, baseline: float = 0.15, gain: float = 1.2):
        self.tau = tau
        self.baseline = baseline
        self.gain = gain
        self.value = baseline
        self.drive = 0.0

    def step(self, drive: float, dt: float = 1.0) -> float:
        """Advance one turn (dt=1 turn); returns current octopamine level."""
        self.drive = float(np.clip(drive, 0.0, 1.0))
        target = self.baseline + self.gain * self.drive
        self.value = float(np.clip(
            self.value + (target - self.value) * (1.0 - np.exp(-dt / self.tau)),
            0.0, 1.0,
        ))
        return self.value


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------

class FlyBrain:
    """Composes the connectome modules and advances one turn per message."""

    def __init__(self, n_ring: int = 64, seed: int = 42):
        self.ring = EPGRingAttractor(n=n_ring, seed=seed)
        self.mb = MushroomBody(seed=seed + 1)
        self.pool = NeuromodulatoryPool()
        self.steps = 0

    def step(
        self,
        topic_angle_deg: float,
        novelty: float = 0.0,
        sensory: np.ndarray | None = None,
        reward: float = 0.0,
    ) -> ConnectomeState:
        """Advance the connectome for one conversational turn."""
        self.ring.step(topic_angle_deg, amplitude=np.clip(0.3 + novelty, 0.0, 1.0))
        self.mb.inject_sensory(sensory if sensory is not None else self.sensory_default())
        if reward != 0.0:
            self.mb.reinforce(reward)
        self.pool.step(novelty)
        self.steps += 1
        return ConnectomeState(
            orientation_deg=self.ring.orientation_deg,
            epg_jump_deg=self.ring.last_jump,
            affinity=self.mb.affinity,
            octopamine=self.pool.value,
            kc_active_fraction=float(np.mean(self.mb.kc > 0.0)),
            mbon=self.mb.mbon.copy(),
        )

    def sensory_default(self) -> np.ndarray:
        """Baseline sensory vector tagged with the current ring orientation."""
        c = np.cos(np.radians(self.ring.orientation_deg))
        s = np.sin(np.radians(self.ring.orientation_deg))
        return np.array([c, s, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0])