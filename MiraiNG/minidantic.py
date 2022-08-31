from enum import Enum
import json
from typing import Any, Callable, Union


class BaseModel:

    def __init__(self, **kwargs) -> None:
        for k, v in self.__annotations__.items():
            if k in kwargs:
                try:
                    self._validate(k, v, kwargs[k])
                except: # noqa
                    ValueError(f"{k} is not {v}")
            else:
                self._validate(k, v, getattr(self, k))
            #log.debug(f"minidantic: name={k}, type={v}, default={kwargs.get(k, None)}, value={getattr(self, k)}")

    @classmethod
    def parse_obj(cla, obj) -> "BaseModel":
        return cla(**obj)

    @classmethod
    def parse_json(cla, json_str) -> "BaseModel":
        return cla(**json.loads(json_str))

    @classmethod
    def parse_env(cla, env: str) -> "BaseModel":
        data = {}
        for i in env.split("\n"):
            if i.strip() == "" or i.startswith("#") or i.startswith(";"):
                continue
            k, v = i.split("=")
            data[k] = v
        return cla(**data)

    def json(self) -> str:
        return json.loads(self.__dict__)

    def dict(self) -> dict:
        return self.__dict__

    def env(self) -> str:
        return "\n".join([f"{k}={v}" for k, v in self.__dict__.items()])

    def __str__(self) -> str:
        return " ".join([f"{k}={v}" for k, v in self.__dict__.items()])
    
    def __repr__(self) -> str:
        return str(self)

    def _validate(self, key, default, value: Union[bool, int, str, Callable, Any]):
        if issubclass(default, Enum):
            if value in default.__annotations__:
                setattr(self, key, getattr(default, value))
            elif value.isdigit() and int(value) in default._value2member_map_:
                setattr(self, key, default(int(value)))
            else:
                raise ValueError(f"{value} is not in {default}")
        elif issubclass(default, bool):
            if value in ("True", "true", True):
                setattr(self, key, True)
            elif value in ("False", "false", False):
                setattr(self, key, False)
            else:
                raise ValueError(f"{value} is not in {default}")
        elif issubclass(default, str):
            setattr(self, key, str(value))
        elif issubclass(default, int):
            setattr(self, key, int(value))
        elif issubclass(default, (list, dict)):
            setattr(self, key, json.loads(value))
        else:
            setattr(self, key, value)
