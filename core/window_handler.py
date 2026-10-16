import win32gui
import win32process
from images.capture import snapshot
import numpy as np
import cv2

def detect_window(poker_room: str) ->  np.ndarray:
    """
    Captura as janelas filhas através da janela principal ("Lobby")
    e retorna uma imagem no formato BGR para processamento com OpenCV
    """
    
    visible_widow = search_parent_window(poker_room)
    # remover a janela principal ("Lobby")
    visible_widow = [t for t in visible_widow if poker_room not in t[1]]
    
    # Verificar se há janelas para capturar
    if not visible_widow:
        print("Nenhuma janela de poker encontrada!")
        return np.zeros((100, 100, 3), dtype=np.uint8)  # Retorna imagem vazia se não houver janelas
    
    # Capturar as janelas
    snap_shot = snapshot(visible_widow)
    
    # Verificar se a captura retornou alguma imagem
    if not snap_shot or len(snap_shot) == 0:
        print("Falha ao capturar janelas!")
        return np.zeros((100, 100, 3), dtype=np.uint8)  # Retorna imagem vazia em caso de falha
    
    # Usar a primeira imagem capturada (poderia ser modificado para combinar múltiplas imagens se necessário)
    img = snap_shot[0]
    
    # Converter diretamente para BGR para evitar conversões desnecessárias
    # Isso é mais rápido que converter para RGB e depois para BGR
    image_bgr = cv2.cvtColor(np.array(img, dtype=np.uint8), cv2.COLOR_RGB2BGR)
    
    return image_bgr


def get_all_child_windows(parent_handle):
    """
    Obtém todas as janelas filhas do handle da janela principal.
    """
    child_windows = []
    
    def callback(hwnd, _):
        title = win32gui.GetWindowText(hwnd).strip()  # Obtém título
        if title:  # Ignorar janelas sem título
            child_windows.append((hwnd, title))
        return True  # Continuar a enumeração
    
    win32gui.EnumChildWindows(parent_handle, callback, None)
    return child_windows

def get_existing_windows(process_id):
    existing_windows = []
    
    def callback(hwnd, _):
        # Verifica se a janela está visível e pertence ao processo correto
        if win32gui.IsWindowVisible(hwnd):
            _, wnd_process_id = win32process.GetWindowThreadProcessId(hwnd)
            if wnd_process_id == process_id:
                title = win32gui.GetWindowText(hwnd).strip()  # Remove espaços
                if title:  # Ignorar janelas sem título
                    existing_windows.append((hwnd, title))
        return True  # Continuar a enumeração
    
    win32gui.EnumWindows(callback, None)
    return existing_windows


def search_parent_window(window_title):
    # Nome da janela principal do jogo
    # window_title = "SwC Poker"
    main_handle = win32gui.FindWindow(None, window_title)

    if main_handle:
        print(f"Handle principal encontrado: {main_handle}")
        
        # Obter todas as janelas filhas, sem restrição de visibilidade
        child_windows = get_all_child_windows(main_handle)
        # print("Todas as janelas filhas associadas:")
        # for hwnd, title in child_windows:
            # print(f"Handle: {hwnd}, Título: {title}")
        
        # Obtém o ID do processo do jogo
        _, process_id = win32process.GetWindowThreadProcessId(main_handle)
        # print(f"Process ID do jogo: {process_id}")
        
        # Lista todas as janelas associadas ao processo, sem restrição
        all_windows = get_existing_windows(process_id)
        print("\nTodas as janelas associadas ao processo:")
        #for hwnd, title in all_windows:
            #print(f"Handle: {hwnd}, Título: {title}")
        return all_windows
        
        

    else:
        print("Janela principal do jogo não encontrada.")
