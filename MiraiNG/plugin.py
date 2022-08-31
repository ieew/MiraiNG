import importlib
import inspect
from pathlib import Path
from typing import Callable, Optional, Set


_plugins: Set["Plugin"] = set()

class Plugin:
    def __init__(self, module: Callable) -> None:
        self.module = module

    @property
    def name(self) -> str:
        return self.module.__name__

    @property
    def version(self) -> str:
        return getattr(self.module, "__version__", "0.0.0")

    @property
    def init(self) -> Optional[Callable]:
        if (call := getattr(self.module, "__init__", None)) is not None:
            if inspect.isfunction(call):
                return call

    @property
    def update(self) -> Optional[Callable]:
        if (call := getattr(self.module, "__update__", None)) is not None:
            if inspect.isfunction(call):
                return call

    @property
    def upgrade(self) -> Optional[Callable]:
        if (call := getattr(self.module, "__upgrade__", None)) is not None:
            if inspect.isfunction(call):
                return call


def plugin_load(module_name: Path, module_prefix: str):
    module = None
    if module_name.is_file():
        module = importlib.import_module(f"{module_prefix}.{module_name.stem}")
    elif module_name.is_dir() and module_name.joinpath("__init__.py").exists():
        module = importlib.import_module(f"{module_prefix}.{module_name.stem}")

    if module:
        return Plugin(module)


def plugins_load(module_dir: Path, module_prefix: str):
    for i in module_dir.iterdir():
        if i.suffix in (".py", ".pyc", ".pyd"):
            if (module := plugin_load(i, module_prefix)) is not None:
                _plugins.add(module)
    return _plugins


def plugins_builtin_load():
    return plugins_load(Path(__file__).parent.joinpath("plugins"), 'MiraiNG.plugins')


def get_plugins() -> set:
    return _plugins
