"""
core/window_handler.py
Deteccao de janelas de poker com suporte multi-mesa.

Migracao da versao anterior:
  - detect_window() (retornava UMA imagem) -> mantido por compat, mas
    internamente chama detect_windows() e pega o primeiro.
  - Nova funcao detect_windows() -> lista de mesas, cada uma com
    {hwnd, title, x, y, w, h, image}.
  - Filtra mesas minimizadas (Windows coloca em -32000).
"""
import win32gui
import win32process
import numpy as np
import cv2

from images.capture import capture, get_window_rect


def get_all_child_windows(parent_handle):
    """Obtem todas as janelas filhas do handle da janela principal."""
    child_windows = []

    def callback(hwnd, _):
        title = win32gui.GetWindowText(hwnd).strip()
        if title:
            child_windows.append((hwnd, title))
        return True

    win32gui.EnumChildWindows(parent_handle, callback, None)
    return child_windows


def get_existing_windows(process_id):
    existing_windows = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            _, wnd_process_id = win32process.GetWindowThreadProcessId(hwnd)
            if wnd_process_id == process_id:
                title = win32gui.GetWindowText(hwnd).strip()
                if title:
                    existing_windows.append((hwnd, title))
        return True

    win32gui.EnumWindows(callback, None)
    return existing_windows


def search_parent_window(window_title):
    """Retorna todas as janelas associadas ao processo da sala de poker."""
    main_handle = win32gui.FindWindow(None, window_title)
    if not main_handle:
        print("Janela principal do jogo nao encontrada.")
        return []

    child_windows = get_all_child_windows(main_handle)
    _, process_id = win32process.GetWindowThreadProcessId(main_handle)
    all_windows = get_existing_windows(process_id)

    # Mescla (evita duplicatas por hwnd)
    seen = set()
    merged = []
    for hwnd, title in child_windows + all_windows:
        if hwnd not in seen and title:
            seen.add(hwnd)
            merged.append((hwnd, title))
    return merged


def detect_windows(poker_room: str, exclude_lobby: bool = True) -> list:
    """
    Detecta TODAS as mesas abertas de uma sala de poker.

    Args:
        poker_room: titulo da janela principal (lobby).
        exclude_lobby: se True, remove a janela do lobby da lista.

    Returns:
        Lista de dicts, um por mesa detectada:
        {
            "hwnd": int,
            "title": str,
            "x": int, "y": int, "w": int, "h": int,
            "image": np.ndarray (BGR),
        }
        Mesas minimizadas (x <= -30000) sao filtradas.
    """
    all_windows = search_parent_window(poker_room)

    if exclude_lobby:
        all_windows = [t for t in all_windows if poker_room not in t[1]]

    results = []
    for hwnd, title in all_windows:
        x, y, w, h = get_window_rect(hwnd)

        # Filtrar minimizados (Windows coloca em -32000)
        if x <= -30000 or y <= -30000:
            continue

        pil_img = capture(hwnd)
        if pil_img is None:
            print(f"Falha ao capturar janela: {title}")
            continue

        bgr = cv2.cvtColor(np.array(pil_img, dtype=np.uint8), cv2.COLOR_RGB2BGR)
        results.append({
            "hwnd": hwnd,
            "title": title,
            "x": x, "y": y, "w": w, "h": h,
            "image": bgr,
        })

    return results


def detect_window(poker_room: str) -> np.ndarray:
    """
    Compatibilidade com codigo antigo: detecta apenas a PRIMEIRA mesa.

    NAO USE em novos fluxos multi-mesa -- prefira detect_windows().
    """
    tables = detect_windows(poker_room)
    if not tables:
        print("Nenhuma janela de poker encontrada!")
        return np.zeros((100, 100, 3), dtype=np.uint8)
    return tables[0]["image"]
