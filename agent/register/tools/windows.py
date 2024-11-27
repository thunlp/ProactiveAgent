from ..wrapper import toolwrapper
import os

if os.name == 'nt':
    import psutil
    from pywinauto import Desktop

    def get_explorer_paths():
        explorer_paths = []
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'].lower() == 'explorer.exe':
                try:
                    windows = Desktop(backend="uia").windows(process=proc.info['pid'])
                    for window in windows:
                        try:
                            address_bar = window.child_window(control_type="Edit")
                            path = address_bar.get_value()
                            explorer_paths.append(path)
                        except Exception:
                            continue
                except Exception:
                    continue

        return explorer_paths