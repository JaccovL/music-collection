"""Cancel events for sync operations."""
import threading

_cancel_events = {
    'collection': threading.Event(),
    'track': threading.Event(),
    'wantlist': threading.Event(),
}


def is_cancelled(sync_type):
    """Check if a sync has been cancelled."""
    return _cancel_events.get(sync_type, threading.Event()).is_set()


def reset_cancel(sync_type):
    """Reset the cancel event for a sync type."""
    if sync_type in _cancel_events:
        _cancel_events[sync_type].clear()


def set_cancel(sync_type):
    """Set the cancel event for a sync type."""
    if sync_type in _cancel_events:
        _cancel_events[sync_type].set()
