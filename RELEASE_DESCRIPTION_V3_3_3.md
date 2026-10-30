# GFG Extreme 3.3.3

Reliability fixes for plugin shutdown and system-profile restoration.

- Unloading waits for active tick and health workers before restoring settings. Cancellation no longer leaves a worker applying policy after shutdown; queued control requests are rejected once shutdown starts.
- Service tick and stop are serialized. A stopped service cannot resume policy writes, repeated successful stops are harmless, and a failed restorer does not prevent other restorers from being attempted.
- Remove verifies restored system-profile values. On failure it keeps the remaining original values, preserves dependency order, and reports the error so Remove can be retried. The current restorer replaces older installed scripts before use.
- Remove invalidates the panel's engine/host caches. An engine still mounted until reboot is reported from the actual mount state.

The pinned GSF engine remains `f13e66cee6b0934d9b90a273e78253502ba64042` (1.4.4), as in the 3.3.2 source tree. This patch does not change shaders, frame scheduling or image-quality settings.

Validation: backend tests, sandbox scenarios, frontend build and Chromium smoke test; deterministic lifecycle stress (200 unloads with repeated cancellation), service serialization, restore failure/retry and installer upgrade tests. No new Steam Deck hardware measurements are claimed.

# GFG Extreme 3.3.3 — исправления стабильности

- Выгрузка дожидается завершения tick и проверки состояния перед восстановлением настроек. Отмена задачи больше не оставляет рабочий поток, способный повторно применить политику после остановки.
- Остановленный Service не возобновляет запись настроек. Ошибка одного восстановления не мешает попыткам восстановить остальные параметры.
- Remove проверяет результат восстановления системного профиля. При ошибке исходные значения сохраняются для повторной попытки, соблюдается порядок зависимых настроек, а панель сообщает о проблеме. Старый установленный скрипт восстановления заменяется исправленным.
- После Remove панель заново проверяет состояние движка. До перезагрузки движок может оставаться смонтированным.

Движок GSF 1.4.4, шейдеры и настройки качества сохранены из исходников 3.3.2. При ошибке восстановления повторите Remove либо перезагрузите устройство. Новые аппаратные замеры на Steam Deck не проводились.
