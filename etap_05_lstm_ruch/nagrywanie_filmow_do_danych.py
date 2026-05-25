import cv2
import mediapipe as mp
import os
import time
import platform

# --- KONFIGURACJA ---
NAZWA_FOLDERU = "../nagrania_gestow_ruchow"
PLIK_PLANU = "plan_nagrania_tylko_ruchome.txt"
ROZDZIELCZOSC = (1280, 720)
FPS = 30.0
KLATKI_NA_NAGRANIE = 60
PRZERWA_MIEDZY_NAGRANIAMI = 2.0  # Czas (w sekundach) pomiędzy kolejnymi nagraniami

# --- 1. ROZPOZNAWANIE SYSTEMU ---
system_operacyjny = platform.system()

if system_operacyjny == "Windows":
    backend = cv2.CAP_DSHOW
    cap = cv2.VideoCapture(0, backend)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0)
    cap.set(cv2.CAP_PROP_EXPOSURE, -6)
elif system_operacyjny == "Linux":
    backend = cv2.CAP_V4L2
    cap = cv2.VideoCapture(0, backend)
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
    cap.set(cv2.CAP_PROP_EXPOSURE, 100)
elif system_operacyjny == "Darwin": # macOS
    backend = cv2.CAP_AVFOUNDATION
else:
    backend = cv2.CAP_ANY # Domyślny fallback

# --- 2. INICJALIZACJA KAMERY ---
# Jeśli na Linuxie masz problem z indeksem, zmień 1 na 0 lub 2.

# --- 3. SZTUCZKA SPRZĘTOWA Z MJPEG ---
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

# --- 4. WYMUSZENIE ROZDZIELCZOŚCI ---
cap.set(cv2.CAP_PROP_FRAME_WIDTH, ROZDZIELCZOSC[0])
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, ROZDZIELCZOSC[1])
cap.set(cv2.CAP_PROP_FPS, FPS)

if not os.path.exists(NAZWA_FOLDERU):
    os.makedirs(NAZWA_FOLDERU)

# 1. Tworzenie domyślnego pliku z planem (jeśli go nie ma)
if not os.path.exists(PLIK_PLANU):
    with open(PLIK_PLANU, "w") as f:
        f.write("H 10\nJ 10\nZ 15")
    print(f"Utworzono domyślny plik '{PLIK_PLANU}'. Możesz go wyedytować, by zmienić plan!")

# 2. Wczytywanie planu
harmonogram = []
with open(PLIK_PLANU, "r") as f:
    for linia in f:
        czesci = linia.strip().split()
        if len(czesci) == 2:
            litera = czesci[0].upper()
            ilosc = int(czesci[1])
            if ilosc > 0:
                harmonogram.append([litera, ilosc])

if not harmonogram:
    print("Twój harmonogram jest pusty lub źle sformatowany! Zamykam program.")
    exit()

# Zmienne śledzące aktualny postęp w harmonogramie
aktualny_krok = 0
aktualna_litera = harmonogram[aktualny_krok][0]
ilosc_docelowa = harmonogram[aktualny_krok][1]
nagran_zrobionych = 0

# Upewnienie się, że folder dla pierwszej litery z planu istnieje
os.makedirs(os.path.join(NAZWA_FOLDERU, aktualna_litera), exist_ok=True)

# --- INICJALIZACJA MEDIAPIPE ---
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)

# --- ZMIENNE STANOWE ---
is_recording = False       
tryb_seryjny = False       
out = None
klatek_nagranych = 0
czas_ostatniej_klatki = time.time()
czas_zakonczenia_ostatniego = 0.0 
frame_interval = 1.0 / FPS

