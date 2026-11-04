"""Open the consent URL with Launch Services, without URL command arguments."""
import ctypes as C
import sys


def main():
    try:
        raw = sys.stdin.buffer.read(131073)
        if not raw or len(raw) > 131072: raise ValueError('input limit')
        core = C.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        services = C.CDLL('/System/Library/Frameworks/CoreServices.framework/CoreServices')
        core.CFStringCreateWithCString.argtypes = [C.c_void_p, C.c_char_p, C.c_uint32]
        core.CFStringCreateWithCString.restype = C.c_void_p
        core.CFURLCreateWithString.argtypes = [C.c_void_p, C.c_void_p, C.c_void_p]
        core.CFURLCreateWithString.restype = C.c_void_p
        core.CFRelease.argtypes = [C.c_void_p]
        services.LSOpenCFURLRef.argtypes = [C.c_void_p, C.c_void_p]
        services.LSOpenCFURLRef.restype = C.c_int32
        string = core.CFStringCreateWithCString(None, raw, 0x08000100)
        if not string: raise ValueError('invalid URL')
        url = core.CFURLCreateWithString(None, string, None)
        try:
            if not url or services.LSOpenCFURLRef(url, None): raise ValueError('launch failed')
        finally:
            if url: core.CFRelease(url)
            core.CFRelease(string)
        return 0
    except Exception:
        sys.stderr.write('browser_launch_failed')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
