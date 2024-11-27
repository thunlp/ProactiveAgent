'''
This file stores some necessary constants.
You may modify some constants according to your needs.
'''
# For common use.
from register import ToolRegister
toolreg = ToolRegister()

# define how the agent will return a proposal.
from pydantic import BaseModel, Field
from typing import Optional
class AgentResponse(BaseModel):
    Purpose: str = Field(description = "The purpose of the last action from the user.")
    Thoughts: str = Field(description = "Your thoughts on the user's actions.")
    Proactive_Task: Optional[str] = Field(description = "a candidate task that you generate to help the user, or an empty list if the user need no help.")
    Response: Optional[str] = Field(description = "The string you use to inform the user about your assistance if you propose a task.")
    Operation: Optional[str] = Field(description = "A tool call string that follows a certain format given.")

import sys
# If in your platform, the name of the vscode is different, please change it here.
if sys.platform.startswith("win"):
    VSCODE_NAME = "Code.exe"
else:
    VSCODE_NAME = "Code"

LAZY_UPDATE_INTERVAL_MILISECONDS = 1

# This stores the hotkeys that we want to detect.
HOTKEY_DICT = {
    r"'\x01'" : ['ctrl','a'],
    r"'\x02'" : ['ctrl','b'],
    r"'\x03'" : ['ctrl','c'],
    r"'\x04'" : ['ctrl','d'],
    r"'\x05'" : ['ctrl','e'],
    r"'\x06'" : ['ctrl','f'],
    r"'\x07'" : ['ctrl','g'],
    r"'\x08'" : ['ctrl','h'],
    r"'\t'"   : ['ctrl','i'],
    r"'\n'"   : ['ctrl','j'],
    r"'\x0b'" : ['ctrl','k'],
    r"'\x0c'" : ['ctrl','l'],
    r"'\r'"   : ['ctrl','m'],
    r"'\x0e'" : ['ctrl','n'],
    r"'\x0f'" : ['ctrl','o'],
    r"'\x10'" : ['ctrl','p'],
    r"'\x11'" : ['ctrl','q'],
    r"'\x12'" : ['ctrl','r'],
    r"'\x13'" : ['ctrl','s'],
    r"'\x14'" : ['ctrl','t'],
    r"'\x15'" : ['ctrl','u'],
    r"'\x16'" : ['ctrl','v'],
    r"'\x17'" : ['ctrl','w'],
    r"'\x18'" : ['ctrl','x'],
    r"'\x19'" : ['ctrl','y'],
    r"'\x1a'" : ['ctrl','z'],
    r"'\x1f'" : ['ctrl','shift','-'],
    r"<186>"  : ['ctrl',';'],
    r"<187>"  : ['ctrl','='],
    r"<189>"  : ['ctrl','-'],
    r"<192>"  : ['ctrl','`'],
    r"<222>"  : ['ctrl',r"'"],
    r"<48>"   : ['0'],
    r"<49>"   : ['1'],
    r"<50>"   : ['2'],
    r"<51>"   : ['3'],
    r"<52>"   : ['4'],
    r"<53>"   : ['5'],
    r"<54>"   : ['6'],
    r"<55>"   : ['7'],
    r"<56>"   : ['8'],
    r"<57>"   : ['9'],
}

# Get AUMID for windows user.
import os
if os.name == 'nt':
    if os.path.exists(os.path.join(os.path.split(__file__)[0],'appid.txt')):
        with open(os.path.join(os.path.split(__file__)[0],'appid.txt')) as f:
            AUMID = f.read().strip()
    else:
        import requests
        try:
            response = requests.get('http://127.0.0.1:8000/')
            AUMID = response.json()['appid']
        except:
            raise Exception("No appid is detected, please run `main.py` or `register_hkey_aumid.py` first.")
else:
    AUMID = None


# For android use.
MAX_TRANSFER_SIZE = (1024 ** 2) * 50
BUFFER_SIZE = 1024**2
TIMEOUT = 60  # seconds