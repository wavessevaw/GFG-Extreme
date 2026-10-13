# Extreme: контракты реализации

Это проект интерфейсов, не описание уже доступных RPC.
[Архитектура](EXTREME_FOUNDATION.md) · [Задания](EXTREME_IMPLEMENTATION_HANDOFF.md)

## Данные

Каждый sample содержит monotonic timestamp, sequence, источник, identity запуска, единицы и признак свежести. Неизвестное значение — null, не ноль. NaN/Infinity и недопустимые диапазоны отвергаются.

SessionIdentity: app/profile, PID + start time, launch owner, модель устройства, backend/version, pipeline, исходное разрешение/Hz и унаследованные ограничения.

Capabilities отдельно описывает scale provisioning/live, CAS provisioning/live, pacer, CPU/GPU cap, fan bias, управление заданиями Steam, priority и scoped memory/swap. Для каждой возможности: supported, reason, requires_restart, способ подтверждения и отката.

ExtremePoint:
- revision и identity;
- requested/applied render percent, исходный reference, подтверждённые source/output extent;
- CAS backend и requested/applied strength;
- target real FPS и FG ceiling;
- CPU/GPU cap и общий предел APU;
- ручные ограничения пользователя.

Evidence: point revision, acknowledged revision, последовательность и окно свежих samples, settle phase, метрики, контекст baseline и причины invalidation. Повтор одного sample не увеличивает окно измерений.

## PowerArbiter

Единственный путь всех изменений мощности. Ceiling = min(унаследованные fast/slow PPT пользователя, аппаратные пределы и действующие более строгие ограничения питания/температуры). Универсального потолка 15 Вт нет. Нижняя граница не может заставить превысить верхнюю: пустой допустимый интервал прекращает регулирование.

Проверять потолок непосредственно перед каждой записью, включая Act boost и recovery; readback проверяет результат. Если actuator не позволяет подтвердить безопасную запись, отказаться от автоматического управления этим actuator.

Пример: пользователь 12 Вт, спокойная точка 10 Вт, Act просит 14 Вт → максимум 12 Вт.
Если внешний QAM сменил предел на 9 Вт, новое значение становится ограничением и владение конфликтующей записью освобождается. Откат возвращает только своё значение, а не ранее сохранённые 12 Вт поверх внешних 9.

## Транзакция рабочей точки

1. PREPARE: capabilities, свежесть, потолок и ownership; записать undo-журнал.
2. APPLY: отправить requested revision.
3. ACK: подтвердить applied revision и фактические значения всех обязательных частей.
4. EVALUATE: после settle принять ACCEPT / REJECT / INCONCLUSIVE.
5. ROLLBACK: восстановить принадлежащие GFG значения, получить подтверждение; иначе RESTORE_PENDING или external override.

Запрос не равен применению. Нет ACK — точка не используется для доказательства или обучения. Частично применённая точка либо завершается, либо откатывается по отдельным подтверждённым полям. Истечение lease, выход игры, выключение, смена режима и suspend прекращают эксперимент.

## Actuator adapter

Операции: probe, acquire, apply, readback, restore_if_owned, recover.
Журнал атомарно сохраняется ДО изменения и содержит scope, owner, PID/start time, прежнее и последнее ожидаемое значение, revision и способ undo.

Восстановление сравнивает текущее значение с последним ожидаемым; внешние изменения не перетираются. Если формат/API не поддерживает надёжное владение, capability ограничивается или отключается. Частичный отказ не отменяет восстановление остальных принадлежащих настроек.

Привилегированный helper принимает ограниченный список валидируемых действий; никакого произвольного shell, пути или PID из UI без проверки принадлежности.

## Измерения и память

TDP, CPU/GPU cap, масштаб, CAS, FG/Act, фокус, loading и значимый контекст имеют revision. Неожиданное изменение во время контролируемого опыта делает его inconclusive. Изменяемые самим опытом параметры записываются как treatment, а не случайный drift.

Memory schema versioned: context key, подтверждённая point, evidence summary, confidence, failure history, user override. Схема имеет лимиты размера, атомарную запись и диапазоны. Неподтверждённые точки не становятся successful warm start.

## Предлагаемая граница backend/UI

get_extreme_status возвращает кэшированный immutable snapshot.
set_extreme_enabled задаёт desired state; UI не пишет sysfs и не ждёт эксперимент.
set_extreme_manual_sharpness задаёт пользовательскую поправку.
reset_extreme_memory очищает только память выбранной игры.

Status содержит state/reason, capabilities, requested/applied point, потолок, timestamp/stale, trial progress и rollback status.

Gain содержит kind: measured / pending / unavailable; percent и uncertainty null до доказательства, metric: real_fps, baseline: Balanced, sample count и context. Output FPS хранится отдельно. CAS 40% означает значение настройки, не «40% улучшения качества».

Числовые лимиты времени, очередей и polling задаются одной конфигурацией и проверяются нагрузочными измерениями. Поток present не выполняет RPC, sysfs, дисковые операции или поиск настроек.
