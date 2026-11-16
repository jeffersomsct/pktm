import ctypes, win32con, win32gui
from struct import pack, calcsize
from ctypes import windll
from PIL import Image
import re
import os
import win32ui

user32,gdi32 = windll.user32,windll.gdi32
PW_RENDERFULLCONTENT = 2

def getWindowBMAP(hwnd,returnImage=False):
    # get Window size and crop pos/size
    L,T,R,B = win32gui.GetWindowRect(hwnd); W,H = R-L,B-T
    x,y,w,h = (8,8,W-16,H-16) if user32.IsZoomed(hwnd) else (7,0,W-14,H-7)

    # create dc's and bmp's
    dc = user32.GetWindowDC(hwnd)
    dc1,dc2 = gdi32.CreateCompatibleDC(dc),gdi32.CreateCompatibleDC(dc)
    bmp1,bmp2 = gdi32.CreateCompatibleBitmap(dc,W,H),gdi32.CreateCompatibleBitmap(dc,w,h)

    # render dc1 and dc2 (bmp1 and bmp2) (uncropped and cropped)
    obj1,obj2 = gdi32.SelectObject(dc1,bmp1),gdi32.SelectObject(dc2,bmp2) # select bmp's into dc's
    user32.PrintWindow(hwnd,dc1,PW_RENDERFULLCONTENT) # render window to dc1
    gdi32.BitBlt(dc2,0,0,w,h,dc1,x,y,win32con.SRCCOPY) # copy dc1 (x,y,w,h) to dc2 (0,0,w,h)
    gdi32.SelectObject(dc1,obj1); gdi32.SelectObject(dc2,obj2) # restore dc's default obj's

    if returnImage: # create Image from bmp2
        data = ctypes.create_string_buffer((w*4)*h)
        bmi = ctypes.c_buffer(pack("IiiHHIIiiII",calcsize("IiiHHIIiiII"),w,-h,1,32,0,0,0,0,0,0))
        gdi32.GetDIBits(dc2,bmp2,0,h,ctypes.byref(data),ctypes.byref(bmi),win32con.DIB_RGB_COLORS)
        img = Image.frombuffer('RGB',(w,h),data,'raw','BGRX')

    # clean up
    gdi32.DeleteObject(bmp1) # delete bmp1 (uncropped)
    gdi32.DeleteDC(dc1); gdi32.DeleteDC(dc2) # delete created dc's
    user32.ReleaseDC(hwnd,dc) # release retrieved dc

    return (bmp2,w,h,img) if returnImage else (bmp2,w,h)

def getSnapshot(hwnd): # get Window HBITMAP as Image
    hbmp,w,h,img = getWindowBMAP(hwnd,True); gdi32.DeleteObject(hbmp); return img


def capture_window_memory(hwnd):
    """Captura janela diretamente da memória sem trazê-la para frente
    
    Versão otimizada para melhor desempenho e confiabilidade
    """
    try:
        # Verificar se a janela existe
        if not win32gui.IsWindow(hwnd):
            return None
            
        # Obter dimensões da janela
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        
        # Verificar dimensões válidas
        if width <= 0 or height <= 0:
            return None
            
        # Criar DC compatível e bitmap
        hwnd_dc = None
        mfc_dc = None
        save_dc = None
        save_bitmap = None
        
        try:
            # Obter DC da janela
            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            save_bitmap = win32ui.CreateBitmap()
            save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(save_bitmap)
            
            # Tentar capturar com PW_RENDERFULLCONTENT | PW_CLIENTONLY (3)
            result = windll.user32.PrintWindow(
                hwnd,
                save_dc.GetSafeHdc(),
                3
            )
            
            # Se falhar, tentar com PW_RENDERFULLCONTENT (2)
            if not result:
                result = windll.user32.PrintWindow(
                    hwnd,
                    save_dc.GetSafeHdc(),
                    2
                )
            
            # Se ainda falhar, tentar com flags padrão (0)
            if not result:
                result = windll.user32.PrintWindow(
                    hwnd,
                    save_dc.GetSafeHdc(),
                    0
                )
            
            # Converter para PIL Image apenas se a captura foi bem-sucedida
            if result:
                bmpinfo = save_bitmap.GetInfo()
                bmpstr = save_bitmap.GetBitmapBits(True)
                
                img = Image.frombuffer(
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1
                )
                return img
            return None
            
        finally:
            # Limpeza garantida mesmo em caso de exceção
            if save_bitmap:
                win32gui.DeleteObject(save_bitmap.GetHandle())
            if save_dc:
                save_dc.DeleteDC()
            if mfc_dc:
                mfc_dc.DeleteDC()
            if hwnd_dc:
                win32gui.ReleaseDC(hwnd, hwnd_dc)
    
    except Exception as e:
        print(f"Erro na captura de memória: {e}")
        return None

