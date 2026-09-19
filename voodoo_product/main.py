from __future__ import annotations

from fastapi import FastAPI

from .composition import install_composed_product_platform
from .config import ProductConfig
from .g8_product_activation import resolve_g8_read_runtime_factory
from .version import __version__

app = FastAPI(
    title="VOODOO One",
    version=__version__,
    description="Governed AI operations control plane",
)
config = ProductConfig.from_env()
install_composed_product_platform(
    app,
    config=config,
    canonical_runtime_factory=resolve_g8_read_runtime_factory(config),
)
