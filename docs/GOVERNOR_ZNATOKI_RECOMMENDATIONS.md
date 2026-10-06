# GFG Extreme — рекомендации «знатоков»
## Что? Где? Когда? Edition — 2026-10-07

Эта ветка собирает в одном месте все рекомендации по развитию GFG Extreme как интеллектуального оркестратора вокруг MAKO Render v4.

## Базовый принцип продукта

MAKO Render v4 остаётся сильным исполнительным движком.

GFG Extreme должен выигрывать не заменой рендера, а качеством управления:

> снижать энергозатраты настолько, насколько возможно, компенсируя это множителем генерации, render scale и другими runtime-манипуляциями, пока игровой опыт остаётся выше заданного порога качества.

Высокий множитель, включая x3, не считается автоматически плохим режимом. Если Render v4 сохраняет хороший игровой опыт, а x3 позволяет существенно снизить TDP, Governor должен уметь предпочитать x3.

Цель:

`минимальный рациональный TDP при приемлемом качестве игрового опыта`

а не:

`минимальный множитель любой ценой`

и не:

`минимальный стабильный TDP любой ценой`.

---

# 1. Перейти от перебора настроек к модели игры

Текущий Governor уже умеет:
- собирать свежие evidence windows;
- пробовать operating points;
- откатываться;
- искать TDP;
- контролировать ownership;
- использовать runtime overlay;
- работать без разрушения Saved-профиля.

Следующий шаг:

`Observe -> Classify -> Predict -> Choose -> Verify -> Remember`

Вместо:

`try multiplier -> try scale -> lower TDP -> guard`

## Что должен знать Governor о текущей игре

- текущий bottleneck;
- real/base FPS;
- output FPS;
- frametime;
- jitter;
- thermal state;
- фактическое энергопотребление;
- запас производительности;
- стабильность сцены;
- насколько scale помогает именно этой игре;
- какие operating points уже проверялись;
- какая точка была лучшей в прошлых сессиях.

---

# 2. Мониторные крючки

## 2.1 Frametime — главный новый сигнал

Нужно собирать отдельно:
- real/base frametime;
- output/present frametime;
- median;
- p95;
- p99;
- MAD или стандартное отклонение;
- slow-frame streak;
- stutter bursts;
- frame pacing regularity;
- 1% low;
- 0.1% low, если метрика достаточно устойчива.

Причина:
две точки могут показывать одинаковые 90 FPS, но одна ощущается плавно, а другая выдаёт периодические 70–120 ms spikes.

Governor не должен судить качество только по среднему FPS.

---

# 3. Температура и thermal headroom

Нужно собирать:
- APU temperature;
- GPU temperature, если доступна отдельно;
- temperature slope;
- thermal throttling;
- запас до зоны throttling.

Важно отличать:

`75 C стабильно`

от

`75 C и растёт на 1.5 C/мин`.

Governor должен понимать heat soak.

Нельзя обучать GameModel на уже перегретом Deck как будто это нормальная производительность игры.

---

# 4. GPU-наблюдение

Собирать:
- GPU utilization / busy;
- GPU frequency;
- GPU frequency ceiling;
- throttling;
- residency/pressure, если доступно без тяжёлого polling.

Это позволит понять, когда render scale имеет смысл.

### GPU-bound
Scale может дать реальный выигрыш.

### CPU-bound
Scale часто только ухудшит картинку без роста real FPS.

---

# 5. CPU-наблюдение

Не ограничиваться общим CPU %.

Собирать:
- per-core utilization summary;
- самый загруженный core;
- CPU frequency;
- sustained single-core saturation;
- scheduler pressure;
- load average как вторичную метрику.

Игра может быть CPU-bound при общем CPU usage 35–45%.

---

# 6. Реальное энергопотребление

Нужно различать:

`TDP cap`

и

`actual package/APU draw`.

Собирать:
- fastPPT;
- slowPPT;
- actual package/APU power;
- battery discharge watts.

Governor должен понимать:

