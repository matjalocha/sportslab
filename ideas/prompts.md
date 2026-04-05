# Prompts Log

Ten plik zawiera wszystkie prompty użytkownika, które doprowadziły do powstania struktury `ideas/`. Zachowywany dosłownie w celu reprodukowalności i historycznej ścieżki decyzji.

---

## Prompt #1 — Inicjalizacja planu produktyzacji

**Data:** 2026-04-05
**Autor:** Mateusz
**Kontekst:** Rozmowa zaczęła się od weryfikacji kuponu `bets_r32_tabpfn_v4.md` przez "wirtualnego doktora matematyki". Po analizie formy zespołów przeszliśmy do planowania produktyzacji całego projektu.

**Treść:**

> Stwórz zespół 6 osób, które planują przerobić ten projekt na dochodowy biznes. W skład zespołu wchodzi lead ze sporym doświadczeniem w tworzeniu firm i pisaniu kodu, doktor matematyki ze specjalizacją w sportach, senior machine learning engineer z 20 letnim doświadczeniem, senior data engineer z 20 letnim doświadczeniem, senior software engineer z 20 letnim doświadczeniem, senior graphic designer z 20 letnim doświadczeniem w tworzeniu UI/UX designów i aplikacji. Niech stworzą szczegółowy plan ustrukturyzowania raportu z podziałem na różne fazy i z rozpisanymi taskami. Konieczne jest na początku uporządkowanie kodu, następnie dodanie nowych funkcjonalności, następnie rozszerzenie na więcej lig, później więcej dyscyplin w zależności od dostępności danych do nich, w kolejnym kroku zaplanowanie aplikacji do zarządzania wszystkim i sprzedaży produktu. Potrzebujemy planu rozwoju projektu od początkowych zadań i działania lokalnie na komputerze, przez automatyzacje wszystkich procesów i finalnie stworzenie produktu i wymyślenie co dokładnie możemy sprzedawać. Trzeba zaplanować strukture repozytoriów i jak to ma działać jeśli chodzi o maszynkę. Konieczne jest założenie kont u LVBet, superbet, fortuna, betclic jeszcze, przygotowanie porządne scrappingu, backtestingu, modelowania, raportowania, optymalizacji strategii i stawek oraz wymyślenie autorskiego podejścia do tematu. Ponadto wszystko musi być dobrze skoordynowane, więc być może skorzystamy z lineara i do tego github, wszystko musi być skrupulatnie zaplanowane i rozpisane. Wyniki niech zostaną zapisane w folderze ideas z podziałem na fazy rozwoju i informacją kiedy przechodzimy do kolejnej fazy, koniecznie rozpisanie tasków z podziałem na konkretne zadania i czy kogoś potrzebujemy jeszcze do zespołu. Ponadto zapisz ten propmpt w ideas/prompts.md

---

## Prompt #2 — Doprecyzowanie liczby sportów

**Data:** 2026-04-05
**Treść:**

> Natomiast zrób co najmniej w planie 2-3 sporty

---

## Decyzje użytkownika w trakcie planowania (via AskUserQuestion)

1. **Monetyzacja (Faza 6)**: B2B API / value feed + research co jeszcze można sprzedać — analizy dla klubów piłkarskich, dashboardy dla trenerów innych dyscyplin, dostęp do danych w jednym miejscu z możliwością własnych analiz. **Nie tylko bety.**
2. **Sporty (Faza 4)**: Tenis (primary) + poszerzone do 3 sportów → tenis + koszykówka + hokej.
3. **Horyzont**: Definition-of-Done jako główne kryterium, plus orientacyjne widełki tygodniowe per faza.

---

## Zasady dotyczące promptów

- Każdy kolejny duży prompt związany z `ideas/` powinien zostać dopisany do tego pliku (sekcja `## Prompt #N`).
- Zachowujemy dokładną treść, datę i kontekst.
- Decyzje wynikające z pytań doprecyzowujących logujemy pod nagłówkiem `## Decyzje użytkownika`.
