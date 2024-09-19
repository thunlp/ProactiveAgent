from datetime import datetime
import sys

import json

from aw_client import ActivityWatchClient

from tqdm import tqdm

# consistent with the main.py
LISTEN_PORT = 5600
# in case you are using other chromes, change the bucket name to the accroding one.
WEB_BUCKET_NAME = "aw-watcher-web-edge"
CLIENT_HOSTNAME = None

platform = sys.platform

if platform.startswith("win"):
    VSCODE_NAME = "Code.exe"
else:
    VSCODE_NAME = "Code"


s_time = datetime(2024,6,3,1,26,37)
e_time = datetime(2024,6,3,1,33,43)

EXPORT_FILENAME = "./event_list.json"
APP_NAMES = ["explorer.exe","msedge.exe"]

# For mac user:
# APP_NAME_SERIES = ["Google Chrome","Safari\u6d4f\u89c8\u5668"]



def get_end_time(data):
    return data["timestamp"] + data["duration"]


def get_event_list(start_time:datetime, end_time:datetime):
    client = ActivityWatchClient(port = LISTEN_PORT)

    hostname = CLIENT_HOSTNAME

    if hostname is None:

        hostname = client.client_hostname

    bucket_name = "aw-watcher-{}_" + hostname

    # get afk information
    events_afk = client.get_events(bucket_id = bucket_name.format("afk"), start = start_time, end = end_time)[-1::-1]

    # get window information
    events_windows = client.get_events(bucket_id = bucket_name.format("window"), start = start_time, end = end_time)[-1::-1]

    # get vscode information
    events_vscode = client.get_events(bucket_name.format("vscode"), start = start_time, end = end_time)[-1::-1]

    # get chrome information
    events_chrome = client.get_events(WEB_BUCKET_NAME, start = start_time, end = end_time)[-1::-1]

    print(events_chrome)

    # get input information
    events_input = client.get_events(bucket_name.format("input"), start = start_time, end = end_time)[-1::-1]

    '''
    Now we parse the time span by using information from events_app.
    aw will parse the application when the user switches to a new app or the app's status changes.
    Therefore, we can use this information to split the time span into different app time blocks.
    Note: The number of the time span might influence the final event number.
    '''

    idx_afk = 0
    idx_vscode = 0
    idx_input = 0
    idx_web = 0

    event_list = []
    single_event = {}

    for event in tqdm(events_windows):
        single_event = {}
        single_event["timestamp"] = event["timestamp"].timestamp()
        single_event["duration"] = event["duration"].total_seconds()

        # get user input sequence
        single_event["user_input"] = []
        text_buffer = ""

        while idx_input < len(events_input) and get_end_time(events_input[idx_input]) < event["timestamp"]:
            idx_input += 1

        while idx_input < len(events_input) and get_end_time(events_input[idx_input]) < get_end_time(event):

            if events_input[idx_input]["data"]["from"] == "keyboard":

                # single_event["user_input"].append(events_input[idx_input]["data"])
                while idx_input < len(events_input) and\
                events_input[idx_input]["data"]["from"] == "keyboard" and\
                events_input[idx_input]["data"]["data"]["type"] == "pressAndRelease" and\
                get_end_time(events_input[idx_input]) < get_end_time(event):
                    
                    key = events_input[idx_input]["data"]["data"]["key"]

                    if key == 'space':
                        key = ' '
                    elif key == 'backspace':
                        key = '\b'
                    elif key =='\u0013' or key == 'enter':
                        key = '\n'
                    elif key in ['shift_r','shift_l']:
                        key = ''

                    if key == '\b':
                        text_buffer = text_buffer[:-1]
                    else:
                        text_buffer += key

                    idx_input += 1

            if text_buffer != "":
                # print(text_buffer)
                data = {"from":"keyboard","type":"input","data":text_buffer}
                single_event["user_input"].append(data)
                text_buffer = ""
            
            if idx_input < len(events_input):
                single_event["user_input"].append(events_input[idx_input]["data"])
                idx_input += 1

        # get user afk status
        # skip former afk status
        while idx_afk < len(events_afk) and get_end_time(events_afk[idx_afk]) < event["timestamp"]:
            idx_afk += 1

        if idx_afk < len(events_afk):

            single_event["status"] = events_afk[idx_afk]["data"]["status"]

        while idx_afk < len(events_afk) and get_end_time(events_afk[idx_afk]) < get_end_time(event):
            single_event["status"] = events_afk[idx_afk]["data"]["status"]
            idx_afk += 1

        # get relavant information.
        if event["data"]["app"] == VSCODE_NAME:
            single_event["app"] = event["data"]["app"]
            while idx_vscode < len(events_vscode) and get_end_time(events_vscode[idx_vscode]) < event["timestamp"]:
                idx_vscode += 1

            if idx_vscode < len(events_vscode):
                single_event["info"] = [events_vscode[idx_vscode]["data"]]
            else:
                single_event["info"] = []

            while idx_vscode < len(events_vscode) and get_end_time(events_vscode[idx_vscode]) < get_end_time(event):
                idx_vscode += 1
                if idx_vscode < len(events_vscode):
                    single_event["info"].append(events_vscode[idx_vscode]["data"])

        elif event["data"]["app"] in APP_NAMES :

            single_event["app"] = "web"
            single_event["info"] = []
            while idx_web < len(events_chrome) and get_end_time(events_chrome[idx_web]) < event["timestamp"]:
                idx_web += 1

            if idx_web < len(events_chrome):
                single_event["info"] = [events_chrome[idx_web]["data"]]
            else:
                single_event["info"] = []

            while idx_web < len(events_chrome) and get_end_time(events_chrome[idx_web]) < get_end_time(event):
                
                idx_web += 1
                if idx_web < len(events_chrome):
                    single_event["info"].append(events_chrome[idx_web]["data"])

        else:
            single_event["app"] = "other"
            single_event["info"] = []

        event_list.append(single_event)

    return event_list


a = get_event_list(s_time, e_time)

with open(EXPORT_FILENAME, "w") as f:
    json.dump(a, f, indent=4)

