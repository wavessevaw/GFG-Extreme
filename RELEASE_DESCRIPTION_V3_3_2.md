# GFG Extreme 3.3.2

More real game frames under generation and a faster response.
**Update engine** and reboot after installing.

## New engine: GSF Kedavra 1.4.4
- **Every frame the game renders is shown.** The base cap now passes a game frame on the very
  next refresh as soon as it is ready, one frame per slot of the cap (×2 at 90 Hz: a slot of two
  refreshes). A game running just under the cap keeps the full frame rate it renders.
- **Faster response.** Game frames reach the screen sooner, in every game, including games that
  hold the cap.
- **Steady rhythm.** A game that holds the cap gets exactly one frame per slot, on the 2-2-2-3
  pattern of fractional caps.

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

Больше настоящих кадров игры при генерации и более быстрый отклик.
После установки нажмите **Update engine** и перезагрузите устройство.

## Новый движок: GSF Kedavra 1.4.4
- **Каждый кадр игры на экране.** Лимит базы теперь пропускает кадр игры на ближайшем обновлении
  экрана, как только он готов, по одному кадру на слот лимита (×2 при 90 Гц: слот в два обновления).
  Игра чуть ниже лимита сохраняет всю частоту кадров, которую рисует.
- **Быстрее отклик.** Кадры игры раньше попадают на экран во всех играх, в том числе в тех, что
  держат лимит.
- **Ровный ритм.** Игра, которая держит лимит, получает ровно один кадр на слот, а при дробном
  лимите в его ритме 2-2-2-3.

Симулятор планировщика, 90 Гц, 3 прогона × 120 с, 3.3.1 → 3.3.2:

| Случай | Кадров игры в секунду | Медианная задержка |
|---|---|---|
| ×2, игра рисует 46,5 FPS | 33,7 → 38,3 | 49,5 → 38,5 мс |
| ×2, игра рисует 43 FPS | 27,3 → 34,1 | 66,1 → 43,8 мс |
| ×2, игра рисует 37 FPS | 22,9 → 30,1 | 64,1 → 52,0 мс |
| ×2,25 (база 40), игра рисует 38 FPS | 20,6 → 30,2 | 81,9 → 49,1 мс |
| ×2, игра держит 45 | 42,9 → 44,3 | 48,8 → 38,7 мс |
