# GFG Extreme 3.3.2

The game keeps its own frames under generation, and the picture responds sooner.
**Update engine** and reboot after installing.

## New engine: GSF Kedavra 1.4.4
- **No more falling to half the frame rate.** The base cap lets one game frame through per slot
  (×2 at 90 Hz: a slot of two refreshes). A frame that finished just after the start of its slot
  used to wait for the whole next slot, so a game rendering 44 fps under ×2 was shown at about 30
  and a 37 fps game at about 22. Such a frame now goes through on the very next refresh, and the
  game keeps the rate it can render.
- **Lower latency.** A game frame no longer waits for its slot, so it reaches the screen sooner,
  also in games that hold the cap.
- **Same cadence when the cap holds.** A game that is on time still gets exactly one frame per
  slot, on the 2-2-2-3 pattern of fractional caps.

Scheduler simulator, 90 Hz, 3 seeds × 120 s, 3.3.1 → 3.3.2:

| Case | Game frames per second | Median latency |
|---|---|---|
| ×2, game renders 46.5 fps | 33.7 → 38.3 | 49.5 → 38.5 ms |
| ×2, game renders 43 fps | 27.3 → 34.1 | 66.1 → 43.8 ms |
| ×2, game renders 37 fps | 22.9 → 30.1 | 64.1 → 52.0 ms |
| ×2.25 (base 40), game renders 38 fps | 20.6 → 30.2 | 81.9 → 49.1 ms |
| ×2, game holds 45 | 42.9 → 44.3 | 48.8 → 38.7 ms |

---

# GFG Extreme 3.3.2

Игра сохраняет свои кадры при генерации, а картинка откликается быстрее.
После установки нажмите **Update engine** и перезагрузите устройство.

## Новый движок: GSF Kedavra 1.4.4
- **Больше никакого провала к половине частоты.** Лимит базы пропускает один кадр игры на слот
  (×2 при 90 Гц: слот в два обновления экрана). Кадр, готовый чуть позже начала слота, раньше ждал
  весь следующий слот, поэтому игра на 44 FPS при ×2 показывалась примерно на 30, а игра на 37 FPS
  примерно на 22. Теперь такой кадр проходит на ближайшем обновлении, и игра сохраняет ту частоту,
  которую может рисовать.
- **Меньше задержка.** Кадр игры больше не ждёт свой слот и раньше попадает на экран, в том числе
  в играх, которые держат лимит.
- **Тот же ритм, когда лимит держится.** Игра, которая успевает, по-прежнему получает ровно один кадр
  на слот, а при дробном лимите в его ритме 2-2-2-3.

Симулятор планировщика, 90 Гц, 3 прогона × 120 с, 3.3.1 → 3.3.2:

| Случай | Кадров игры в секунду | Медианная задержка |
|---|---|---|
| ×2, игра рисует 46,5 FPS | 33,7 → 38,3 | 49,5 → 38,5 мс |
| ×2, игра рисует 43 FPS | 27,3 → 34,1 | 66,1 → 43,8 мс |
| ×2, игра рисует 37 FPS | 22,9 → 30,1 | 64,1 → 52,0 мс |
| ×2,25 (база 40), игра рисует 38 FPS | 20,6 → 30,2 | 81,9 → 49,1 мс |
| ×2, игра держит 45 | 42,9 → 44,3 | 48,8 → 38,7 мс |