def capture_protected_window(hwnd):
    """Specialized capture method for windows with access restrictions"""
    try:
        # Get window dimensions and ensure they are valid
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        
        if width <= 0 or height <= 0:
            return None

        # Get window DC
        window_dc = win32gui.GetWindowDC(hwnd)
        window_mfc = win32ui.CreateDCFromHandle(window_dc)
        
        try:
            # Create memory DC and bitmap
            mem_dc = window_mfc.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(window_mfc, width, height)
            mem_dc.SelectObject(bitmap)
            
            # Try to capture using PrintWindow with different flags
            result = windll.user32.PrintWindow(
                hwnd, 
                mem_dc.GetSafeHdc(),
                2  # PW_RENDERFULLCONTENT
            )
            
            if not result:
                result = windll.user32.PrintWindow(
                    hwnd, 
                    mem_dc.GetSafeHdc(),
                    0
                )
            
            if result:
                # Convert to PIL Image
                bmpinfo = bitmap.GetInfo()
                bmpstr = bitmap.GetBitmapBits(True)
                img = Image.frombuffer(
                    'RGB',
                    (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                    bmpstr, 'raw', 'BGRX', 0, 1
                )
                return img
                
        finally:
            # Cleanup
            if 'bitmap' in locals():
                win32gui.DeleteObject(bitmap.GetHandle())
            if 'mem_dc' in locals():
                mem_dc.DeleteDC()
            window_mfc.DeleteDC()
            win32gui.ReleaseDC(hwnd, window_dc)

    except Exception as e:
        print(f"Error in protected capture: {e}")
    return None

# Função snapshot otimizada para melhor desempenho
def snapshot(window):
    """Captura as janelas especificadas e retorna uma lista de imagens PIL
    
    Args:
        window: Lista de tuplas (hwnd, title) representando as janelas a serem capturadas
        
    Returns:
        Lista de objetos PIL.Image das janelas capturadas
    """
    imgs = []
    
    # Verificar se há janelas para capturar
    if not window:
        print("Nenhuma janela para capturar")
        return imgs
    
    for w in window:
        try:
            hwnd = w[0]
            title = w[1]
            
            # Usar método mais rápido e confiável para captura
            img = capture_window_memory(hwnd)
            
            # Tentar método alternativo se o primeiro falhar
            if img is None:
                img = getSnapshot(hwnd)
            
            # Tentar método protegido como último recurso
            if img is None:
                img = capture_protected_window(hwnd)
            
            if img:
                # Opcional: salvar imagem em disco (comentado para melhorar desempenho)
                sanitized_filename = re.sub(r'[\\/*?:"<>| ]', '_', title)
                file_path = os.path.join('imgs', sanitized_filename + ".png")
                img.save(file_path)
                print(f"Snapshot de '{title}' salvo!")
                
                imgs.append(img)
            else:
                print(f"Falha ao capturar janela: {title}")
        except Exception as e:
            print(f"Erro ao capturar janela {w[1]}: {e}")
    
    return imgs
