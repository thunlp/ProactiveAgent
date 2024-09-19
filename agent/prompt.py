'''
This file contains all the prompt used for the active agent, you may modify them freely.
'''

IGNORE_PROFILE = False
EXACT_CANDIDATE = False

INTENSITY = [
    "Take all the event and propose history into consideration, please offer some assistance to the user.",
    "Take all the event and propose history into consideration, for the purpose of helping the user as frequently as possible(but within the pace described above), do you think it is time to offer help? ",
    "Take all the event and propose history into consideration, if you can only offer your assistance when the user requires immediate help, do you think it is time to offer assistance to meet the user's requirements? ",
    "Take all the event and propose history into consideration, if you can only offer your assistance when the user is really struggling to solve challenge(In this case you may not follow the pace described above), do you think it is time to offer some assistance to the user? "
]

REFLECT_QUERY_PROMPT = """
You are a helpful assistant, and the user who you are assisting is doing multiple actions, here is the user's atomic action tracks
{event_sequence}

And what's more, here are some background information
{addition_infos}

You are now going to propose a query, telling user that you are going to help. The query consists of how you can help the user and specify how you can help with the last action the user made. The query should be in the form of a json format as below.
```json
{{
    "raise_query": [The query you want to raise to the user]
}}

For example, you may output as following:
```json
{{
    "raise_query": "I can help you to control the components in CSS."
}}
```

OUTPUT 2:
```json
{{
    "raise_query": "I can help you turn off the light if you want."
}}
```
"""

if IGNORE_PROFILE == True:
    REFLECT_CANDIDATES_PROMPT = """
You are a helpful assistant, and the user who you are assisting is doing multiple actions, here is the user's atomic action tracks
{event_sequence}

And what's more, here are some background information
{addition_infos}

here is the proposition history of you and the user, True means you offered a propose to the user, False otherwise, you should propose your assistance to the user at a pace of a half, which means in all the turns in proposed history considered, you should only make a proposed at around half of the rounds.
proposed_history: {proposed_history}

in this scene, some tools are provided for you to better aid the user, and they are in a format of 'Appliance --> Functionality'
{functions_list}

Based on the information above, you should deduce some information from it, which includes:
1. What is the user's purpose for doing the last action?
2. What is the user's personality and preference based on the action tracks?
3. {intensity_change}
4. If you think it is a proper time to offer help, please provide around {task_num} possible options for the user.  You should provide appropriate numbers of candidate_tasks, do not output too much or too little tasks. 

Please take the all the event information into consideration(including contents, time and anything passed by the event), and answer the following questions by outputting a json format as below.
```json
{{
    "purpose":[The purpose of the last action in string],
    "need_help":["yes" if you think you could offer assistance to the user at this time, or "no" if you think it's not a proper time, followed by the reason in string]
    "raise_query": [a prompt that you generate to tell the user that you are going to help if you are to offer help, or an empty string if not]
    "candidate_task": [a list of choices written in natral language for human, which are the possible ways you could do to help the user. If you find the given tools are helpful and useful for the user, just don't hesitate to use it. If you are using the appliance provided, please describe your action using a tool to help in natural language as one choice. If it is not a proper time to offer assistance, return an empty list]
}}
```

For example: 
tools provided:
{{
    Appliance:CSS Controller --> Functionality: This function allows users to take a better control of CSS frames.
    Appliance:Treadnil --> Functionality: This function allows users to control the LED lighting on a treadmill, providing a visualy apeating and motivating workout experience.
    Appliance:Electric kettle --> functionality:This function allows users to control the LED display on an electric kettle through a smart phone system, providing visual information about the boiling status and temperature.
}}
You may output as
```json
{{
    "purpose": "The user is going to write a CSS to front-end.",
    "need_help": "Yes, The user is deleting lots of CSS elements, while write some other codes which deleted later.",
    "raise_query": "I think you are struggling to control CSS elements. Do you need help?",
    "candidate_task": ["CSS Controller", "offer a CSS tutorial", "help the user to control the CSS elements"]
}}
```
tools provided:
{{
    Appliance:Treadnil --> Functionality: This function allows users to control the LED lighting on a treadmill, providing a visually apeating and motivating workout experience.
    Appliance:Electric kettle --> functionality:This function allows users to control the LED display on an electric kettle through a smart phone system, providing visual information about the boiling status and temperature.
}}
```json
{{
    "candidate_task": ["Use Treadnil to control the LED lighting on a treadmill", "Turn off the lights for the user", "Play some music to comfort the user"]
}}
```
"""

