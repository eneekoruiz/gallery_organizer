"""Keep active Windows imports awake on mains power, without lighting the screen."""
import ctypes
import os
import threading
from contextlib import contextmanager


class _PowerStatus(ctypes.Structure):
    _fields_ = [('ACLineStatus', ctypes.c_ubyte), ('BatteryFlag', ctypes.c_ubyte),
               ('BatteryLifePercent', ctypes.c_ubyte), ('SystemStatusFlag', ctypes.c_ubyte),
               ('BatteryLifeTime', ctypes.c_uint32), ('BatteryFullLifeTime', ctypes.c_uint32)]


@contextmanager
def keep_awake_on_ac():
    if os.name != 'nt':
        yield
        return
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetSystemPowerStatus.argtypes = [ctypes.POINTER(_PowerStatus)]
    kernel.GetSystemPowerStatus.restype = ctypes.c_int
    kernel.SetThreadExecutionState.argtypes = [ctypes.c_uint32]
    kernel.SetThreadExecutionState.restype = ctypes.c_uint32
    stop = threading.Event()

    def maintain_request():
        try:
            while not stop.is_set():
                status = _PowerStatus()
                online = kernel.GetSystemPowerStatus(ctypes.byref(status)) and status.ACLineStatus == 1
                kernel.SetThreadExecutionState(0x80000001 if online else 0x80000000)
                stop.wait(30)
        finally:
            kernel.SetThreadExecutionState(0x80000000)

    thread = threading.Thread(target=maintain_request, name='GalleryPowerRequest', daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=1)
