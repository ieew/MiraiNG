from typing import List, Tuple
from urllib import request
from pathlib import Path
import os

from .log import log
from .config import config
from .utils import print_down, PathTree, jar, MovieHandler, parseString
from .plugin import plugins_load, plugins_builtin_load
import subprocess


directory_tree = {
    "mirai": {
        "libs": {},
        "plugins": {}
    },
    "plugins": {},
    "__FILE__": [
        {
            "name": ".env",
            "type": "env",
            "data": {
                "source": "Aliyun",
                "update": True,
                "upgrade": False,
                "mah_down": "Download"
            }
        }
    ]
}


class MiraiNG:
    def __init__(self) -> None:
        self.path = Path("./").absolute()
        self.mirai_path = self.path.joinpath("mirai")
        self.mirai_libs = self.path.joinpath("mirai/libs")
        self.mirai_plugin_path = self.path.joinpath("mirai/plugins")
        self.plugins = plugins_builtin_load()
        self.pending_upgrade: List[Tuple[Path, MovieHandler]] = []
        log.info("MiraiNG init start ...")
        path_tree = PathTree(path="./")
        path_tree(directory_tree)
        self.config: config = config.parse_env(self.path.joinpath(".env").read_text(encoding="utf-8"))
        log.info(f"config: {self.config}")
        os.chdir(self.mirai_path)
        for module in self.plugins:
            if module.init is not None:
                log.info(f"Plugins init {module.name} ...")
                module.init()
        log.info("MiraiNG init end ...")
        self.update()
        self.upgrade()

    def run(self):
        log.info("run ...")
        subprocess.run(("java", "-cp", f"{self.mirai_libs}\*", "net.mamoe.mirai.console.terminal.MiraiConsoleTerminalLoader"))

    def update(self):
        pending = ["mirai-console", "mirai-console-terminal", "mirai-core-all"]
        if self.config.update:
            log.debug("MiraiNG update start ...")
            for i in self.mirai_libs.iterdir():
                jar_file = jar(i)
                if jar_file.is_mirai_jar:
                    if jar_file.name in pending:
                        pending.remove(jar_file.name)

                    Handler = self._down_cloud_info(jar_file.name)

                    if jar_file.version < Handler.release:
                        log.info(f"{jar_file.name} 有新版本可更新。当前版本: {jar_file.version}  最新版本: {Handler.release}")
                        self.pending_upgrade.append((i, Handler, True))
            else:
                for i in pending:
                    Handler = self._down_cloud_info(i)
                    log.info(f"{i} 有新版本可更新。当前版本: (无)  最新版本: {Handler.release}")
                    self.pending_upgrade.append((i, Handler, False))
                else:
                    self.grade = True
                log.debug("MiraiNG update end ...")
        if self.config.plugins_update:
            for module in self.plugins:
                if module.init is not None:
                    log.info(f"Plugins update {module.name} ...")
                    module.update()

    def upgrade(self):
        if self.config.upgrade or self.grade:
            log.debug("MiraiNG upgrade start ...")
            for path, handler, rm_file in self.pending_upgrade:
                url = f"{self.config.source.value}/{handler.artifactId}/{handler.release}/{handler.artifactId}-{handler.release}-all.jar"
                try:
                    prints = print_down(handler.artifactId, handler.release, 30)
                    request.urlretrieve(url, f"{self.mirai_libs}/{handler.artifactId}-{handler.release}-all.jar", prints)
                    print()
                except Exception as e:
                    log.info(e)
                    if Path(f"{self.mirai_libs}/{handler.artifactId}-{handler.release}-all.jar").is_file():
                        Path(f"{self.mirai_libs}/{handler.artifactId}-{handler.release}-all.jar").unlink()
                    exit(1)
                else:
                    if rm_file:
                        path.unlink()
            log.debug("MiraiNG upgrade end ...")
        if self.config.plugins_upgrade:
            for module in self.plugins:
                if module.init is not None:
                    log.info(f"Plugins upgrade {module.name} ...")
                    module.upgrade()

    def _down_cloud_info(self, name: jar):
        Handler = MovieHandler()
        response = request.urlopen(f"{self.config.source.value}/{name}/maven-metadata.xml")
        parseString(response.read(), Handler)
        return Handler