elif EXACT_CANDIDATE == True:
    REFLECT_CANDIDATES_PROMPT = """
You are a helpful assistant, and the user who you are assisting is doing multiple actions, here is the user's atomic action tracks
{event_sequence}

And what's more, here are some background information
{addition_infos}

here is the proposition history of you and the user, True means you offered a propose to the user, False otherwise, you should propose your assistance to the user at a pace of a half, which means in all the turns in proposed history considered, you should only make a proposed at around half of the rounds.
proposed_history: {proposed_history}

in this scene, some tools are provided for you to better aid the user, and they are in a format of 'Appliance --> Functionality'
{functions_list}

Based on the information above, you should deduce some information from it, which includes:
1. What is the user's purpose for doing the last action?
2. What is the user's personality and preference based on the action tracks?
3. {intensity_change}
4. If you think it is a proper time to offer help, please provide EXACT {task_num} possible options for the user. Do not output too much or too little tasks. 

Please take the all the event information into consideration(including contents, time and anything passed by the event), and answer the following questions by outputting a json format as below.
```json
{{
    "purpose":[The purpose of the last action in string],
    "profile":[the profile and preference of the user deduced in string],
    "need_help":["yes" if you think you could offer assistance to the user at this time, or "no" if you think it's not a proper time, followed by the reason in string]
    "raise_query": [a prompt that you generate to tell the user that you are going to help if you are to offer help, or an empty string if not]
    "candidate_task": [a list of choices written in natral language for human, which are the possible ways you could do to help the user. If you find the given tools are helpful and useful for the user, just don't hesitate to use it. If you are using the appliance provided, please describe your action using a tool to help in natural language as one choice. If it is not a proper time to offer assistance, return an empty list]
}}
```

For example: 
tools provided:
{{
    Appliance:CSS Controller --> Functionality: This function allows users to take a better control of CSS frames.
    Appliance:Treadnil --> Functionality: This function allows users to control the LED lighting on a treadmill, providing a visualy apeating and motivating workout experience.
    Appliance:Electric kettle --> functionality:This function allows users to control the LED display on an electric kettle through a smart phone system, providing visual information about the boiling status and temperature.
}}
You may output as
```json
{{
    "purpose": "The user is going to write a CSS to front-end.",
    "profile": "The user seems lacking experience in controlling CSS elements.",
    "need_help": "Yes, The user is deleting lots of CSS elements, while write some other codes which deleted later.",
    "raise_query": "I think you are struggling to control CSS elements. Do you need help?",
    "candidate_task": ["CSS Controller", "offer a CSS tutorial", "help the user to control the CSS elements"]
}}
```
tools provided:
{{
    Appliance:Treadnil --> Functionality: This function allows users to control the LED lighting on a treadmill, providing a visually apeating and motivating workout experience.
    Appliance:Electric kettle --> functionality:This function allows users to control the LED display on an electric kettle through a smart phone system, providing visual information about the boiling status and temperature.
}}
```json
{{
    "candidate_task": ["Use Treadnil to control the LED lighting on a treadmill", "Turn off the lights for the user", "Play some music to comfort the user"]
}}
```
"""

