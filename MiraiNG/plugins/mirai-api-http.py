import re
import zipfile
from pathlib import Path
from urllib import request

from MiraiNG import log
from MiraiNG.utils import print_down


__name__ = "mirai-api-http"
file: Path = None
file_version = "0.0.0"
cloud_version = None
new_version_url = None
new_file_name = None


def __init__():
    """一坨用来获取 mirai-api-http jar file 中的版本号的屎
    """
    jar = None
    for i in Path("plugins").iterdir():
        jar = zipfile.ZipFile(i)
        try:
            jar.getinfo("META-INF/mirai-api-http.kotlin_module")
        except:
            continue
        else:
            global file
            file = i
            break

    if jar:
        text = jar.read(jar.getinfo("net/mamoe/mirai/api/http/HttpApiPluginBase.class")).hex()

        b = list(b"qwertyuiopasdfghjklzxccvbnmQWERTYUIOPASDFGHJKLZXCVBNM0123456789.-_")
        if (redata := re.search(r"186e65742e6d616d6f652e6d697261692d6170692d68747470([a-f0-9]+?)0800", text)) is not None:
            d = ""
            for i in list(bytes.fromhex(redata.group(1))):
                if i in b:
                    d += chr(i)
            else:
                global file_version
                file_version = f"v{d}"


def __update__():
    Request = request.Request("https://github.com/project-mirai/mirai-api-http/tags")
    data = request.urlopen(Request).read()
    if (redata := re.findall(r"/project-mirai/mirai-api-http/releases/tag/([a-zA-Z0-9\.]+)", data.decode())) is not None:
        data = set({i for i in redata})
    
    global cloud_version
    for i in data:
        if cloud_version is None or i > cloud_version:
            cloud_version = i
    
    if file_version < cloud_version:
        log.info(f"mirai-api-http 有新版本可更新。当前版本: {file_version}  最新版本: {cloud_version}")
        Request = request.Request(f"https://github.com/project-mirai/mirai-api-http/releases/tag/{cloud_version}")
        data = request.urlopen(Request).read()
        if (redata := re.search(f"/project-mirai/mirai-api-http/releases/download/{cloud_version}/(.+?\.jar)", data.decode())) is not None:
            global new_version_url, new_file_name
            new_version_url = f"https://github.com{redata.group(0)}"
            new_file_name = redata.group(1)
            log.debug(f"新版本 mirai-api-http url={new_version_url}")


def __upgrade__():
    if new_file_name:
        try:
            prints = print_down(new_file_name, cloud_version, 30)
            request.urlretrieve(new_version_url, f"plugins/{new_file_name}", prints)
            print()
        except Exception as e:
            log.error(e)
            Path(f"plugins/{new_file_name}").unlink()
        else:
            if file is not None:
                file.unlink()
