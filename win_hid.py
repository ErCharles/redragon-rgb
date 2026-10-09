"""Luces en Windows. Solo el informe 0x08, 382 bytes. No abre el teclado de las teclas."""

import ctypes
from ctypes import wintypes

PACKET = 382
VID = 0x258A
PID = 0x0049
_SUCCESS = 0x00110000


class Missing(Exception):
    pass


class Denied(Exception):
    pass


def guard(pkt):
    data = bytes(pkt)
    if len(data) != PACKET or data[0] != 0x08 or data[1:4] != b"\x0a\x7a\x01" or b"\x05\x83\xb6" in data[:6]:
        raise RuntimeError("solo se puede enviar el color")


def _libs():
    hid = ctypes.WinDLL("hid", use_last_error=True)
    setup = ctypes.WinDLL("setupapi", use_last_error=True)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    return hid, setup, k32


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class IFACE(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", wintypes.DWORD),
        ("Reserved", ctypes.c_void_p),
    ]


class ATTR(ctypes.Structure):
    _fields_ = [
        ("Size", wintypes.ULONG),
        ("VendorID", wintypes.USHORT),
        ("ProductID", wintypes.USHORT),
        ("VersionNumber", wintypes.USHORT),
    ]


class CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", wintypes.USHORT),
        ("UsagePage", wintypes.USHORT),
        ("InputReportByteLength", wintypes.USHORT),
        ("OutputReportByteLength", wintypes.USHORT),
        ("FeatureReportByteLength", wintypes.USHORT),
        ("Reserved", wintypes.USHORT * 17),
        ("NumberLinkCollectionNodes", wintypes.USHORT),
        ("NumberInputButtonCaps", wintypes.USHORT),
        ("NumberInputValueCaps", wintypes.USHORT),
        ("NumberInputDataIndices", wintypes.USHORT),
        ("NumberOutputButtonCaps", wintypes.USHORT),
        ("NumberOutputValueCaps", wintypes.USHORT),
        ("NumberOutputDataIndices", wintypes.USHORT),
        ("NumberFeatureButtonCaps", wintypes.USHORT),
        ("NumberFeatureValueCaps", wintypes.USHORT),
        ("NumberFeatureDataIndices", wintypes.USHORT),
    ]


def _bind(hid, setup, k32):
    hid.HidD_GetHidGuid.argtypes = [ctypes.POINTER(GUID)]
    hid.HidD_GetAttributes.argtypes = [wintypes.HANDLE, ctypes.POINTER(ATTR)]
    hid.HidD_GetAttributes.restype = wintypes.BOOLEAN
    hid.HidD_GetPreparsedData.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
    hid.HidD_GetPreparsedData.restype = wintypes.BOOLEAN
    hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
    hid.HidD_FreePreparsedData.restype = wintypes.BOOLEAN
    hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(CAPS)]
    hid.HidP_GetCaps.restype = ctypes.c_long
    hid.HidD_SetFeature.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.ULONG]
    hid.HidD_SetFeature.restype = wintypes.BOOLEAN
    setup.SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID), wintypes.LPCWSTR, wintypes.HWND, wintypes.DWORD]
    setup.SetupDiGetClassDevsW.restype = ctypes.c_void_p
    setup.SetupDiEnumDeviceInterfaces.argtypes = [
        wintypes.HANDLE, ctypes.c_void_p, ctypes.POINTER(GUID), wintypes.DWORD, ctypes.POINTER(IFACE)
    ]
    setup.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL
    setup.SetupDiGetDeviceInterfaceDetailW.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(IFACE), ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p,
    ]
    setup.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL
    setup.SetupDiDestroyDeviceInfoList.argtypes = [wintypes.HANDLE]
    setup.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL
    k32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    k32.CreateFileW.restype = ctypes.c_void_p
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL


def _bad(handle):
    return not handle or handle == ctypes.c_void_p(-1).value


def _paths(hid, setup):
    guid = GUID()
    hid.HidD_GetHidGuid(ctypes.byref(guid))
    info = setup.SetupDiGetClassDevsW(ctypes.byref(guid), None, None, 0x12)
    if _bad(info):
        return
    try:
        idx = 0
        iface = IFACE()
        while True:
            iface.cbSize = ctypes.sizeof(iface)
            if not setup.SetupDiEnumDeviceInterfaces(info, None, ctypes.byref(guid), idx, ctypes.byref(iface)):
                return
            idx += 1
            need = wintypes.DWORD()
            setup.SetupDiGetDeviceInterfaceDetailW(info, ctypes.byref(iface), None, 0, ctypes.byref(need), None)
            if not need.value:
                continue
            buf = ctypes.create_string_buffer(need.value)
            ctypes.cast(buf, ctypes.POINTER(wintypes.DWORD))[0] = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
            if not setup.SetupDiGetDeviceInterfaceDetailW(info, ctypes.byref(iface), buf, need, None, None):
                continue
            off = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 4
            yield ctypes.wstring_at(ctypes.addressof(buf) + off)
    finally:
        setup.SetupDiDestroyDeviceInfoList(info)


def open_led():
    hid, setup, k32 = _libs()
    _bind(hid, setup, k32)
    denied = False
    mark = f"vid_{VID:04x}&pid_{PID:04x}"
    for path in _paths(hid, setup):
        if mark not in path.lower():
            continue
        handle = k32.CreateFileW(path, 0xC0000000, 0x7, None, 3, 0, None)
        if _bad(handle):
            if ctypes.get_last_error() == 5:
                denied = True
            continue
        attrs = ATTR()
        attrs.Size = ctypes.sizeof(attrs)
        if not hid.HidD_GetAttributes(handle, ctypes.byref(attrs)) or attrs.VendorID != VID or attrs.ProductID != PID:
            k32.CloseHandle(handle)
            continue
        prep = ctypes.c_void_p()
        if not hid.HidD_GetPreparsedData(handle, ctypes.byref(prep)):
            k32.CloseHandle(handle)
            continue
        caps = CAPS()
        status = hid.HidP_GetCaps(prep, ctypes.byref(caps))
        hid.HidD_FreePreparsedData(prep)
        if status != _SUCCESS or caps.FeatureReportByteLength != PACKET:
            k32.CloseHandle(handle)
            continue
        return handle
    if denied:
        raise Denied()
    raise Missing()
def send(handle, pkt):
    guard(pkt)
    hid, _, _ = _libs()
    hid.HidD_SetFeature.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.ULONG]
    hid.HidD_SetFeature.restype = wintypes.BOOLEAN
    buf = (ctypes.c_ubyte * PACKET).from_buffer_copy(bytes(pkt))
    if not hid.HidD_SetFeature(handle, ctypes.cast(buf, ctypes.c_void_p), PACKET):
        raise OSError(ctypes.get_last_error() or 1, "HidD_SetFeature")


def close(handle):
    if not handle:
        return
    _, _, k32 = _libs()
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL
    k32.CloseHandle(handle)