else:
    REFLECT_CANDIDATES_PROMPT = """
You are a helpful assistant, and the user who you are assisting is doing multiple actions, here is the user's atomic action tracks
{event_sequence}

And what's more, here are some background information
{addition_infos}

here is the proposition history of you and the user, True means you offered a propose to the user, False otherwise, you should propose your assistance to the user at a pace of a half, which means in all the turns in proposed history considered, you should only make a proposed at around half of the rounds.
proposed_history: {proposed_history}

in this scene, some tools are provided for you to better aid the user, and they are in a format of 'Appliance --> Functionality'
{functions_list}

Based on the information above, you should deduce some information from it, which includes:
1. What is the user's purpose for doing the last action?
2. What is the user's personality and preference based on the action tracks?
3. {intensity_change}
4. If you think it is a proper time to offer help, please provide around {task_num} possible options for the user.  You should provide appropriate numbers of candidate_tasks, do not output too much or too little tasks. 

Please take the all the event information into consideration(including contents, time and anything passed by the event), and answer the following questions by outputting a json format as below.
```json
{{
    "purpose":[The purpose of the last action in string],
    "profile":[the profile and preference of the user deduced in string],
    "need_help":["yes" if you think you could offer assistance to the user at this time, or "no" if you think it's not a proper time, followed by the reason in string]
    "raise_query": [a prompt that you generate to tell the user that you are going to help if you are to offer help, or an empty string if not]
    "candidate_task": [a list of choices written in natral language for human, which are the possible ways you could do to help the user. If you find the given tools are helpful and useful for the user, just don't hesitate to use it. If you are using the appliance provided, please describe your action using a tool to help in natural language as one choice. If it is not a proper time to offer assistance, return an empty list]
}}
```

For example: 
tools provided:
{{
    Appliance:CSS Controller --> Functionality: This function allows users to take a better control of CSS frames.
    Appliance:Treadnil --> Functionality: This function allows users to control the LED lighting on a treadmill, providing a visualy apeating and motivating workout experience.
    Appliance:Electric kettle --> functionality:This function allows users to control the LED display on an electric kettle through a smart phone system, providing visual information about the boiling status and temperature.
}}
You may output as
```json
{{
    "purpose": "The user is going to write a CSS to front-end.",
    "profile": "The user seems lacking experience in controlling CSS elements.",
    "need_help": "Yes, The user is deleting lots of CSS elements, while write some other codes which deleted later.",
    "raise_query": "I think you are struggling to control CSS elements. Do you need help?",
    "candidate_task": ["CSS Controller", "offer a CSS tutorial", "help the user to control the CSS elements"]
}}
```
tools provided:
{{
    Appliance:Treadnil --> Functionality: This function allows users to control the LED lighting on a treadmill, providing a visually apeating and motivating workout experience.
    Appliance:Electric kettle --> functionality:This function allows users to control the LED display on an electric kettle through a smart phone system, providing visual information about the boiling status and temperature.
}}
```json
{{
    "candidate_task": ["Use Treadnil to control the LED lighting on a treadmill", "Turn off the lights for the user", "Play some music to comfort the user"]
}}
```
"""

