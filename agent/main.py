'''
This file will set up a local server for our demo, making response for the tool calls for the agent.
You should first host a server by running this file, then to run the `ragent.py`
'''
import os
from typing import Literal, Dict, Optional

import fastapi
import uvicorn
from contextlib import asynccontextmanager

from register import ToolRegister
toolreg = ToolRegister()

@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    """
    Initialize the app.
    For windows user: If no appid is registed, the server will register an appid for our active agent, and save it to appid.txt.
    """
    global appid
    id_file = os.path.join(os.path.split(__file__)[0],'appid.txt')
    if os.name == 'nt':

        # TODO: is it possible if we can read our own AUMID but not from files?
        if not os.path.exists(id_file):
            # run script register_hkey_aumid.py
            import subprocess
            ret = subprocess.run(['python',os.path.join(os.path.split(__file__)[0],'register_hkey_aumid.py')])
            if ret.returncode != 0:
                raise Exception('Failed to register AUMID')

        with open(id_file) as f:
            appid = f.read().strip()

    print('Initializing Server complete.')

    yield


app = fastapi.FastAPI(lifespan=lifespan)


@app.get('/')
def root() -> dict[Literal['appid'], str]:
    """
    Returns the appid registed. It can also be found in `appid.txt`.

    Returns:
        dict[Literal['appid'], str]: the appid.
    """
    return {'appid': appid}

@app.get('/search')
async def search(query: str, search_engine:str = 'bing') -> Dict[str,str]:
    """
    Search Tool. This function will call the search tool, and open a tab with the accroding query and search engine. Details in register/tools/browser.py

    Args:
        query (str): Your query.
        search_engine (str, optional): The search engine to be used. Defaults to 'bing'.

    Returns:
        Dict[str,str],
        if succeeded, return {'status': 'success'}
        else, return {'status': 'error', 'error': error message}
    """
    return await toolreg["search"](query, search_engine)

@app.get('/chat')
async def chat(messages: str, api_key:str = "", base_url:Optional[str] = None) -> Dict[str,str]:
    """
    chat with ChatGPT-3.5-turbo. This function will call the chat tool, and pass the message to the chatbot, the response will be copied in the clipboard. Details in register/tools/chat.py
    You can modity the default model by modifying the `model` variable in `register/tools/chat.py`.

    Args:
        messages (str): The message to be sent to the chatbot.
        api_key (str, optional):  Defaults to "".
        base_url (str, optional):  Defaults to None.

    Returns:
        Dict[str,str],
        if succeeded, return {'status': 'success'}
        else, return {'status': 'error', 'error': error message}
    """
    # print(messages)
    return await toolreg["chat"](messages,api_key = api_key, base_url = base_url)

@app.get('/read')
async def read(filepath: str, line_number: int = 1) -> Dict[str,str]:
    """
    Read the file in `filepath`, start from `line_number`.
    This function will call the read tool, and return the content read.

    Args:
        filepath (str): Absolute path from workspace root.
        line_number (int, optional): Starting line number; supports negative values for reverse indexing.. Defaults to 1.

    Returns:
        Dict[str,str]
    If succeeded, return {'status': 'success', 'content': content}
    else, return {'status': 'error', 'error': error message}
    """
    try:
        # print(filepath, line_number)
        content = toolreg["read"](filepath, line_number)
        # print('>', content)
        return {'status': 'success', 'content': content}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@app.get("/rename_file")
async def rename_file(original_path:str, new_name:str) -> Dict[str,str]:
    """
    Rename a file in the workspace.

    Args:
        original_path (str): Absolute path from workspace root.
        new_name (str): New name for the file.

    Returns:
        Dict[str,str]
    If succeeded, return {'status': 'success'}
    else, return {'status': 'error', 'error': error message}
    """
    try:
        return {'status': 'success', 'message': toolreg["rename_file"](original_path, new_name)}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

if __name__ == '__main__':
    uvicorn.run("main:app", host='127.0.0.1', port=8000, reload=True)