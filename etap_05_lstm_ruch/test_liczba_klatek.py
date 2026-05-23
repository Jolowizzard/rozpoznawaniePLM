import cv2

# Podaj ścieżkę do jednego z wygenerowanych plików .mp4
sciezka_wideo = "../nagrania_gestow/H/TUTAJ_NAZWA_PLIKU.mp4" 

cap = cv2.VideoCapture(sciezka_wideo)

if not cap.isOpened():
    print("Nie można otworzyć pliku wideo. Sprawdź ścieżkę!")
else:
    # Pobranie liczby klatek z metadanych
    liczba_klatek = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Liczba klatek (z metadanych): {liczba_klatek}")

    # Dla 100% pewności - fizyczne przeliczenie klatek jedna po drugiej
    licznik_fizyczny = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        licznik_fizyczny += 1
        
    print(f"Fizycznie przeczytane klatki: {licznik_fizyczny}")

cap.release()