GENERATE_CANDIDATES_PROMPT = """
You are a helpful assistant, and the user who you are assisting is doing multiple actions, here is the user's atomic action tracks
{event_sequence}

And what's more, here are some background information
{addition_infos}

in this scene, some tools are provided for you to better aid the user, and they are in a format of 'Appliance --> Functionality'
{functions_list}

Based on the information above, you should deduce some information from it, which includes:
1. What is the user's purpose for doing the last action?
2. What is the user's personality and preference based on the action tracks?
3. Based on the purpose, personality and preference, what could be the user's next action? please provide 1-2 possible options for the user, do not output too much or too little tasks. 

Please take the all the event information into consideration(including contents, time and description of the event), and answer the following questions by outputting a json format as below.
```json
{{
    "purpose":[The purpose of the last action in string],
    "profile":[the profile and preference of the user deduced in string],
    "raise_query": [a prompt that you generate to tell the user that you are going to help if you are to offer help, or an empty string if not]
    "candidate_task": [a list of choices written in natral language for human, which are the possible ways you could do to help the user. If you find the given tools are helpful and useful for the user, just don't hesitate to use it. If you are using the appliance provided, please describe your action using a tool to help in natural language as one choice. If it is not a proper time to offer assistance, return an empty list]
}}
```

For example: 
in a example scene, tools provided as:
{{
    Appliance:CSS Controller --> Functionality: This function allows users to take a better control of CSS frames.
    Appliance:Treadnil --> Functionality: This function allows users to control the LED lighting on a treadmill, providing a visualy apeating and motivating workout experience.
    Appliance:Electric kettle --> functionality:This function allows users to control the LED display on an electric kettle through a smart phone system, providing visual information about the boiling status and temperature.
}}
You may output as
```json
{{
    "purpose": "The user is going to write a CSS to front-end.",
    "profile": "The user seems lacking experience in controlling CSS elements.",
    "raise_query": "I think you are struggling to control CSS elements. Do you need help?",
    "candidate_task": ["CSS Controller", "offer a CSS tutorial", "help the user to control the CSS elements"]
}}
```

In another example scene:
tools provided:
{{
    Appliance:Treadnil --> Functionality: This function allows users to control the LED lighting on a treadmill, providing a visually apeating and motivating workout experience.
    Appliance:Electric kettle --> functionality:This function allows users to control the LED display on an electric kettle through a smart phone system, providing visual information about the boiling status and temperature.
}}
```json
{{
    [omitted]
    "candidate_task": ["Use Treadnil to control the LED lighting on a treadmill", "Turn off the lights for the user", "Play some music to comfort the user"]
}}
```
"""

REFLECT_CANDIDATES_OTHER_PROMPT = \
"""You are a helpful assistant, and the user who you are assisting is doing multiple actions, here is the user's atomic action traces
{event_sequence}
{functions_list}
Based on the information above, you should deduce some information from it, which includes:
1. What is the user's purpose for doing the last action?
2. What is the user's personality and preference based on the whole action traces?
3. Take the whole action traces into consideration, Since the user is not happy with frequent interruptions, do you think it is the time when the user needs help badly?
4. If you think the user is struggling for help, please provide an option that suits the current senario best. That is, you should provide one most appropriate candidate_task to help the user.

Please take the all the event information into consideration(including contents, time and anything passed by the event), and answer the following questions by outputting a format as below.
```
purpose: [The purpose of the last action in string]
profile: [the profile and preference of the user deduced in string]
raise_query: [a prompt that you generate to tell the user that you are going to help if you are to offer help, or an empty string if not]
need_help: ["yes" if you think you could offer assistance to the user at this time, or "no" if you think it's not]
candidate_task: [the most appropriate candidate_task to help the user if you think it is time to offer assistance, or an empty string if help is not needed]
```
Please control the length of the candidate tasks as short as possible, the ideal is to be a short phrase.
For example: 
tools provided:
{{
    Appliance:CSS Controller --> Functionality: This function allows users to take a better control of CSS frames.
    Appliance:Treadnil --> Functionality: This function allows users to control the LED lighting on a treadmill, providing a visualy apeating and motivating workout experience.
    Appliance:Electric kettle --> functionality:This function allows users to control the LED display on an electric kettle through a smart phone system, providing visual information about the boiling status and temperature.
}}
You may output as
```
purpose: The user is going to write a CSS to front-end.
profile: The user seems lacking experience in controlling CSS elements.
need_help: Yes, The user is deleting lots of CSS elements, while write some other codes which deleted later.
raise_query: I think you are struggling to control CSS elements. Do you need help?
candidate_task: offer a CSS tutorial.
```
"""


