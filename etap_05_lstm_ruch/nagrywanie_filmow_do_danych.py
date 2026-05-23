import cv2
import mediapipe as mp
import os
import time

# --- KONFIGURACJA ---
NAZWA_FOLDERU = "../nagrania_gestow"
PLIK_PLANU = "plan_nagrania.txt"
ROZDZIELCZOSC = (1280, 720)
FPS = 30.0
KLATKI_NA_NAGRANIE = 30

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

# --- INICJALIZACJA KAMERY I MEDIAPIPE ---
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, ROZDZIELCZOSC[0])
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, ROZDZIELCZOSC[1])

is_recording = False
out = None
klatek_nagranych = 0
czas_ostatniej_klatki = time.time()
frame_interval = 1.0 / FPS

print("\n--- KAMERA URUCHOMIONA ---")
print("Wciśnij [SPACJĘ] w oknie kamery, aby rozpocząć nagranie (30 klatek).")
print("Wciśnij [Q] w oknie kamery, aby wyjść z programu.")
print(f"Ustawienia: {ROZDZIELCZOSC[0]}x{ROZDZIELCZOSC[1]} @ {FPS} FPS\n")

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

    # Zakończenie programu
    if key == ord('q'):
        print("Przerwano przez użytkownika (Klawisz Q).")
        break

    # --- LOGIKA NAGRYWANIA (SPACJA) ---
    # Kod ASCII dla spacji to 32, można też użyć ord(' ')
    if key == ord(' ') and not is_recording:
        is_recording = True
        klatek_nagranych = 0
        czas_ostatniej_klatki = time.time()
        sciezka_klasy = os.path.join(NAZWA_FOLDERU, aktualna_litera)
        nazwa_pliku = f"{aktualna_litera}_{int(time.time() * 1000)}.mp4"
        sciezka_zapisu = os.path.join(sciezka_klasy, nazwa_pliku)
        
        fourcc = cv2.VideoWriter_fourcc(*'MP4V')
        out = cv2.VideoWriter(sciezka_zapisu, fourcc, FPS, ROZDZIELCZOSC)
        print(f"Nagrywanie: {nazwa_pliku}...")

    # Zapis klatek, jeśli nagrywanie jest aktywne
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
        
        if klatek_nagranych >= KLATKI_NA_NAGRANIE:
            is_recording = False
            out.release()
            nagran_zrobionych += 1
            print(f"[ZAPISANO] Wykonano {nagran_zrobionych}/{ilosc_docelowa} nagrań dla '{aktualna_litera}'.")

            if nagran_zrobionych >= ilosc_docelowa:
                aktualny_krok += 1
                
                if aktualny_krok >= len(harmonogram):
                    print("\n=== GRATULACJE! CAŁY PLAN WYKONANY! ===")
                    cv2.rectangle(display_frame, (10, 10), (800, 150), (0, 255, 0), -1)
                    cv2.putText(display_frame, "PLAN ZAKONCZONY!", (30, 100), cv2.FONT_HERSHEY_DUPLEX, 2, (0, 0, 0), 3)
                    cv2.imshow('Zbieranie Danych (Spacja = Nagrywaj)', display_frame)
                    cv2.waitKey(3000)
                    break
                else:
                    aktualna_litera = harmonogram[aktualny_krok][0]
                    ilosc_docelowa = harmonogram[aktualny_krok][1]
                    nagran_zrobionych = 0
                    
                    # Utworzenie nowego folderu dla kolejnej litery
                    os.makedirs(os.path.join(NAZWA_FOLDERU, aktualna_litera), exist_ok=True)
                    
                    print(f"\n---> ZMIANA ZADANIA! Teraz nagrywaj: {aktualna_litera} <---")

    tekst_info = f"Zadanie: {aktualna_litera} | Zrobiono: {nagran_zrobionych}/{ilosc_docelowa}"
    cv2.rectangle(display_frame, (10, 10), (400, 50), (0, 0, 0), -1)
    cv2.putText(display_frame, tekst_info, (20, 35), cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 255, 255), 2)

    cv2.imshow('Zbieranie Danych (Spacja = Nagrywaj)', display_frame)

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