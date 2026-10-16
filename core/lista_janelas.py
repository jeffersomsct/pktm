import ctypes
import win32gui

def enum_windows_callback(hwnd, windows):
    if win32gui.IsWindowVisible(hwnd):  # Apenas janelas visíveis
        title = win32gui.GetWindowText(hwnd)
        if title:  # Ignora janelas sem título
            windows.append(title)

def listar_janelas():
    windows = []
    win32gui.EnumWindows(enum_windows_callback, windows)
    return windows

# Lista todas as janelas visíveis
janelas = listar_janelas()
for i, janela in enumerate(janelas, 1):
    print(f"{i}: {janela}")
