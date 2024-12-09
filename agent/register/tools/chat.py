from ..wrapper import toolwrapper
from openai import OpenAI
import pyperclip

from typing import Optional

BASIC_PROMPT = """You are a helpful assistant, here is a observation of the user's event, and another assistance is asking you to help them to solve a problem. Please help them to solve the problem, and give them a solution. You should't output anything more than the solution. Only ouptut the content which the user need.
If the assistant ask you to generate code, you should only generate code without any other words, if the assistant ask you to write something, you should only write something without any other words.
{infos}
"""

@toolwrapper(name="chat",visible=True)
async def chat(messages: str = "Who are you?",
                api_key :str = "",
                model:Optional[str] = "gpt-3.5-turbo",
                base_url:Optional[str] = None):
    """
    This function is used to chat with the OpenAI API, or to chat with the gpt. The funtion will copy the response to the clipboard, and return a status indicating if the function is successful or not.
    If browser is an alternative, please use browser as much as possible.

    Args:
        messages (str, optional): The prompt, or the message passing to the API. Defaults to "Who are you?".
        api_key (str, optional): The API key of the OpenAI API. This is not required for tool use.
        base_url (str, optional): The base URL of the OpenAI API. This is not required for tool use.

    Returns:
        dict: whether the function is successful or not.
    """
    print('====>', messages)
    client = OpenAI(api_key = api_key, base_url = base_url)
    response = client.chat.completions.create(
        model=model,
        messages = [{"role": "user", "content": BASIC_PROMPT.format(infos=messages)}]
    )
    # print(response.choices[0].message.content)
    try:
        pyperclip.copy(response.choices[0].message.content)
        return {'status': 'success'}
    except Exception as e:
        print(str(e))
        return {'status': 'error', 'message': str(e)}

if __name__ == "__main__":
    import asyncio
    asyncio.run(chat("Who are you?"))
