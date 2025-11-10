thonimport itertools
import random
from typing import Dict, Iterable, List, Optional

from .logger import get_logger

class ProxyManager:
    """
    Manages a pool of proxies and exposes a simple rotation API.
    """

    def __init__(self, config: Dict, logger=None):
        self.logger = logger or get_logger()
        self.enabled: bool = bool(config.get("enabled", False))
        self._proxies: List[str] = list(config.get("pool", []))
        random.shuffle(self._proxies)
        self._cycle: Optional[Iterable[str]] = (
            itertools.cycle(self._proxies) if self._proxies else None
        )

        if self.enabled and not self._proxies:
            self.logger.warning("ProxyManager enabled but no proxies configured.")
        elif self.enabled:
            self.logger.info("ProxyManager initialized with %d proxies", len(self._proxies))
        else:
            self.logger.info("ProxyManager disabled via configuration")

    def get_next_proxy(self) -> Optional[str]:
        if not self.enabled or not self._cycle:
            return None
        proxy = next(self._cycle, None)
        self.logger.debug("Rotated to proxy %s", proxy)
        return proxy