print("\n--- KAMERA URUCHOMIONA ---")
print("Wciśnij [SPACJĘ], aby rozpocząć automatyczną serię nagrań dla aktualnej litery.")
print("Po wykonaniu wszystkich powtórzeń dla litery, program poczeka na kolejną [SPACJĘ].")
print("Wciśnij [Q] w oknie kamery, aby wyjść z programu.")
print(f"System: {system_operacyjny} | Celowane Ustawienia: {ROZDZIELCZOSC[0]}x{ROZDZIELCZOSC[1]} @ {FPS} FPS\n")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Błąd odczytu z kamery.")
        break

    # Efekt lustra dla naturalnego podglądu
    frame = cv2.flip(frame, 1)
    display_frame = frame.copy()

    # Rysowanie punktów MediaPipe (tylko na podglądzie, nie na nagraniu!)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    wyniki = hands.process(frame_rgb)
    if wyniki.multi_hand_landmarks:
        for hand_landmarks in wyniki.multi_hand_landmarks:
            mp_drawing.draw_landmarks(display_frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    # --- OBSŁUGA KLAWISZY W OPENCV ---
    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):
        print("Przerwano przez użytkownika (Klawisz Q).")
        break

    # --- START TRYBU SERYJNEGO (SPACJA) ---
    if key == ord(' ') and not tryb_seryjny:
        tryb_seryjny = True
        czas_zakonczenia_ostatniego = 0.0  
        print(f"\n[START] Rozpoczęto serię nagrań dla litery: {aktualna_litera}")

    # --- LOGIKA AUTOMATYCZNEGO NAGRYWANIA ---
    if tryb_seryjny and not is_recording:
        pozostaly_czas = PRZERWA_MIEDZY_NAGRANIAMI - (time.time() - czas_zakonczenia_ostatniego)
        
        if pozostaly_czas <= 0:
            is_recording = True
            klatek_nagranych = 0
            czas_ostatniej_klatki = time.time()
            sciezka_klasy = os.path.join(NAZWA_FOLDERU, aktualna_litera)
            nazwa_pliku = f"{aktualna_litera}_{int(time.time() * 1000)}.mp4"
            sciezka_zapisu = os.path.join(sciezka_klasy, nazwa_pliku)
            
            # Zawsze bierzemy faktyczną rozdzielczość klatki, żeby pliki się nie psuły!
            wysokosc, szerokosc, _ = frame.shape
            rzeczywista_rozdzielczosc = (szerokosc, wysokosc)

            fourcc = cv2.VideoWriter_fourcc(*'MP4V')
            out = cv2.VideoWriter(sciezka_zapisu, fourcc, FPS, rzeczywista_rozdzielczosc)
            print(f"Nagrywanie: {nazwa_pliku}...")
        else:
            # Odliczanie na ekranie
            cv2.putText(display_frame, f"Kolejne ujęcie za: {pozostaly_czas:.1f}s", (20, 80), 
                        cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 165, 0), 2)

    # --- ZAPIS KLATEK ---
    if is_recording:
        out.write(frame)
        klatek_nagranych += 1
        
        procent = int((klatek_nagranych / KLATKI_NA_NAGRANIE) * 100)
        
        cv2.circle(display_frame, (50, 50), 20, (0, 0, 255), -1)
        cv2.putText(display_frame, f"NAGRYWANIE: {klatek_nagranych}/{KLATKI_NA_NAGRANIE}", (80, 60), cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 0, 255), 2)
        
        bar_width = 200
        bar_height = 20
        filled = int((procent / 100) * bar_width)
        cv2.rectangle(display_frame, (50, 90), (50 + bar_width, 90 + bar_height), (100, 100, 100), -1)
        cv2.rectangle(display_frame, (50, 90), (50 + filled, 90 + bar_height), (0, 255, 0), -1)
        cv2.putText(display_frame, f"{procent}%", (260, 105), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 1)
        
        # Koniec pojedynczego nagrania
        if klatek_nagranych >= KLATKI_NA_NAGRANIE:
            is_recording = False
            out.release()
            nagran_zrobionych += 1
            czas_zakonczenia_ostatniego = time.time()
            print(f"[ZAPISANO] Wykonano {nagran_zrobionych}/{ilosc_docelowa} nagrań dla '{aktualna_litera}'.")

            if nagran_zrobionych >= ilosc_docelowa:
                tryb_seryjny = False 
                aktualny_krok += 1
                
                if aktualny_krok >= len(harmonogram):
                    print("\n=== GRATULACJE! CAŁY PLAN WYKONANY! ===")
                    cv2.rectangle(display_frame, (10, 10), (600, 150), (0, 255, 0), -1)
                    cv2.putText(display_frame, "PLAN ZAKONCZONY!", (30, 100), cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 0, 0), 3)
                    cv2.imshow('Zbieranie Danych', display_frame)
                    cv2.waitKey(3000)
                    break
                else:
                    aktualna_litera = harmonogram[aktualny_krok][0]
                    ilosc_docelowa = harmonogram[aktualny_krok][1]
                    nagran_zrobionych = 0
                    
                    os.makedirs(os.path.join(NAZWA_FOLDERU, aktualna_litera), exist_ok=True)
                    
                    print(f"\n---> ZMIANA ZADANIA! Przygotuj się do: {aktualna_litera}")
                    print("---> Wciśnij [SPACJĘ], gdy będziesz gotów na serię.")

    # --- INTERFEJS TEKSTOWY ---
    tekst_info = f"Zadanie: {aktualna_litera} | Zrobiono: {nagran_zrobionych}/{ilosc_docelowa}"
    cv2.rectangle(display_frame, (10, 10), (450, 50), (0, 0, 0), -1)
    cv2.putText(display_frame, tekst_info, (20, 35), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 255), 2)

    if not tryb_seryjny and aktualny_krok < len(harmonogram):
        cv2.putText(display_frame, "[SPACJA] = START SERII", (20, 80), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 0), 2)

    cv2.imshow('Zbieranie Danych', display_frame)

    czas_obecny = time.time()
    czas_przeszlosci = czas_obecny - czas_ostatniej_klatki
    if czas_przeszlosci < frame_interval:
        time.sleep(frame_interval - czas_przeszlosci)
    czas_ostatniej_klatki = time.time()

if is_recording and out is not None:
    out.release()
cap.release()
cv2.destroyAllWindows()
hands.close()