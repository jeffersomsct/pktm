import ctypes, win32con, win32gui
import win32clipboard as w32clip
from struct import pack, calcsize
from ctypes import windll, wintypes
from PIL import Image
import re
import os
import numpy as np
import mss
import mss.tools
import win32gui
import win32con
import pygetwindow as gw
import pyautogui
from PIL import Image
import time
# No topo do arquivo, adicione:
import win32ui
import win32process
import win32api

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

def copyBitmap(hbmp): # copy HBITMAP to clipboard
    w32clip.OpenClipboard(); w32clip.EmptyClipboard()
    w32clip.SetClipboardData(w32clip.CF_BITMAP,hbmp); w32clip.CloseClipboard()

def copySnapshot(hwnd): # copy Window HBITMAP to clipboard
    hbmp,w,h = getWindowBMAP(hwnd); copyBitmap(hbmp); gdi32.DeleteObject(hbmp)

def getSnapshot(hwnd): # get Window HBITMAP as Image
    hbmp,w,h,img = getWindowBMAP(hwnd,True); gdi32.DeleteObject(hbmp); return img


def capture_window_modern(hwnd):
    """Modern window capture using Windows.Graphics.Capture API (Windows 10+)"""
    try:
        from windows.graphics.capture import GraphicsCaptureSession
        from windows.graphics.capture.interop import create_for_window
        from windows.graphics.directx import DirectXPixelFormat
        from windows.graphics.imaging import BitmapAlphaMode, BitmapEncoder
        import asyncio

        item = create_for_window(hwnd)
        session = GraphicsCaptureSession()
        session.start_capture(item)

        frame = session.try_get_next_frame()
        if frame:
            with frame.create_bitmap():
                temp_file = "temp_capture.png"
                frame.save_to_file(temp_file)
                img = Image.open(temp_file)
                os.remove(temp_file)
                return img

    except Exception as e:
        print(f"Error in modern capture: {e}")
        return None
    finally:
        if 'session' in locals():
            session.close()

def capture_window_d3d(hwnd):
    """DirectX-based window capture using d3dshot"""
    try:
        # Initialize D3D capture
        d = d3dshot.create(capture_output="pil")
        
        # Get window position
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        
        # Capture the specific region
        screenshot = d.screenshot(region=(left, top, right, bottom))
        
        return screenshot
        
    except Exception as e:
        print(f"Error in D3D capture: {e}")
        return None

def capture_window_mss(hwnd):
    """Capture specific window content using MSS"""
    try:
        # Ensure window is not minimized
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        
        # Bring window to front
        win32gui.SetForegroundWindow(hwnd)
        
        # Get window position and size
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        with mss.mss() as sct:
            # Get window DC and window area
            window_dc = win32gui.GetWindowDC(hwnd)
            dc_obj = win32gui.GetObject(window_dc)
            
            # Define the region for the specific window
            monitor = {
                "top": top,
                "left": left,
                "width": width,
                "height": height,
                "mon": 1  # Primary monitor
            }

            # Capture the window
            screenshot = sct.grab(monitor)
            
            # Convert to PIL Image
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            return img

    except Exception as e:
        print(f"Error in MSS capture: {e}")
        return None

def capture_window_gui(hwnd):
    """Capture specific window content using PyGetWindow and PyAutoGUI"""
    try:
        # Get window by handle
        window = gw.Window(hwnd)
        
        # Ensure window is active and not minimized
        if window.isMinimized:
            window.restore()
        window.activate()
        
        # Small delay to ensure window is fully activated
        time.sleep(0.2)
        
        # Get window position and size
        left, top = window.left, window.top
        width, height = window.width, window.height
        
        # Capture the window
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        return screenshot

    except Exception as e:
        print(f"Error in GUI capture: {e}")
        return None

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
                
                # Usar numpy para processamento mais rápido
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

def detect_window_technology(hwnd):
    """Detect the rendering technology used by the window"""
    try:
        class_name = win32gui.GetClassName(hwnd)
        window_text = win32gui.GetWindowText(hwnd)
        
        # Get window styles
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        
        # Check for common DirectX/Game window classes
        if "DirectUIHWND" in class_name:
            return "DirectX (Modern UI)"
        elif "Chrome_RenderWidgetHostHWND" in class_name:
            return "Chromium/GPU Accelerated"
        elif class_name.startswith("SDL_"):
            return "SDL (OpenGL/DirectX)"
        elif "OpenGL" in class_name or "GLFWWindow" in class_name:
            return "OpenGL"
        elif "D3D" in class_name:
            return "DirectX"
        elif style & win32con.WS_CHILD and "OpenGL" in window_text:
            return "OpenGL"
        elif ex_style & win32con.WS_EX_LAYERED:
            return "Layered Window (Modern)"
        else:
            return "Standard GDI"
            
    except Exception as e:
        print(f"Error detecting technology: {e}")
        return "Unknown"

# Modify snapshot function to use technology detection
def snapshot(window):
    imgs = []
    for w in window:
        hwnd = w[0]
        
        tech = detect_window_technology(hwnd)
        print(f"Window technology: {tech}")
        
        if tech == "Standard GDI":
            img = capture_window_gdi(hwnd)
        else:
            img = capture_window_memory(hwnd)

        if img:
            sanitized_filename = re.sub(r'[\\/*?:"<>| ]', '_', w[1])
            file_path = os.path.join('imgs', sanitized_filename + ".png")
            img.save(file_path)
            print("Snapshot Saved!")
            imgs.append(img)
    return imgs


