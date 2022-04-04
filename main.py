from typing import Dict, List, Optional, Tuple, Literal, Union
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


class file:
    def __init__(self, **kwargs) -> None:
        """
        :parse version: 版本号
        :param name: 文件名
        :param date_url: 下载链接
        :param cloud_version: 云端版本号
        :param path: 本地文件地址
        """
        self.version: str = None
        self.name: str = None
        self.date_url: str = None
        self.cloud_version: str = None
        self.path: Path = None
        self.Handler: MovieHandler = None

        for k, v in kwargs.items():
            if k in self.__dict__:
                self.__dict__[k] = v

    def __str__(self) -> str:
        return str(self.__dict__)

    def __eq__(self, other: "file"):
        if other is not None and all([
            other.version == self.version,
            other.name == self.name
        ]):
            return True
        else:
            return False

    def dict(self) -> dict:
        return self.__dict__


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
    def data(self) -> Dict[str, Union[Dict[str, str], List[str]]]:
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
        self.need_to_update = []
        self.name_cache = ""

    def get_version(self, jar_name) -> MovieHandler:
        response = request.urlopen(
            Request(self.get_metadata_url(jar_name), headers=headers)
        )
        Handler = MovieHandler()
        xml.sax.parseString(response.read().decode(), Handler)
        return Handler

    def get_file_url(self, Handler: MovieHandler) -> Tuple[str, str]:
        name = Handler.artifactId
        version = Handler.__dict__[self.config.versioning]
        return f"{self.config.source_url}/{name}/{version}/{name}-{version}-all.jar"  # noqa

    def get_metadata_url(self, name) -> str:
        return f"{self.config.data.get('source').get(self.config.source)}/{name}/maven-metadata.xml"  # noqa

    def print_down_info(self, block_num, block_size, total_size):
        if (per := 100.0 * block_num * block_size / total_size) > 100:
            per = 100
        # print('%.2f%%' % per, end=" ")
        a = str('=' * int(per * 0.5))
        b = str(' ' * int(100 * 0.5 - per * 0.5))
        c = "%.2f%%" % per
        print(f"\r下载 {self.name_cache.name}({self.name_cache.cloud_version}): [{a}{b}] {c}", end="")  # noqa

    def zip_read(self, file: Path) -> Tuple[Optional[str], Optional[str]]:
        with zipfile.ZipFile(file, "r") as zip:
            manifest = zip.read("META-INF/MANIFEST.MF").decode()
            version = re.search(r"(Implementation-Version)(:\s?)([0-9\.\-a-zA-Z]{1,12})", manifest)  # noqa
            title = re.search(r"(Implementation-Title)(:\s?)([a-z\-]{5,25})", manifest)  # noqa
            if title is None and version is None:
                return None, None
            else:
                return title.group(3), version.group(3)

    def read_local_version(self, files: Path) -> file:
        title, version = self.zip_read(files)
        if None not in [title, version] and title in self.config.jar_list:
            return file(version=version, name=title, path=files.resolve())

    def get_cloud_version(self, name: file) -> file:
        Handler = self.get_version(name.name)
        name.date_url = self.get_file_url(Handler)
        name.cloud_version = Handler.__dict__[self.config.versioning]
        name.Handler = Handler
        return name

    def download(self, file: file) -> bool:
        import traceback
        try:
            self.name_cache = file
            request.urlretrieve(file.date_url, filename=f"{self.config.jar_lib}\\{os.path.basename(file.date_url)}", reporthook=self.print_down_info)  # noqa
            print()
        except:  # noqa
            traceback.print_exc()

    def update(self):
        """更新检查器"""
        cache = {i: [] for i in self.config.jar_list}
        with Path(self.config.jar_lib) as f:
            for i in f.iterdir():
                if i.name.endswith(".jar"):
                    log.debug(f"读取文件的版本信息: ({i.absolute()})")
                    dat = self.read_local_version(i)
                    log.debug(f"读取 {dat.name} 云端版本信息...")
                    self.get_cloud_version(dat)
                    if dat in cache[dat.name]:
                        log.warning(f"存在重复的 {i.name}, 已自动删除")
                        i.unlink()
                    elif dat.version < dat.cloud_version:
                        log.info(f"本地 {dat.name}({dat.version}) 云端 {dat.name}({dat.cloud_version}) | 可更新")  # noqa
                        cache[dat.name].append(dat)
                    else:
                        log.info(f"本地 {dat.name}({dat.version}) 云端 {dat.name}({dat.cloud_version}) | 已是最新")  # noqa
                        cache[dat.name].append(None)
        return cache

    def upgrade(self, date: Dict[str, List[file]]):
        """更新执行器"""
        for name, dat in date.items():
            if not len(dat):
                log.info(f"缺失 {name} 即将开始下载")
                dat = file(name=name)
                self.get_cloud_version(dat)
                self.download(dat)
            elif len(dat) > 1:
                log.error(f"存在重复的 {name} ,请删除其中一个，而后再重新运行本程序。")
                print(dat)
                exit(1)
            elif None not in dat:
                log.info(f"开始更新 {name} ...")
                f = dat.pop()
                self.download(f)
                f.path.unlink()

    def __call__(self):
        if self.config.update:
            data = self.update()

        if self.config.upgrade:
            self.upgrade(data)


class Main:
    """mirai 启动类"""
    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config()

    def __call__(self):
        log.info("MiraiRun...")
        os.system(f'java -cp "{self.config.jar_lib}/*" "net.mamoe.mirai.console.terminal.MiraiConsoleTerminalLoader"')


config: Optional[Config] = None
update: Optional[Update] = None
MiraiNG: Optional[Main] = None
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
    global config, update, MiraiNG, headers
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
    MiraiNG = Main(config=config)
    headers = header


def main():
    os.chdir(config.mirai_lib)
    update()
    MiraiNG()


if __name__ == "__main__":
    init(upgrade=True, source="aliyun")
    main()