> выставлено 10 W, реально игра использует 7.4 W.

Это важно для построения реальной efficiency curve.

---

# 7. Battery telemetry

На батарее собирать:
- discharge W;
- battery %;
- estimated runtime;
- charge/discharge status.

Это позволит оценивать не только абстрактные ватты, но и пользовательский выигрыш:

> этот operating point даёт +38 минут автономности при почти неизменном опыте.

---

# 8. Fan RPM

Если SteamOS предоставляет стабильный и дешёвый источник:
- fan RPM;
- скорость изменения RPM.

Это позволяет учитывать акустический комфорт.

Если две точки дают одинаковый опыт, но одна требует вентилятор 5200 RPM, а другая 3600 RPM, Governor должен это знать.

---

# 9. Presentation state

Собирать:
- реальный active refresh rate;
- Gamescope mode;
- external display state;
- VRR state/range;
- frame limiter state;
- resolution.

OLED не всегда означает 90 Hz.
Dock не означает автоматически 60 Hz.

Target FPS должен исходить из текущей presentation environment.

90/60 оставить как fallback.

---

# 10. Renderer v4 telemetry

Сохранять и расширять текущие сигналы:
- generated-delivery misses;
- pressure/recovery;
- bypass/recovery;
- scheduler intervals;
- runtime-state-applied;
- fixed/adaptive plan;
- measured real FPS;
- measured output FPS;
- actual multiplier;
- actual scale;
- transition events.

Render v4 остаётся главным источником истины о собственном pipeline.

---

# 11. Input-latency proxy

Настоящий click-to-photon измерять трудно.

Но можно построить proxy из:
- real FPS;
- base frametime;
- multiplier;
- frame queue;
- present timing;
- scheduler intervals;
- pipeline depth, если доступен.

Это особенно важно для x3.

x3 может быть отличной точкой по мощности, но Governor должен понимать, когда real cadence уже слишком низкий для конкретного профиля качества.

---

# 12. Scene-change detector

Governor должен отличать:
- смену сцены;
- тяжёлую кат-сцену;
- выход на открытую локацию;
- меню;
- загрузочный экран;
- краткий spike.

Признаки:
- резкое устойчивое изменение GPU load;
- изменение frametime distribution;
- изменение actual power;
- изменение CPU/GPU bottleneck.

После scene change:
1. не паниковать;
2. открыть короткое observation window;
3. только потом менять point.

---

# 13. Transient / shader-stutter detector

Один 150 ms spike не должен запускать:
- рост TDP;
- смену multiplier;
- scale transition.

Нужна классификация:

`isolated transient`

против

`sustained degradation`.

Признаки:
- единичные outliers;
- burst duration;
- восстановление median/p95;
- pressure events;
- повторяемость.

---

# 14. Memory pressure

Не главный сигнал, но полезен для диагностики:
- RAM usage;
- swap usage;
- memory pressure;
- shared GPU memory pressure, если доступно.

Это позволит Governor не пытаться лечить TDP то, что вызвано memory pressure.

---

# 15. Разные частоты мониторинга

Не опрашивать всё одинаково часто.

## High-frequency
10–30 Hz:
- frametime;
- renderer misses/pressure;
- cadence.

## Medium-frequency
2–5 Hz:
- GPU utilization;
- GPU clock;
- CPU frequency/load;
- actual package power.

## Low-frequency
0.5–1 Hz:
- temperature;
- battery;
- fan;
- memory;
- display sanity check.

Политика должна работать на агрегированных окнах, а не на сыром шуме.

---

# 16. State Estimator

Перед policy engine нужен отдельный слой:

```
SystemState:
  bottleneck
  thermal_state
  pacing_state
  power_state
  scene_state
  telemetry_confidence
  headroom
```

## Bottleneck
- GPU_BOUND
- CPU_BOUND
- POWER_BOUND
- THERMAL
- MIXED
- UNKNOWN

## Pacing
- CLEAN
- UNSTABLE
- STUTTER_BURST

