import webbrowser
from typing import Literal
from urllib.parse import quote
from ..wrapper import toolwrapper

@toolwrapper(name="search", visible=True)
async def search(query:str="python+fastapi+windows+toast+notification+example", search_engine:Literal["google","bing","duckduckgo"]="bing"):
    """
    This function opens a web browser with a search query.

    Args:
        query (str, optional): The query you are about to search on a search engine.
        search_engine (Literal['google';,'bing';,'duckduckgo'], optional): the type of the searching engine. Defaults to "bing".

    Returns:
        dict: the status for running this function.
    """
    
    query = quote(query)
    
    match search_engine:
        case "google":
            url = f"https://www.google.com/search?q={query}"
        case "bing":
            url = f"https://www.bing.com/search?q={query}"
        case "duckduckgo":
            url = f"https://www.duckduckgo.com/?q={query}"
    
    try:
        webbrowser.open(url)
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'error', 'error': f"{str(e)}"}

if __name__ == "__main__":
    import asyncio
    asyncio.run(search())