"""pipeline/memory/base.py — MemoryMonitor protocol.

Authority: CONSTITUTION.md C21, C24, C26, D2057.
Ratified: 2026-07-22.

Cross-platform memory monitoring. macOS (vm_stat), Linux (cgroups), Windows (psutil).
Default: psutil_monitor.py (works everywhere).
"""

from abc import abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class MemoryMonitor(Protocol):
    """Protocol for cross-platform memory monitoring.

    Must work on macOS, Linux, Windows.
    """

    @abstractmethod
    def free_gb(self) -> float:
        """Available memory in GB."""
        ...

    @abstractmethod
    def used_gb(self) -> float:
        """Currently used memory in GB."""
        ...

    @abstractmethod
    def wired_gb(self) -> float:
        """Wired/locked memory in GB (macOS) or equivalent."""
        ...

    @abstractmethod
    def check_budget(self, required_gb: float) -> bool:
        """Check if required_gb is available. Returns True if safe to proceed."""
        ...

    @abstractmethod
    def growth_rate_pct(self, interval_sec: float = 60.0) -> float:
        """Memory growth rate as percentage over interval."""
        ...

    @property
    @abstractmethod
    def monitor_name(self) -> str:
        """Human-readable monitor identifier."""
        ...

