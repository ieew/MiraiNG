from typing import Dict, Optional, Tuple, Literal
from urllib import request
import xml.sax
from xml.sax.xmlreader import AttributesImpl
import os
import logging
from pathlib import Path
import zipfile
import re


def Request(
    url: str,
    headers={},
    data=None,
    *args, **kwargs
) -> request.Request:
    return request.Request(url, headers=headers, data=data, *args, **kwargs)


class MovieHandler(xml.sax.ContentHandler):
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
                    self.__dict__[tag].append(content)
                else:
                    self.__dict__[tag] = content
            self.__data.append(tag)


class Config:
    """配置储存类"""
    def __init__(self, **kv) -> None:
        """
        :说明:

            初始化并设定配置

        :注释:

            `source: str[maven, aliyun]`: 仅接受字符串 maven, aliyun 二选一, 不然可能会出错。default: maven  # noqa
            `update: bool`: 是否获取云端 mirai 更新信息。default: True
            `upgrade: bool`: 是否自动更新本地 mirai 版本。default: False
            `versioning: str[release, latest]`: 下载通道 仅接受字符串 release, latest 二选一， 不然可能会出错。default: release
            `jar_list: list`: 用来限制检查哪些 jar 的更新信息。不建议更改。default: [mirai-console, mirai-console-terminal, mirai-console-all]
        """
        self.source: Literal["maven", "aliyun"] = "maven"
        self.update: bool = True
        self.upgrade: bool = False
        self.versioning: Literal["release", "latest"] = "release"
        self.jar_list = [
            "mirai-console",
            "mirai-console-terminal",
            "mirai-core-all"
        ]
        self.jar_lib = "./libs/"
        self.mirai_lib = "mirai/"

        self.__data = {
            "source": {
                "maven": "https://repo.maven.apache.org/maven2/net/mamoe",
                "aliyun": "https://maven.aliyun.com/repository/public/net/mamoe"  # noqa
            },
            "versioning": ["latest", "release"]
        }

        for k, v in kv.items():
            self.__dict__[k] = v

    @property
    def data(self) -> dict:
        return self.__data

    @property
    def source_url(self) -> Optional[str]:
        if self.source in self.__data['source']:
            return f"{self.__data['source'][self.source]}"

    def __getattr__(self, key):
        return self.__dict__[key]

    def __setattr__(self, key, value):
        self.__dict__[key] = value

    def __str__(self) -> str:
        return str(self.__dict__)


class Update:
    """更新逻辑执行类"""
    def __init__(
        self,
        config: Optional[Config] = None
    ) -> None:
        self.config = config or Config()
        self.date_url: Dict[str, Optional[Tuple[MovieHandler, str]]] = {
            "mirai-console": None,
            "mirai-console-terminal": None,
            "mirai-core-all": None
        }
        self.file_version = {
            "mirai-console": None,
            "mirai-console-terminal": None,
            "mirai-core-all": None
        }

    def get_version(self, jar_name) -> MovieHandler:
        response = request.urlopen(
            Request(self.get_metadata_url(jar_name), headers=headers)
        )
        Handler = MovieHandler()
        xml.sax.parseString(response.read().decode(), Handler)
        return Handler

    def get_url(self, Handler: MovieHandler) -> Tuple[str, str]:
        name = Handler.artifactId
        version = Handler.__dict__[self.config.versioning]
        return f"{self.config.source_url}/{name}/{version}/{name}-{version}-all.jar"  # noqa

    def get_metadata_url(self, name) -> str:
        return f"{self.config.data.get('source').get(self.config.source)}/{name}/maven-metadata.xml"  # noqa

    def record_local_info(self, name, version):
        if self.file_version[name] is None:
            log.debug(f"本地 {name} 版本号: {version}")
            self.file_version[name] = version
        else:
            log.warning(f"存在多余的 {name}")

    def zip_read(self, file: Path) -> Tuple[Optional[str], Optional[str]]:
        with zipfile.ZipFile(file, "r") as zip:
            manifest = zip.read("META-INF/MANIFEST.MF").decode()
            version = re.search(r"(Implementation-Version)(:\s?)([0-9\.]{1,12})", manifest)  # noqa
            title = re.search(r"(Implementation-Title)(:\s?)([a-z\-]{5,25})", manifest)  # noqa
            if title is not None and version is not None:
                return title.group(3), version.group(3)
            else:
                return None, None

    def read_mirai_version(self):
        with Path(self.config.jar_lib) as f:
            for i in f.iterdir():
                try:
                    title, version = self.zip_read(i)
                    if None not in [title, version] and title in self.file_version:  # noqa
                        self.record_local_info(title, version)
                except OSError:
                    log.warning(f"文件 {i.resolve()} 已损坏，将会被直接删除")
                    i.unlink()
                except zipfile.BadZipFile:
                    log.warn(f"忽略文件: {i.resolve()}")

    def get_cloud_version(self):
        log.info("获取云端版本信息...")
        if self.config.update:
            for i in self.config.jar_list:
                Handler = self.get_version(i)
                log.debug(
                    "云端 "
                    f"{Handler.artifactId} 版本号: "
                    f"{Handler.__dict__[self.config.versioning]}"
                )
                url = self.get_url(Handler)
                if i in self.date_url:
                    self.date_url[i] = (Handler, url)

    def update(self):
        """更新检查器"""
        self.get_cloud_version()
        self.read_mirai_version()
        # print(self.file_version)
        # print(self.date_url)
        file_version = {k: v or "0.0.0" for k, v in self.file_version.items()}
        for i in self.config.jar_list:
            local = file_version[i]
            cloud = self.date_url[i][0].__dict__[self.config.versioning]
            if local < cloud:
                log.info(f"本地: {i}({local}) 云端: {i}({cloud}) | 可更新")

    def upgrade(self):
        """更新执行器"""
        log.info("更新 Mirai 文件...")

    def __call__(self):
        if self.config.update:
            self.update()

        if self.config.upgrade:
            self.upgrade()


class Main:
    """mirai 启动类"""
    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config()

    def __call__(self):
        log.info("MiraiRun...")


config: Optional[Config] = None
update: Optional[Update] = None
mirai_ok: Optional[Main] = None
headers: dict = {}

log: logging.Logger = logging.getLogger("MiraiNG")
log_hander = logging.StreamHandler()
log.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    fmt="{%(asctime)s %(name)s} : [%(levelname)s] | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log_hander.setFormatter(formatter)
log.addHandler(log_hander)


def init(header={}, **kwargs):
    global config, update, mirai_ok, headers
    config = Config(**kwargs)

    for path in [
        config.mirai_lib,
        f"{config.mirai_lib}/{config.jar_lib}",
        f"{config.mirai_lib}/plugins"
    ]:
        with Path(path) as f:
            if f.is_file():
                f.unlink()
            if not f.exists():
                f.mkdir()

    update = Update(config=config)
    mirai_ok = Main(config=config)
    headers = header


def main():
    os.chdir(config.mirai_lib)
    update()
    mirai_ok()


if __name__ == "__main__":
    init(upgrade=True, source="aliyun")
    main()
