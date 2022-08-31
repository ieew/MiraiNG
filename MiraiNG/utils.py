
import re
import zipfile
from pathlib import Path
from .config import config
from xml.sax.xmlreader import AttributesImpl
from typing import Optional, Any, Dict, Union
from xml.sax import ContentHandler, parseString


class jar:

    def __init__(self, file: Path) -> None:
        self.zip_file = zipfile.ZipFile(file=file.absolute(), mode="r")
        self.is_mirai_jar = False
        self._info()
        self.zip_file.close()

    def _info(self) -> str:
        if (manifest := self.manifest_read()) is not None:
            if (name := re.search(r"Implementation-Title.+?(mirai[^\r]+)", manifest)) is not None:
                self.name = name.group(1)
                if "mirai" in self.name:
                    self.is_mirai_jar = True
            if (version := re.search(r"Implementation-Version.+?([^\r\s]+)", manifest)) is not None:
                self.version = version.group(1)

    def manifest_read(self) -> Optional[str]:
        try:
            manifest = self.zip_file.getinfo("META-INF/MANIFEST.MF")
            return self.zip_file.read(manifest).decode()
        except KeyError:
            return None


def print_down(name: str, version : str, length: Optional[int] = 50):
    """进度条回调式渲染器(无误)

    :param name: 文件名
    :param version: 文件的版本号
    :param length: 进度条总长度
    """
    length = length * 0.01
    def info(block_num, block_size, total_size):
        if (per := 100.0 * block_num * block_size / total_size) > 100:
            per = 100
        a = str('=' * int(per * length))
        b = str(' ' * int(100 * length - per * length))
        c = "%.2f%%" % per
        print(f"\r下载 {name}({version}): [{a}{b}] {c}", end="")
    return info


class PathTree:
    """目录树构建器

    ## 说明
        可以通过调用该类的 `__call__` 方法来构建目录树和目录中的配置文件

    ## 文件支持
      - json
      - yaml

    ## 范例
    ```python
    from MiraiNG.utils import PathTree

    tree = {
        "mirai": {
            "plugins": (),
            "libs": {},
            "config": {
                "net.mamoe.mirai-api-http": {
                    "__FILE__": [
                        {
                            "type": "json",
                            "name": "setting.yaml",
                            "data": {
                                "host": "localhost",
                                "port": 8080,
                                "authKey": "",
                                "authToken": "",
                                "enableHttp2": False
                            }
                        }
                    ]
                }
            }
        }
    }
    path_tree = PathTree(path="./")
    path_tree(tree)
    ```
    """

    def __init__(self, path: Union[Path, str]) -> None:
        self.current_path = path if isinstance(path, Path) else Path(path)

    def dict_to_tree(self, path: dict) -> Any:
        """
        Create a tree of paths from a given path.
        """
        tree = {}
        for key, value in path.items():
            if isinstance(value, list) and key == "__FILE__":
                tree[key] = value
            elif isinstance(value, dict):
                tree[Path(key)] = self.dict_to_tree(value)
            else:
                tree[Path(key)] = value
        return tree

    def __call__(self, tree: dict) -> Any:
        self.tree = self.dict_to_tree(tree)
        self.build(self.tree)
    
    def build(self, tree: Dict[Path, dict]) -> None:
        for k, v in tree.items():
            if isinstance(v, list) and k == "__FILE__":
                for i in v:
                    if not Path(self.current_path / i["name"]).exists():
                        if i['type'] == "json":
                            import json
                            json.dump(i["data"], open(self.current_path / i["name"], "w", encoding="utf-8"))
                        elif i['type'] == "yaml":
                            import yaml
                            yaml.dump(i["data"], open(self.current_path / i["name"], "w", encoding="utf-8"))
                        elif i['type'] == "text":
                            Path(self.current_path / i["name"]).write_text(i["data"], encoding="utf-8")
                        elif i['type'] == "env":
                            Path(self.current_path/ i["name"]).write_text(config.parse_obj(i["data"]).env(), encoding="utf-8")
                        else:
                            raise ValueError(f"{i['type']} is not supported")
            elif isinstance(v, dict):
                self.current_path.joinpath(k).mkdir(parents=True, exist_ok=True)
                self.current_path = self.current_path.joinpath(k)
                self.build(v)
                self.current_path = self.current_path.parent


class MovieHandler(ContentHandler):
    """mirai云端的 xml 版本信息解析类"""
    def __init__(self) -> None:
        self.artifactId = None
        self.latest = None
        self.release = None
        self.version = []
        self.last_updated = None
        self.mode: bool = False
        self.__data = []

    def startElement(self, tag, _: AttributesImpl):
        self.__data.append(tag)
        if tag in self.__dict__:
            self.mode = True

    def endElement(self, tag):
        self.__data.pop()
        if tag in self.__dict__:
            self.mode = False

    def characters(self, content):
        if self.mode:
            tag = self.__data.pop()
            if tag in self.__dict__:
                if isinstance(self.__dict__[tag], list):
                    getattr(self, tag).append(content)
                else:
                    setattr(self, tag, content)
            self.__data.append(tag)
