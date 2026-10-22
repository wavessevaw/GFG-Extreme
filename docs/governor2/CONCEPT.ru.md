# Governor 2.0: единый координатор GFG

Решение: иерархический supervisory controller с ограничениями и транзакционным управлением. Не нейросеть, не ещё один параллельный автопилот. Он выбирает рабочую точку всего конвейера и разрешает только один эксперимент с изменением нагрузки одновременно. Авторитет пользователя, системная безопасность и восстановление выше оптимизации.

## Что он координирует

- Real source FPS cap и FG ratio/режим; отдельно requested и effective из движка.
- TDP fast/slow PPT, CPU max, GPU policy с ownership/readback/restore.
- FG quality tier и filters только в разрешённом пользователем диапазоне. Не отключать HDR или менять пользовательский художественный preset скрыто ради цифры FPS.
- Порядок warmup, измерения, применения, подтверждения, rollback и повторной оценки.
- Частоту диагностики, сохранение telemetry и per-game prior. Debug capture не должен незаметно менять workload во время измерения.
- Он **не** выполняет GPU synchronization, не решает отдельный vblank и не заменяет thermal firmware. Pair scheduling/completion и KMS остаются в Gamescope; CPU supervisory tick не может гарантировать дедлайн11ms.

## Общий контракт данных

Snapshot включает engine_session_id, policy_revision, source/display epoch, monotonic sequence/time, coverage, active display/refresh/resolution/transfer, requested/effective policy, actual source FPS, confirmed displayed counts, repeat/missing slots, queue depth, completion delay, GPU stage timings, p95/p99, temperature/age, power readback и ownership. Validity отдельно для каждого домена.

Отсутствующее поле = unknown, не0. engine policy echo не равно90 отображённым кадрам. Старый status без completion/KMS identity поддерживается в observe-only режиме для новых энергопроб; ручной режим/обычный passthrough остаётся работоспособным. Не включать строгий новый gate в текущем3.0 status без версии протокола: это отключит экономию для всех, а не исправит измерение.

Snapshot/context ключ: game + output mode + resolution + transfer + engine build/schema + effective FG/filter cost tier + CPU/GPU constraints. Battery charge/temp не включать в high-cardinality cache key; это динамические ограничения.

## Порядок полномочий

1. Manual override / ownership loss: прекратить записи в затронутый ресурс, не «восстанавливать» поверх пользователя.
2. Safety и незавершённое восстановление: thermal/device lost/suspend отменяют optimization lease. Восстановление проходит с readback и сохранённым journal.
3. Fast performance guard: rollback последнего собственного ухудшения при source/output deficit. Если причина не в нашем изменении, не повышать TDP бесконечно.
4. Requested product objective: fixed30→90, Quality, Balanced, Battery. Ограничения latency/quality действуют во всех режимах.
5. Медленная оптимизация feasible point по энергии. One change at a time.

## Состояния и команды

`OBSERVE → BASELINE → APPLY_PENDING → SETTLE → VERIFY → COMMIT/HOLD`.
При failure: `ROLLBACK_PENDING → READBACK → QUARANTINE → OBSERVE`.
При manual change: `USER_OWNED`. При нет данных: `UNKNOWN`, новые пробы запрещены. Pending restore не исчезает при смене игры/перезапуске plugin.

Каждая команда содержит transaction_id, owner, axis, old/target value, context epoch, deadline, reason. Перед hardware write — persist intent (atomic replace+fsync файла/каталога по требованиям устройства). После readback — persist applied. Recovery на startup сверяет журнал с actual readback. Не считать timeout доказательством, что запись не произошла: late manager completion требует повторной reconciliation, а не новой baseline.

«Один эксперимент» относится ко всему влияющему на workload состоянию, а не только одной sysfs записи. Проба CPU на фиксированном TDP включает A/B/A и возврат исходных clock constraints. Другие loops могут наблюдать, но не оптимизировать. Safety вправе прервать эксперимент, его samples маркируются invalid.

## Политика выбора точки

Сначала отфильтровать точки по ограничениям: сохраняется пользовательская FPS цель, output deadlines, latency budget, качество, thermal и power ceiling. Затем минимизировать измеренную энергию среди допустимых точек; для Quality предпочтение более высоким real FPS в заданном power ceiling. Стартовый prior проверяется с запасом, не применяется как доказанный optimum.

Базовые координаты: (real cap, FG tier, TDP, CPU cap, GPU mode). Постоянно перебирать декартово произведение нельзя. Порядок coordinate descent:

1. Доказать source+FG+display feasibility при пользовательских power limits.
2. Зафиксировать cap, найти TDP bracket last-good / first-bad.
3. На устойчивой точке провести CPU **или** GPU trial с неизменным TDP и matched workload.
4. Если новый clock режим принят, повторно проверить TDP в новом контексте.
5. Изменение FG tier допускается только после доказанного FG bottleneck, по прежним quality/latency gates.

Каждый probe имеет energy/time/write budget и minimum expected benefit. Не считать -1W cap выигрышем, если measured draw не изменился. Изучать scene-change отдельно от power failure; floor TTL действует внутри сессии. After-failure backoff переносит remaining duration, не начинается заново при каждом reload.

## Пример решения вместо абстрактного «управлять эффективнее»

30→90, источник держит30; KMS даёт45, GPU analysis растёт, игра CPU не ограничена. Решение: **не** снижать CPU clock только потому, что real30 удерживается; **не** принимать pace=1 от scheduler. Отменить текущий power trial, вернуть last-good settings, классифицировать FG/display ограничение. Запросить более дешёвый FG tier только если quality bounds разрешены, иначе сообщить limited. Пробовать больше TDP лишь при измеренном power headroom и thermal admissibility.

Другой случай: source30/output90/latency стабильны, TDP15→14, draw8→8W. Нет доказанной экономии; не записывать «сэкономлен1W». Прекратить частые probes до следующего контекстного изменения или cooldown. При8→7.6W требуется matched baseline и confidence, а не один sensor sample.

## Применяемый сейчас код и границы

В ветке `codex/controller-review-examples` есть изменения настоящих3.0 controllers: thermal recovery вне measurement branch, сохранение restore-pending, freshness Pilot, probe interlock, минимум sample coverage, fast severe guard, workload epoch для HDR/filters, честная SessionStats. Это переходные исправления, **не весь Governor2.0**. Bool probe_active не реализует persistent lease/timeout; минимальный sample count не заменяет полноценную time-weighted validity; старый pace всё ещё требует исправления в движке.

`transaction_reference.py` — исполняемый пример ядра транзакции с fake actuator tests. Он показывает ownership, pending apply, readback и rollback при expiry; не подключён к железу, не даёт оценок энергосбережения. Production adapter обязан добавить persistent journal, bounds, fast/slow PPT atomicity, manager late-write reconciliation и actual display telemetry.

## Развёртывание без подмены проверки

- Shadow: новый coordinator только предлагает действия; сравнить с active decisions и журналировать disagreements.
- Actuator fault simulation: partial write, delayed ack, user override, restart, stale epoch, duplicate completion, timeout. Не ослаблять invariants ради synthetic score.
- Limited actuation: один axis (TDP), остальные observe; затем CPU/GPU leases.
- Stage-by-stage hardware gates на фиксированных builds: воспроизводимая нагрузка, A/B/A, physical pacing/latency и фактические joules.
- Никаких публичных release/tag в этой исследовательской ветке. Основной агент может переносить отдельные проверенные commits после review.