## Thermal
- COOL
- WARM
- HOT
- THROTTLING

Policy не должен напрямую реагировать на каждый raw sensor.

---

# 17. Experience floor

Governor нужен нижний порог качества.

Не одна цель FPS, а набор ограничений:
- min real FPS;
- max p95 frametime;
- max jitter;
- max stutter rate;
- max scale penalty;
- thermal margin;
- acceptable renderer pressure;
- latency proxy ceiling.

Точка ниже floor считается плохой, даже если она экономит ещё 1 W.

---

# 18. Режимы пользователя

## Quality
Приоритет:
- высокий real FPS;
- low latency;
- высокий scale;
- shallow FG;
- power вторичен.

## Balanced
Приоритет:
- лучший общий utility;
- x2.5/x3 разрешены;
- 90% scale разрешён при хорошем trade-off.

## Battery
Приоритет:
- минимальный рациональный power;
- x3 нормален;
- scale reduction разрешён;
- но experience floor нарушать нельзя.

---

# 19. Utility-модель

Вместо fixed ladder использовать сравнение кандидатов.

Пример:

```
utility =
    power_saving
  - real_fps_penalty
  - frametime_penalty
  - latency_penalty
  - generation_penalty
  - scaling_penalty
  - instability_penalty
  - thermal_penalty
  - acoustic_penalty
  - transition_penalty
```

Это не ML.
Это прозрачная policy function.

---

# 20. Не минимальный TDP, а точка насыщения экономии

Пример:

- 12 W -> 10 W: почти бесплатная экономия;
- 10 W -> 8 W: x2 -> x3, опыт всё ещё хороший;
- 8 W -> 7 W: 90% scale, ещё разумно;
- 7 W -> 6 W: нужен 80% scale + frametime хуже.

Governor должен остановиться на 7–8 W.

То есть искать:

**minimum rational TDP**

а не математический минимум.

---

# 21. Efficiency metrics

Добавить внутренние показатели:

- output frames / joule;
- real frames / watt;
- experience score / watt;
- battery minutes gained per quality-cost unit.

Лучший кандидат должен быть не просто самым дешёвым, а самым эффективным.

---

# 22. Pareto frontier

Для каждой игры Governor может строить поверхность:

`TDP x multiplier x scale -> experience`

И отбрасывать доминируемые точки.

Пример:
если x2.5 / 10 W даёт почти тот же опыт, что x2 / 14 W, x2 / 14 W неинтересен для Balanced/Battery.

Остаётся Pareto frontier:
- больше качества;
- меньше power.

Режим пользователя выбирает точку на этой границе.

---

# 23. Scale effectiveness

Scale нужно проверять эмпирически.

После trial:
- изменился ли real FPS;
- улучшился ли p95;
- снизился ли GPU busy;
- снизился ли required TDP;
- насколько ухудшилось качество.

Если scale 90% ничего не даёт конкретной CPU-bound игре, запомнить это и больше не повторять бессмысленные trials.

---

# 24. Persistent GameModel

Сохранять по игре:

```
game_id
display_mode
renderer_version
config_fingerprint

native_capacity
likely_bottleneck
stable_points
failed_points
scale_effectiveness
tdp_curve
frametime_profile
thermal_profile
last_good_point
confidence
sample_count
last_updated
```

Следующий запуск:
1. начать рядом с last-known-good;
2. быстро проверить;
3. исследовать только если среда изменилась.

---

# 25. Context fingerprint

GameModel должен учитывать не только game ID.

Контекст:
- handheld/dock;
- refresh rate;
- resolution;
- charging/battery;
- Governor mode;
- Render v4 version;
- significant runtime config.

Иначе нельзя переносить знания OLED 90 Hz на внешний 4K-дисплей.

---

# 26. Confidence score

Каждое решение должно иметь confidence.

Пример:

`x3 @ 8 W / confidence 92%`

Основания:
- 4 min stable evidence;
- clean frametime;
- no pressure;
- thermals stable;
- point seen in previous sessions.

