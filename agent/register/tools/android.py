

from ..wrapper import toolwrapper

from typing import Optional
# android_

@toolwrapper(name="android_tap_viewId", visible=True)
def tap(viewId:str):
    '''
    simulate a user's tap behavior on the screen, typically used to trigger buttons, links, or other clickable UI elements.
    viewId(str): Used to uniquely identify the view element that needs to be clicked, either as a resource ID, text content, or other attribute.
    '''
    pass

@toolwrapper(name="android_tap_position", visible=True)
def tap_pos(x:int, y:int):
    """
    simulate a user's tap behavior on the screen, typically used to trigger buttons, links, or other clickable UI elements.
    Args:
        x (int): the x coordinate of the tap position
        y (int): the y coordinate of the tap position
    """
    pass

@toolwrapper(name = "android_press_viewId", visible=True)
def press(viewId:str, duration:int):
    """
    simulate the behavior of a user pressing on the screen for a long period of time, often used to trigger context menus or other long-press events.
    Args:
        viewId (str): Used to uniquely identify the view element that needs to be pressed, either as a resource ID, text content, or other attribute.
        duration (int): the duration of the press in milliseconds.
    """
    pass

@toolwrapper(name = "android_press_pos", visible=True)
def press_pos(x:int, y:int, duration:int):
    """
    simulate the behavior of a user pressing on the screen for a long period of time, often used to trigger context menus or other long-press events.
    Args:
        x (int): the x coordinate of the press position
        y (int): the y coordinate of the press position
        duration (int): the duration of the press in milliseconds.
    """
    pass

@toolwrapper(name = "android_input", visible=True)
def input_text(viewId: Optional[str], text:str):
    """
    Simulates the user entering text into an input box, often used to fill out a form or search box.

    Args:
        viewId (Optional[str]): Used to uniquely identify the input box, either as a resource ID or other attribute. AN EMPTY PARAMETER IS ALLOWED.
        text (str): text that you want to input.
    """


@toolwrapper(name = 'android_back')
def back():
    """
    Simulates the user pressing the device's back button, often used to return to a previous screen or close the current activity.
    """
    pass

@toolwrapper(name = 'android_home')
def home():
    """
    Simulates the user pressing the device's Home button, often used to return to the home screen.
    """
    pass

@toolwrapper(name = 'android_swipe')
def swipe(start_x:int, start_y:int, end_x:int, end_y:int, duration:int):
    """
    Simulates the user's swipe behavior on the screen, commonly used for scrolling lists, switching pages, or other scenarios that require swipe.

    Args:
        start_x (int): the x coordinate of the swiping start position
        start_y (int): the x coordinate of the swiping start position
        end_x (int): the x coordinate of the swiping destination position
        end_y (int): the x coordinate of the swiping destination position
        duration (int): the duration of the press in milliseconds.
    """
    pass

@toolwrapper('android_get_notification')
def get_notification():
    """
    Used to get al the notification of the android device currently.
    """
    pass

@toolwrapper('android_add_notification')
def add_notification(title:str, content:str):
    """
    Used to add a notification to the android device. The notification will be displayed on the notification bar.
    Args:
        title (str): the title of the notification
        content(str): the content of the notification.
    """
    pass

@toolwrapper('android_get_calendar')
def get_calendar(start_time:int, end_time:int):
    """
    Used to get the calendar events of the android device within the specified time range.
    Args:
        start_time (int): the start time of the calendar events, in milliseconds since the Unix epoch.
        end_time (int): the end time of the calendar events, in milliseconds since the Unix epoch.
    """
    pass

@toolwrapper('android_add_calender')
def add_calendar(start_time:int, end_time:int, location:str, description:str, title:str):
    """
    Used to add a calendar event to the android device.
    Args:
        start_time (int): the start time of the calendar event, in milliseconds since the Unix epoch.
        end_time (int): the end time of the calendar event, in milliseconds since the Unix epoch.
        location (str): the location of the calendar event.
        description (str): the description of the calendar event.
        title (str): the title of the calendar event.
    """
    pass