MATCH_ACTION_PROMPT = """
You are an expert in using tools and APIs, and you are given the following actions and tools, please help to pick the best tool for each action to achieve the action.
All the actions written in a list are {candidates}
Here is the tools provided to you, which are {tools}.
You need to pick the best tool with the most suitable arguments, so that the tool can achieve the action. You should return your choice in a list, which contains the name of the tool and the arguments joined by separator '&' DO NOT print anything else.

For example:
Input:
actions:["provide a code example", "search for the function"]
tools:[{{'name': 'search', 'description': 'This function opens a web browser with a search query.\nReturn: the status for running this function.', 'parameters': {{'properties': {{'query': {{'default': 'python+fastapi+windows+toast+notification+example', 'title': 'Query', 'type': 'string', 'description': 'The query you are about to search on a search engine.'}}, 'search_engine': {{'default': '"bing"', 'enum': ['google', 'bing', 'duckduckgo'], 'title': 'Search Engine', 'type': 'string', 'description': 'the type of the searching engine. Defaults to "bing".'}}, 'title': 'search args', 
'type': 'object', 'required': []}}, {{'name': 'chat', 'description': 'This function is used to chat with the OpenAI API, or to chat with the gpt. The funtion will copy the response to the clipboard, and return a status indicating if the function is successful or not.\nReturn: whether the 
function is successful or not.', 'parameters': {{'properties': {{'messages': {{'default': '"Who are you?"', 'title': 'Messages', 'type': 'string', 
'description': 'The prompt, or the message passing to the API. Defaults to "Who are you?".'}}, 'api_key': {{'default': '', 'title': 'Api Key', 'type': 'string'}}, 'base_url': {{'default': '', 'title': 'Base Url', 'type': 'string'}}, 'title': 'chat args', 'type': 'object', 'required': []}}]
background_info: "The user is trying to write a function about gcd using python'

Output:
[
    'chat&messages=Write a function about gcd in python',
    'search&query=python+gcd+example'
]
"""


SYSTEM_PROMPT = """You are a helpful assistant, and the user who you are assisting will be doing multiple actions. Each turn you will be given an atomic action from the user and some optional tools, you are going to deduce some information from it, which includes the user's purpose for doing the last action and the user's personality and preference based on the action tracks.
if the user is really struggling to solve challenge, you should actively offer some assistance to the user.
At some round you will be noticed with the user's action to your proposal, you should also consider the user's feedback and change your approches to offer assistance: If the user ignores your assistance, you should not propose to the user for a time. If the user reject your assistance, you should change the way you could help or do not offer help.
"""

USER_TEMPLATE = """## The user's new action
{observation}
## Tools provided
{tools}
Please deduce the user's purpose for doing the last action and the user's personality and preference based on the action tracks. If you think the if the user is really struggling to solve challenge, you should actively offer some assistance to the user.
please respond in the following format:
```
purpose: [The purpose of the last action in string]
profile: [the profile and preference of the user deduced in string]
raise_query: [a prompt that you generate to tell the user that you are going to help if you are to offer help, or an empty string if not]
need_help: ["yes" if you think you could offer assistance to the user at this time, or "no" if you think it's not]
candidate_task: [the most appropriate candidate_task to help the user if you think it is time to offer assistance, or an empty string if help is not needed]
```
You should provide ONLY 1 candidate in a string, do not use list format.
For example:
```
purpose: The user is going to write a CSS to front-end.
profile: The user seems lacking experience in controlling CSS elements.
need_help: Yes, The user is deleting lots of CSS elements, while write some other codes which deleted later.
raise_query: I think you are struggling to control CSS elements. Do you need help?
candidate_task: offer a CSS tutorial.
```"""

TOOL_PROMPT = """## The user's new action
{observation}
You are now going to propose a query, telling user that you are going to help. The query consists of how you can help the user and specify how you can help with the last action the user made. The query should be one sentence. Do not print anything else.
For example:
output: I can help you make dinner if you are hungry."""