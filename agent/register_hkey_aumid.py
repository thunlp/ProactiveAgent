'''
This file will regist an appid for the demo agent.
source from: https://github.com/DatGuy1/Windows-Toasts/blob/main/scripts/register_hkey_aumid.py
'''

# import argparse
import pathlib
import guid
import os

# noinspection PyCompatibility
import winreg
from typing import Optional

def register_hkey(appId: str, appName: str, iconPath: Optional[pathlib.Path]):
    '''
    Register the AUMID for the application.
    '''
    if iconPath is not None:
        if not iconPath.exists():
            raise ValueError(f"Could not register the application: File {iconPath} does not exist")
        elif iconPath.suffix != ".ico":
            raise ValueError(f"Could not register the application: File {iconPath} must be of type .ico")

    winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    keyPath = f"SOFTWARE\\Classes\\AppUserModelId\\{appId}"
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, keyPath) as masterKey:
        winreg.SetValueEx(masterKey, "DisplayName", 0, winreg.REG_SZ, appName)
        if iconPath is not None:
            winreg.SetValueEx(masterKey, "IconUri", 0, winreg.REG_SZ, str(iconPath.resolve()))

if __name__ == "__main__":
    appid = guid.GUID()
    # save guid to file
    with open(os.path.join(os.path.split(__file__)[0], "appid.txt"), "w") as f:
        f.write(appid)
    register_hkey(appid, "ActiveAgent", pathlib.Path(os.path.join(os.path.split(__file__)[0], "icon.ico")))
    print(f"Successfully registered the application ID '{appid}'")

# def main():  # pragma: no cover
#     parser = argparse.ArgumentParser(description="Register AUMID in the registry for use in toast notifications")
#     parser.add_argument("--app_id", "-a", type=str, required=True, help="Application User Model ID for identification")
#     parser.add_argument("--name", "-n", type=str, required=True, help="Display name on notification")
#     parser.add_argument("--icon", "-i", type=pathlib.Path, required=False, help="Path to image file for desired icon")
#     args = parser.parse_args()

#     register_hkey(args.app_id, args.name, args.icon)
#     print(f"Successfully registered the application ID '{args.app_id}'")


# if __name__ == "__main__":
#     main()