import logging
from datetime import datetime, timezone
import atexit

import aw_client

from aw_core import Event
from pynput import keyboard, mouse
import threading

logger = logging.getLogger(__name__)


class HIDInputListener:
    def __init__(self) -> None:
        self.events = []
        self.keylogger = logger.getChild("keyboard")
        self.mouselogger = logger.getChild("mouse")
        self.event_data = []
        self.has_event = threading.Event()
        self.pos = None
        self.delta = {"scrollX": 0, "scrollY": 0}
        self.scroll_timer = None
        self.move_timer = None

    def reset_data(self):
        self.event_data = []

    def push_event(self, event):
        self.event_data.append(event)
        self.has_event.set()

    def get_event(self):
        while True:
            if len(self.event_data) > 0:
                data: dict = self.event_data.pop(0)
                yield data
            else:
                # block until new event pushed
                self.has_event.wait()

        return None

    def start(self):
        self.keylistener = keyboard.Listener(
            on_press=self.on_press, on_release=self.on_release)
        self.keylistener.start()
        self.mouselistener = mouse.Listener(
            on_move=self.on_move, on_click=self.on_click, on_scroll=self.on_scroll)
        self.mouselistener.start()

    def on_move(self, x, y):
        # self.push_event({
        #     "from":"mouse",
        #     "type":"move",
        #     "time": datetime.now(tz=timezone.utc),
        #     "data": {
        #         "x":x,
        #         "y":y
        #     }
        # })
        if self.pos is None:
            self.pos = (x, y)

        def lazy_move_update():
            self.push_event({
                "from": "mouse",
                "type": "move",
                "time": datetime.now(tz=timezone.utc),
                "data": {
                    "x":self.pos[0],
                    "y":self.pos[1]
                }
            })
            del self.move_timer
            self.move_timer = None
        
        if self.move_timer is None:
            self.move_timer = threading.Timer(1, lazy_move_update,)
            self.move_timer.start()

    def on_click(self, x, y, button: mouse.Button, down):
        # self.logger.debug(f"Click: {button} at {(x, y)}")
        if down:
            self.events.append({
                "from": "mouse",
                "type": "click",
                "time": datetime.now(tz=timezone.utc),
                "data": {
                    "x": x,
                    "y": y,
                    "button": button.name,
                    "down": down
                }
            })
        else:
            down_event = list(filter(lambda x: x["from"] == "mouse" and x["type"] ==
                              "click" and x["data"]["button"] == button.name and x["data"]["down"], self.events))
            if len(down_event) == 0:
                self.mouselogger.debug(
                    f"Error: button {button} not pressed before release!")
                return
            if len(down_event) > 1:
                self.mouselogger.debug(
                    f"Error: button {button} pressed multiple times before release!")
                for e in down_event:
                    self.events.remove(e)
                return
            down_event = down_event[0]
            self.events.remove(down_event)
            self.push_event(
                {
                    "from": "mouse",
                    "time": down_event["time"],
                    "duration": (datetime.now(tz=timezone.utc) - down_event["time"]),
                    "data": {
                        "type": "click",
                        "button": button.name,
                    }
                }
            )
            # (datetime.now(tz=timezone.utc) - datetime.now(tz=timezone.utc)).total_seconds

    def on_scroll(self, x, y, scrollx, scrolly):
        # self.logger.debug(f"Scroll: {scrollx}, {scrolly} at {(x, y)}")
        def lazy_push():
            if self.delta["scrollX"] != 0 or self.delta["scrollY"]!=0:
                self.push_event({
                    "from": "mouse",
                    "type": "scroll",
                    "time": datetime.now(tz=timezone.utc),
                    "data": {
                        "x": x,
                        "y": y,
                        "scrollx": self.delta["scrollX"],
                        "scrolly": self.delta["scrollY"]
                    }
                })
            self.delta["scrollX"] = 0
            self.delta["scrollY"] = 0
            del self.scroll_timer
            self.scroll_timer = None
        
        if self.pos is None:
            if x != self.pos[0] or y!= self.pos[1]:
                if self.scroll_timer is not None:
                    self.scroll_timer.cancel()
                    del self.scroll_timer
                    self.scroll_timer = None
                lazy_push()
        self.delta["scrollX"] += scrollx
        self.delta["scrollY"] += scrolly
        if self.scroll_timer is None:
            self.scroll_timer = threading.Timer(1, lazy_push,)
            self.scroll_timer.start()


    def on_press(self, key: keyboard.KeyCode):
        # self.logger.debug(f"Press: {key}")
        # self.event_data["presses"] += 1
        # self.new_event.set()
        format_key = self._format_key(key)
        # adding pressed key to events
        self.events.append({
            "from": "keyboard",
            "type": "press",
            "time": datetime.now(tz=timezone.utc),
            "data": {
                "key": format_key
            }
        })

    def on_release(self, key: keyboard.KeyCode):
        # Don't count releases, only clicks
        # self.logger.debug(f"Release: {key}")
        format_key = self._format_key(key)
        press_events = list(filter(
            lambda x: x["from"] == "keyboard" and x["data"]["key"] == format_key, self.events))
        if len(press_events) == 0:
            self.keylogger.debug(
                f"Error: key {key} not pressed before release!")
            return
        if len(press_events) > 1:
            self.keylogger.debug(
                f"Error: key {key} pressed multiple times before release!")
            for e in press_events:
                self.events.remove(e)
            return
        press_event = press_events[0]
        self.events.remove(press_event)
        # adding the event to the data
        self.push_event(
            {
                "from": "keyboard",
                "time": press_event["time"],
                "duration": (datetime.now(tz=timezone.utc) - press_event["time"]),
                "data": {

                    "type": "pressAndRelease",
                    "key": format_key
                }
            }
        )

    def _format_key(self, key: keyboard.KeyCode) -> str:
        """Helper method to format the key name."""
        if hasattr(key, 'char') and key.char:
            return key.char
        elif hasattr(key, 'name'):
            return str(key.name)
        else:
            return str(key)
        
