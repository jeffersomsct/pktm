"""
images/capture.py
Captura de janelas de poker -- SEM persistencia.

Quem chama decide se/onde salvar, passando table_id/hand_id para
images.snapshot_saver.SnapshotSaver.

Migracao da versao anterior:
  - Funcao snapshot(window) REMOVIDA (fazia captura + save junto).
  - Nova funcao capture(hwnd) -> PIL.Image | None (so captura).
  - Nova funcao get_window_rect(hwnd) -> (x, y, w, h) pra uso no matching.
"""
import ctypes
from ctypes import windll
from struct import pack, calcsize

import win32con
import win32gui
import win32ui
from PIL import Image

user32, gdi32 = windll.user32, windll.gdi32
PW_RENDERFULLCONTENT = 2


def getWindowBMAP(hwnd, returnImage=False):
    """Retorna (bmp, w, h) ou (bmp, w, h, img) de uma janela."""
    L, T, R, B = win32gui.GetWindowRect(hwnd)
    W, H = R - L, B - T
    x, y, w, h = (8, 8, W - 16, H - 16) if user32.IsZoomed(hwnd) else (7, 0, W - 14, H - 7)

    dc = user32.GetWindowDC(hwnd)
    dc1, dc2 = gdi32.CreateCompatibleDC(dc), gdi32.CreateCompatibleDC(dc)
    bmp1, bmp2 = (
        gdi32.CreateCompatibleBitmap(dc, W, H),
        gdi32.CreateCompatibleBitmap(dc, w, h),
    )

    obj1, obj2 = gdi32.SelectObject(dc1, bmp1), gdi32.SelectObject(dc2, bmp2)
    user32.PrintWindow(hwnd, dc1, PW_RENDERFULLCONTENT)
    gdi32.BitBlt(dc2, 0, 0, w, h, dc1, x, y, win32con.SRCCOPY)
    gdi32.SelectObject(dc1, obj1)
    gdi32.SelectObject(dc2, obj2)

    if returnImage:
        data = ctypes.create_string_buffer((w * 4) * h)
        bmi = ctypes.c_buffer(
            pack("IiiHHIIiiII", calcsize("IiiHHIIiiII"), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
        )
        gdi32.GetDIBits(dc2, bmp2, 0, h, ctypes.byref(data),
                        ctypes.byref(bmi), win32con.DIB_RGB_COLORS)
        img = Image.frombuffer('RGB', (w, h), data, 'raw', 'BGRX')

    gdi32.DeleteObject(bmp1)
    gdi32.DeleteDC(dc1)
    gdi32.DeleteDC(dc2)
    user32.ReleaseDC(hwnd, dc)

    return (bmp2, w, h, img) if returnImage else (bmp2, w, h)


def getSnapshot(hwnd) -> Image.Image:
    """Atalho: so quer a PIL.Image."""
    hbmp, w, h, img = getWindowBMAP(hwnd, True)
    gdi32.DeleteObject(hbmp)
    return img


def capture_window_memory(hwnd):
    """Captura janela diretamente da memoria (mais rapido, nao traz pra frente)."""
    try:
        if not win32gui.IsWindow(hwnd):
            return None

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0:
            return None

        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(save_bitmap)

        try:
            # PW_RENDERFULLCONTENT | PW_CLIENTONLY = 3
            result = windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)
            if not result:
                result = windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)
            if not result:
                result = windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 0)

            if result:
                bmpinfo = save_bitmap.GetInfo()
                bmpstr = save_bitmap.GetBitmapBits(True)
                return Image.frombuffer(
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1,
                )
            return None
        finally:
            win32gui.DeleteObject(save_bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)
    except Exception as e:
        print(f"Erro na captura de memoria: {e}")
        return None


def capture_protected_window(hwnd):
    """Captura janelas com restricao de acesso (fallback)."""
    try:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width, height = right - left, bottom - top
        if width <= 0 or height <= 0:
            return None

        window_dc = win32gui.GetWindowDC(hwnd)
        window_mfc = win32ui.CreateDCFromHandle(window_dc)
        try:
            mem_dc = window_mfc.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(window_mfc, width, height)
            mem_dc.SelectObject(bitmap)

            result = windll.user32.PrintWindow(hwnd, mem_dc.GetSafeHdc(), 2)
            if not result:
                result = windll.user32.PrintWindow(hwnd, mem_dc.GetSafeHdc(), 0)

            if result:
                bmpinfo = bitmap.GetInfo()
                bmpstr = bitmap.GetBitmapBits(True)
                return Image.frombuffer(
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1,
                )
            return None
        finally:
            if 'bitmap' in locals():
                win32gui.DeleteObject(bitmap.GetHandle())
            if 'mem_dc' in locals():
                mem_dc.DeleteDC()
            window_mfc.DeleteDC()
            win32gui.ReleaseDC(hwnd, window_dc)
    except Exception as e:
        print(f"Error in protected capture: {e}")
        return None


def capture(hwnd):
    """
    Captura uma janela e devolve PIL.Image.

    Ordem de tentativa:
      1. capture_window_memory  (mais rapido)
      2. getSnapshot            (fallback classico)
      3. capture_protected_window (ultimo recurso)

    NAO salva em disco -- use SnapshotSaver para isso.
    """
    img = capture_window_memory(hwnd)
    if img is None:
        img = getSnapshot(hwnd)
    if img is None:
        img = capture_protected_window(hwnd)
    return img


def get_window_rect(hwnd):
    """Retorna (x, y, w, h) da janela. Para mesas minimizadas retorna (-32000, ...)."""
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return left, top, right - left, bottom - top