При низкой confidence Governor:
- продолжает наблюдать;
- меньше экспериментирует;
- не делает сильных persistent conclusions.

---

# 27. Причины решений

Каждый переход должен объясняться.

Пример:

> x2.5 -> x3  
> expected saving: 2.1 W  
> real FPS floor: passed  
> p95 frametime: passed  
> thermal margin: improved  
> scale unchanged  
> confidence: 87%

Это полезно и для пользователя, и для отладки.

---

# 28. Effort rating

Easy / Medium / Hard / Nightmare можно оставить.

Но всегда показывать причину:
- Hard: x3 required
- Hard: 80% scale
- Hard: high TDP
- Hard: low thermal margin
- Nightmare: experience floor failed
- Nightmare: target cannot be sustained

Так rating перестаёт быть декоративной наклейкой.

---

# 29. Архитектурное разделение

`governor_service.py` не должен становиться всем проектом.

Рекомендуемые компоненты:

### TelemetryHub
Собирает renderer/hardware telemetry.

### StateEstimator
Классифицирует bottleneck, pacing, thermal state.

### GameModelStore
Хранит learned state.

### GovernorPolicy
Строит и ранжирует кандидатов.

### RuntimeActuator
Multiplier/scale/runtime overlay.

### PowerController
TDP ownership/search.

### SessionEvaluator
Оценивает результат trial.

### GovernorSupervisor
Lifecycle + RPC.

---

# 30. Real-world replay

Создать:
`tests/replay/real/`

Собирать реальные traces:
- GPU-bound;
- CPU-bound;
- thermal soak;
- shader stutter;
- scene transition;
- x3 low-power stable;
- x3 latency-sensitive;
- dock;
- external high-refresh;
- sleep/resume;
- QAM conflict;
- PowerTools conflict;
- Flatpak;
- telemetry loss;
- renderer crash.

Правило:

**каждый реальный баг превращается в replay regression fixture.**

---

# 31. CI и надёжность

Старые инженерные замечания остаются актуальны:

- CI должен запускаться независимо от существования release tag;
- frontend должен rebuild/test перед packaging;
- privileged TDP helper должен иметь timeout;
- frontend RPC errors не должны молча проглатываться;
- устаревшие docs/status strings нужно удалить;
- release validation должен быть обязательным PR check.

---

# 32. Приоритет следующей разработки

## Phase 1 — Eyes
Добавить наблюдаемость:
1. frametime;
2. GPU;
3. CPU;
4. thermal;
5. actual power;
6. battery;
7. refresh state;
8. confidence.

## Phase 2 — Brain
Добавить:
1. StateEstimator;
2. experience floor;
3. bottleneck classification;
4. scene/transient detector.

## Phase 3 — Intelligence
Добавить:
1. utility ranking;
2. GameModel;
3. Pareto frontier;
4. warm start;
5. scale effectiveness learning;
6. saturation-point search.

## Phase 4 — Validation
1. Deck traces;
2. replay import;
3. weight calibration;
4. adversarial x3 tests.

---

# 33. Ключевой принцип для будущих агентов

Не превращать Governor в автоматическую панель управления.

Перед добавлением любого нового правила задавать вопрос:

> Какой новый факт о состоянии игры Governor сможет понять благодаря этому изменению?

Если ответ:

> он просто попробует ещё один multiplier

это не интеллект.

Если ответ:

> он поймёт, что игра GPU-bound, scale 90% экономит 1.8 W без ухудшения pacing, а x3 остаётся выше real-FPS floor

это правильное направление.

---

# Итог

MAKO Render v4 даёт GFG Extreme сильный исполнительный слой.

Главная задача теперь — построить вокруг него систему, которая:
- видит;
- понимает;
- прогнозирует;
- сравнивает;
- проверяет;
- запоминает.

То есть использовать multiplier, scale и TDP не как три ползунка, а как набор инструментов для управления одной целью:

**максимум хорошего игрового опыта на каждый потраченный ватт.**