s_time = None
e_time = None

@atexit.register
def printTimeSpan():
    global s_time, e_time
    e_time = datetime.now()
    print(f"{s_time} - {e_time}")


# @click.command()
# @click.option("--testing", is_flag=True)
def main(testing: bool):
    logging.basicConfig(level=logging.DEBUG)
    global s_time
    s_time = datetime.now()
    logger.info("Starting watcher...")
    client = aw_client.ActivityWatchClient(
        "aw-watcher-input", testing=testing, port=5600)

    with client:
        # Create bucjet
        bucket_name = "{}_{}".format(
            client.client_name, client.client_hostname)
        eventtype = "os.hid.input"
        client.create_bucket(bucket_name, eventtype, queued=False)
        poll_time = 5

        hidlistener = HIDInputListener()
        hidlistener.start()
        
        # print(bucket_name)

        for event in hidlistener.get_event():

            client.heartbeat(bucket_name,
                             Event(timestamp=event.pop("time"), duration=event.pop(
                                 "duration", 0), data=event),
                             poll_time,
                             queued=True
                             )

    # while True:
    #     last_run = now

    #     # we want to ensure that the polling happens with a predictable cadence
    #     time_to_sleep = poll_time - datetime.now().timestamp() % poll_time
    #     # ensure that the sleep time is between 0 and poll_time (if system time is changed, this might be negative)
    #     time_to_sleep = max(min(time_to_sleep, poll_time), 0)
    #     sleep(time_to_sleep)

    #     now = datetime.now(tz=timezone.utc)

    #     # If input:    Send a heartbeat with data, ensure the span is correctly set, and don't use pulsetime.
    #     # If no input: Send a heartbeat with all-zeroes in the data, use a pulsetime.
    #     # FIXME: Doesn't account for scrolling
    #     # FIXME: Counts both keyup and keydown
    #     keyboard_data = keyboard.next_event()
    #     mouse_data = mouse.next_event()
    #     merged_data = dict(**keyboard_data, **mouse_data)
    #     e = Event(timestamp=last_run, duration=(now - last_run), data=merged_data)

    #     pulsetime = 0.0
    #     if all(map(lambda v: v == 0, merged_data.values())):
    #         pulsetime = poll_time + 0.1
    #         logger.info("No new input")
    #     else:
    #         logger.info(f"New input: {e}")
    #     client.heartbeat(bucket_name, e, pulsetime=pulsetime, queued=True)
if __name__ == "__main__":
    main(True)