def capture_window_gdi(hwnd):
    """Optimized capture method for Standard GDI windows"""
    try:
        # Get window dimensions
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        # Get window DC and create compatible DC
        wdc = win32gui.GetWindowDC(hwnd)
        dcobj = win32ui.CreateDCFromHandle(wdc)
        cdc = dcobj.CreateCompatibleDC()

        # Create bitmap object
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(dcobj, width, height)
        cdc.SelectObject(bitmap)

        # Use PrintWindow with proper flags
        PW_CLIENTONLY = 0x1
        PW_RENDERFULLCONTENT = 0x2
        
        result = windll.user32.PrintWindow(
            hwnd, 
            cdc.GetSafeHdc(),
            PW_RENDERFULLCONTENT
        )

        if not result:  # If first attempt fails, try with client only
            result = windll.user32.PrintWindow(
                hwnd, 
                cdc.GetSafeHdc(),
                PW_CLIENTONLY
            )

        # Additional BitBlt for better capture
        if result:
            windll.user32.RedrawWindow(hwnd, None, None, 
                win32con.RDW_UPDATENOW | win32con.RDW_ALLCHILDREN)
            windll.gdi32.BitBlt(
                cdc.GetSafeHdc(),
                0, 0, width, height,
                dcobj.GetSafeHdc(),
                0, 0,
                win32con.SRCCOPY
            )

        # Convert to PIL Image
        bmpinfo = bitmap.GetInfo()
        bmpstr = bitmap.GetBitmapBits(True)
        img = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1
        )

        # Cleanup
        win32gui.DeleteObject(bitmap.GetHandle())
        cdc.DeleteDC()
        dcobj.DeleteDC()
        win32gui.ReleaseDC(hwnd, wdc)

        return img

    except Exception as e:
        print(f"Error in GDI capture: {e}")
        return None

# Modify snapshot function to use GDI capture for GDI windows
def snapshot(window):
    imgs = []
    for w in window:
        hwnd = w[0]
        
        tech = detect_window_technology(hwnd)
        print(f"Window technology: {tech}")
        
        if tech == "Standard GDI":
            img = capture_window_gdi(hwnd)
        else:
            img = capture_window_memory(hwnd)

        if img:
            sanitized_filename = re.sub(r'[\\/*?:"<>| ]', '_', w[1])
            file_path = os.path.join('imgs', sanitized_filename + ".png")
            img.save(file_path)
            print("Snapshot Saved!")
            imgs.append(img)
    return imgs


def detect_window_protection(hwnd):
    """Detect window protection mechanisms"""
    try:
        class_name = win32gui.GetClassName(hwnd)
        window_text = win32gui.GetWindowText(hwnd)
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        
        protections = []
        
        # Check for layered window (often used for protected content)
        if ex_style & win32con.WS_EX_LAYERED:
            protections.append("Layered Window")
            
        # Check for topmost window (common in protected apps)
        if ex_style & win32con.WS_EX_TOPMOST:
            protections.append("Topmost Window")
            
        # Check for DirectX/Hardware acceleration
        if "D3D" in class_name or "DirectX" in class_name:
            protections.append("DirectX Protected")
            
        # Check for specific window styles that might indicate protection
        if style & win32con.WS_CLIPCHILDREN:
            protections.append("Clip Children")
            
        # Check process privileges
        try:
            pid = win32process.GetWindowThreadProcessId(hwnd)[1]
            handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, pid)
            if handle:
                protections.append("Standard Process")
                win32api.CloseHandle(handle)
            else:
                protections.append("Protected Process")
        except:
            protections.append("Access Denied")
        
        return protections
        
    except Exception as e:
        print(f"Error detecting protection: {e}")
        return ["Unknown"]

# Modify snapshot function to use protection detection
def snapshot(window):
    imgs = []
    for w in window:
        hwnd = w[0]
        
        tech = detect_window_technology(hwnd)
        protections = detect_window_protection(hwnd)
        print(f"Window technology: {tech}")
        print(f"Window protections: {protections}")
        
        # Choose capture method based on protections
        if "Protected Process" in protections or "DirectX Protected" in protections:
            # Try alternative capture method for protected windows
            img = capture_window_memory(hwnd)
        elif "Layered Window" in protections:
            # Use specific method for layered windows
            img = capture_window_gdi(hwnd)
        else:
            # Use standard capture method
            img = getSnapshot(hwnd)

        if img:
            sanitized_filename = re.sub(r'[\\/*?:"<>| ]', '_', w[1])
            file_path = os.path.join('imgs', sanitized_filename + ".png")
            img.save(file_path)
            print("Snapshot Saved!")
            imgs.append(img)
    return imgs


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
            
            # Detectar tecnologia e proteções apenas se necessário (comentado para melhorar desempenho)
            # tech = detect_window_technology(hwnd)
            # protections = detect_window_protection(hwnd)
            # print(f"Window technology: {tech}")
            # print(f"Window protections: {protections}")
            
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
