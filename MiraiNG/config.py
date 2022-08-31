from enum import Enum
from .minidantic import BaseModel


class BaseEnum(Enum):
    def __str__(self) -> str:
        return self.name


class Source(BaseEnum):
    Aliyun: str = "https://maven.aliyun.com/repository/public/net/mamoe"
    Maven: str = "https://repo.maven.apache.org/maven2/net/mamoe"


class Mah(BaseEnum):
    No: int = 0
    Download: int = 1
    Update: int = 2
    Upgrade: int = 3


class config(BaseModel):
    source: Source = Source.Aliyun
    update: bool = True
    upgrade: bool = False
    mah_down: Mah = Mah.Download
    plugins_update: bool = False
    plugins_upgrade: bool = False
    Graia: bool = False
    Nonebot: bool = False
