# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Simple event pub/sub used across core and manager.

Events carry typed payloads (positional/keyword args). To keep layers decoupled,
the payloads should be plain Python objects or dataclasses from `core.types`.

Subscriber exceptions are caught to avoid stopping other handlers.

Thread Safety:
When a tkinter root is registered via set_tk_root(), notifications from background
threads are automatically scheduled on the main thread using after_idle().
"""

import threading
from typing import Callable, List, Optional

# Global tkinter root reference for thread-safe GUI updates
_tk_root = None
_main_thread_id: Optional[int] = None


def set_tk_root(root) -> None:
    """Register the tkinter root for thread-safe event notifications.
    
    Call this once after creating the main application window.
    
    Args:
        root: The tkinter root window (e.g., ttk.Window instance)
    """
    global _tk_root, _main_thread_id
    _tk_root = root
    _main_thread_id = threading.current_thread().ident


def get_tk_root():
    """Get the registered tkinter root."""
    return _tk_root


def is_main_thread() -> bool:
    """Check if current thread is the main GUI thread."""
    if _main_thread_id is None:
        return True  # If not set, assume main thread
    return threading.current_thread().ident == _main_thread_id


class Event:
    """Event class for publisher-subscriber pattern.
    
    Thread-safe: When called from a background thread with a registered tk root,
    callbacks are automatically scheduled on the main GUI thread.
    """

    def __init__(self):
        self._subscribers: List[Callable] = []

    def subscribe(self, callback: Callable):
        """Subscribe a callback function to this event."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        """Unsubscribe a callback function from this event."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def notify(self, *args, **kwargs):
        """Notify all subscribers with given arguments.
        
        If called from a background thread and tk root is registered,
        callbacks are scheduled on the main thread using after_idle().
        """
        if is_main_thread() or _tk_root is None:
            # Already on main thread or no tk root - call directly
            self._do_notify(*args, **kwargs)
        else:
            # Schedule on main thread for thread safety
            _tk_root.after_idle(lambda: self._do_notify(*args, **kwargs))
    
    def _do_notify(self, *args, **kwargs):
        """execute the subscriber callbacks."""
        # Make a copy in case subscribers modify list during iteration
        subs = list(self._subscribers)
        for sub in subs:
            try:
                sub(*args, **kwargs)
            except Exception as e:
                pass
