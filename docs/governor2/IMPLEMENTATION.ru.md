# Практические исправления после повторной проверки аудита

Ветка `codex/controller-review-examples`, база audit 373a648 (GFG main3448a9b + отчёты). Изменены настоящие controllers, не только описания. Релизы не создавались. Это reference integration для review/cherry-pick, не заявленная аппаратная готовность.

## Изменения

- Governor thermal state обрабатывается **до** hold/no-cap. После устойчивого охлаждения85°C− и10s возвращает разрешённый потолок по1W/10s; Quality/measurement восстанавливают мощность в пределах этого потолка. Unknown temperature не расслабляет защиту. Порог/скорость — инженерный консервативный пример, требуется hardware acceptance.
- restore failure сохраняет pending и исходный контекст; новая игра не может claim перезаписать оригинальные значения до завершения восстановления. Отдельный fault-injection test.
- Service передаёт активность CPU/GPU probe в Governor, который не меняет TDP обычным optimizer в этом окне; завершение требует нового окна. Thermal emergency имеет приоритет. Это interlock, не полный persistent Governor2 lease.
- Missing/nonfinite pace запрещает healthy verdict; sparse gap перезапускает окно, требуется минимум8samples. Для3.0 это переходное условие, не полноценная доказательная time-weighted coverage.
- Fast guard восстанавливает TDP после3 свежих по времени severe samples, без ожидания10s окна; код использует существующую `_decide` для failure memory. Physical pacing guard требует ещё изменения engine telemetry.
- Pilot требует текущих real/confirmed данных и новых engine time_ns; gap очищает стабильность. Legacy unit fixtures без time_ns используют injected clock; production status имеет time_ns. Полный timeout/lease для потери измерения описан в Governor2.
- Autopilot thermal hysteresis предотвращает oscillation при84.9↔85.1°C, выход после60s ниже80°C. Изменение objective само по себе не доказывает холодное устройство.
- Policy epoch включает HDR/post, иначе workload изменился, а окна остались прежними.
- SessionStats сохраняет valid0FPS; saved_w/saved_wh не выводятся из недоиспользованного power cap. Отдельно cap_reduction_w, observed_apu_wh и draw_coverage_s. Пользовательский интерфейс не должен выдавать эти величины за causal savings.

## Перепроверка и уточнения предыдущих советов

1. «Просто заморозить TDP» недостаточно. После interlock и sample coverage общий sandbox показал24s до снижения cap в тяжёлой сцене вместо≤20s. Тест **не ослаблялся**; добавлен separate severe guard. После него общий sandbox проходит.
2. Полезность интерлока не означает, что прежние CPU A/B всегда давали ложный успех: они могут обнаружить drift и abort. Дефект — отсутствие общей гарантии и потери/повторы экспериментов. Новый тест проверяет настоящий Service с injected active probe.
3. Quality4W после cooling — ошибка соблюдения policy, не автоматически потерянный FPS: в fixture лёгкая сцена держит cap и на4W. Thermal recovery требует отдельного состояния, не условия «FPS упал».
4. Среднее29.7 при cap30 — не математическая ошибка threshold, а недостаточность такого threshold для latency/pacing SLA. Не меняем0.97 на1.00 без реальных данных.
5. Отсутствие причинной baseline нельзя исправить переименованием15−8W в savings: возвращаем unknown. Реальный energy gain должен прийти из matched comparison.

## Проверки

- На старом коде16 новых test methods:16 failure records (включая отдельные subtests), baseline positive controls присутствуют. Лог `controller-red.log`.
- После добавления отдельного severe guard: **106 backend tests PASS**, включая17 новых regression methods и существующий sandbox suite; 6.812s в этой среде.
- Отдельный Governor2 transaction reference: **6 tests PASS** (ownership/ack/timeout/stale/readback/override).
- Логи приложены в `docs/audit-v3.0.0/evidence/`.

Команды:
```
python3 -m unittest discover -s tests -p 'test_*.py'
python3 -m unittest discover -s docs/governor2 -p 'test_*.py'
```

Новые timestamp/lease/thermal numeric параметры не подтверждены Deck. Не исправлены в этом commit: engine physical counter protocol, exact ZIP tools, runtime transaction install, полный persistent governor journal/unload concurrency, GPU-controller coverage, model TTL и causal A/B baseline. Это явно оставленные задачи, не утверждение о завершённом Governor2.
