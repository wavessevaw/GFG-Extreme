# GFG Extreme 1.0.11 — актуальные замечания «знатоков»

Дата ревью: 2026-10-07  
Состояние основного проекта на момент ревью: GFG Extreme 1.0.11

Этот документ дополняет:
- `docs/GOVERNOR_ZNATOKI_RECOMMENDATIONS.md`
- `docs/UI_AUDIT_2026-10-07.md`

Он фиксирует не абстрактную желаемую архитектуру, а конкретные выводы после реальных Steam Deck логов и серии 1.0.0–1.0.11.

---

## 1. Что уже движется в правильную сторону

После первых реальных Deck-логов Governor перестал быть только лестницей preset'ов и начал использовать реальные evidence:

- delivered ratio принимается как наблюдение и затем отдельно верифицируется;
- текущая generated-frame capacity Render v4 учитывается как динамический ceiling;
- failed operating points запоминаются per-game через Steam AppID;
- возраст failure сохраняется через reload, TTL больше не перезапускается;
- TDP ownership/restore стал существенно безопаснее;
- фактический APU draw отделён от выставленного TDP cap;
- Governor больше не обязан покупать дополнительные ватты, если APU их фактически не использует;
- thermal state начал участвовать в policy;
- thermal hysteresis убирает дёрганье вокруг порога;
- confirmation logic вынесена из `governor_service.py`;
- появились session statistics и пользовательская оценка savings;
- реальный лог превращается в regression-тесты.

Особенно важный эмпирический результат:

`30 real -> x3 -> ~90 output` при примерно `10–11 W` на Witcher 3 / Steam Deck OLED действительно работает.

Это подтверждает базовую доктрину проекта: высокий FG multiplier не является плохим сам по себе. Если experience floor сохраняется, x3 может быть лучшим энергетическим operating point.

---

# 2. Открытый долг: floor memory должна переживать rebuild controller

В 1.0.5 добавлена полезная `floor_failures`:

```python
floor_failures: Dict[int, tuple[float, float, int]]
```

Она предотвращает повторные TDP-down probes, которые уже несколько раз вызвали FPS dip.

Проблема: эта память живёт только внутри экземпляра `BudgetController`.

Она теряется при:
- Battery -> Balanced;
- Balanced -> Battery;
- пересоздании controller;
- reload plugin/Governor;
- других путях, где текущий BudgetController уничтожается.

Получается архитектурная асимметрия:

- failed operating point запоминается в GameModel;
- failed TDP floor забывается вместе с объектом controller.

Это снова позволяет повторять доказанно плохой эксперимент.

## Что делать

Floor memory должна быть частью per-game/context memory.

Рекомендуемая запись:

```text
point_key
failed_floor_w
failed_at / expires_at
repeat_count
context_fingerprint
```

Контекст минимум:
- Steam AppID;
- target refresh/output;
- mode;
- renderer version;
- handheld/external;
- resolution при наличии.

При новом controller:
1. загрузить ещё живые floor failures;
2. сохранить remaining backoff;
3. не переякоривать TTL к текущему времени;
4. уменьшать/сбрасывать failure только после свежего evidence, что уровень снова держится.

Нужны regression tests:
- floor failure -> mode switch -> тот же floor не пробуется заново;
- floor failure -> reload -> remaining backoff сохраняется;
- expiry -> floor снова доступен;
- новая лёгкая сцена + достаточное подтверждение -> память снимается.

---

# 3. Recent Sessions сейчас некорректно маркирует mixed-mode session

Session history полезна, но сейчас summary получает:

```python
mode = self._mode(profile)
```

в момент завершения сессии.

Если пользователь играл:

`Battery -> Balanced -> Quality`

вся 30-минутная сессия может отображаться как `Quality`.

Это делает сравнение режимов статистически ложным.

## Что делать

Предпочтительный вариант: mode segments.

```text
session
  segments:
    Battery: 14m
    Balanced: 9m
    Quality: 7m
```

Для каждого segment отдельно считать:
- avg real/output FPS;
- avg TDP;
- avg actual draw;
- max temperature;
- stutter share;
- saved W / energy;
- stable point distribution.

В UI:
- если один режим: показывать его;
- если несколько: `Mixed`;
- в Details раскрывать распределение времени.

Минимальный безопасный вариант, если сегментация пока не готова:

```text
mode = mixed
modes_used = [battery, balanced, quality]
```

Нельзя подписывать всю сессию последним выбранным режимом.

---

# 4. Не закреплять эвристику "2.5 W ниже cap = not power bound" как интеллект

В 1.0.11 появился полезный guard:

```text
actual draw < TDP cap - 2.5 W
=> не покупать дополнительные watts
```

Это намного лучше старого:

`FPS short -> raise TDP`.

Но это всё ещё эвристика одного сигнала.

Низкий draw может означать:
- CPU bottleneck;
- shader/streaming hitch;
- frame limiter;
- renderer pressure;
- scene transition;
- scheduler issue;
- transient stall;
- thermal limitation;
- просто шум измерения.

## Что делать дальше

Перенести решение в StateEstimator.

Пример:

```text
POWER_BOUND confidence high:
  draw near cap
  + GPU busy high
  + clocks constrained
  + sustained real-fps shortage

CPU_BOUND confidence high:
  draw below cap
  + one/few CPU cores saturated
  + GPU not saturated
  + scale reduction gives no benefit

TRANSIENT:
  isolated frametime burst
  + rapid recovery
  + no sustained pressure
```

Policy должна получать:

```text
state = CPU_BOUND
confidence = 0.84
```

а не самостоятельно интерпретировать каждый raw sensor.

До появления StateEstimator оставить 2.5 W guard можно, но:
- оформить его как conservative fallback;
- логировать evidence;
- не превращать этот threshold в долговременную GameModel-истину.

---

# 5. Thermal policy полезна, но thresholds ещё не откалиброваны

Thermal-aware Battery/Balanced и hysteresis правильны архитектурно.

Но текущие пороги всё ещё rules of thumb, а не hardware-calibrated model.

Нельзя считать:
- одну температуру;
- один slope;
- один 90-second hold

универсальными для OLED/LCD/dock/external и всех ambient conditions.

## Что делать

Сохранять:
- temperature;
- slope;
- fan RPM;
- actual draw;
- clocks;
- throttle events;
- время после load transition.

Строить thermal headroom:

```text
distance_to_throttle
+ heating_rate
+ sustained_duration
```

GameModel не должен обучаться на throttled state как на нормальной capability игры.

---

# 6. Floor backoff не должен маскировать реальное изменение сцены

1.0.11 правильно сделал repeated failures более "липкими": одно случайное low-draw reading больше не снимает тройной failure.

Но обратная опасность: 10-минутный backoff способен слишком долго не замечать реально облегчавшуюся сцену.

Правило должно зависеть не только от таймера.

## Более сильный release condition

Разрешать ранний повторный probe при сочетании:

- draw устойчиво ниже старого failure floor;
- GPU load/clock materially ниже;
- real frametime стабилен;
- сцена стабильна N секунд;
- нет recent transient/stall;
- confidence достаточно высокий.

То есть:

`scene changed materially -> old floor evidence decays faster`.

Это важнее простого "через 600 секунд можно снова".

---

# 7. Нужна единая иерархия памяти

Сейчас появляются несколько типов памяти:

- remembered held point;
- rejected operating point;
- per-game failed point;
- floor failure;
- thermal deferred state;
- session history;
- renderer capacity;
- power-search state.

Если продолжать добавлять каждую память отдельным словарём, Governor станет набором пересекающихся TTL.

## Рекомендуемая структура

```text
GameModel
  context
  stable_points
  failed_points
  power_floor_evidence
  scale_effectiveness
  thermal_profile
  bottleneck_profile
  efficiency_frontier
  confidence
  recent_sessions
```

У каждой learned записи:
- evidence_count;
- confidence;
- created_at;
- last_verified;
- expiry/decay;
- context fingerprint.

Нужно постепенно сводить разрозненные памяти в один GameModelStore, а не добавлять очередной локальный dict.

---

# 8. Context fingerprint ещё недостаточно зрелый

Steam AppID — правильный шаг, но одной игры недостаточно.

Одна и та же игра на:

- OLED 90 Hz;
- LCD 60 Hz;
- dock 60 Hz;
- external 120 Hz;
- 1280x800;
- 1920x1080;
- 4K;
- battery;
- charger

может иметь совершенно другую efficiency frontier.

## Минимальный fingerprint

```text
app_id
target_refresh
resolution
handheld/external
mode
renderer_version
major config fingerprint
```

Battery/charger можно либо включать в fingerprint, либо хранить как condition при evidence.

Нельзя переносить "30x3 @ 10 W works" на другой display context без свежей проверки.

---

# 9. 60 Hz policy всё ещё требует реального validation

60 Hz Balanced / integer-ratio старт выглядит разумно.

Но это пока не такая же эмпирика, как OLED 90 Hz Witcher trace.

До real LCD/docked trace считать это:
- стартовой эвристикой;
- не calibrated operating policy.

Нужен отдельный реальный тест:
- LCD 60 Hz или dock 60 Hz;
- Battery/Balanced/Quality;
- startup;
- heavy scene;
- mode switch;
- warm start;
- suspend/resume.

---

# 10. Версия 1.0.x называется stable раньше, чем validation matrix действительно заполнена

Код заметно взрослеет, но "stable" пока опирается на ограниченное количество железа/игр.

Реальные логи особенно ценны, однако несколько сессий Witcher 3 на OLED не являются полной validation matrix.

## До широкого stable-confidence нужны хотя бы классы игр

- GPU-bound AAA;
- CPU-bound;
- shader-stutter-heavy;
- лёгкая/indie;
- Vulkan;
- DX11/DX12 через Proton;
- 60 Hz;
- 90 Hz;
- dock/external;
- long thermal soak;
- suspend/resume;
- game restart with warm memory;
- PowerTools/QAM conflict;
- telemetry loss/recovery.

Это не требует откатывать версию назад.

Но README/release wording должен честно различать:
- automated coverage;
- Deck-tested paths;
- broadly hardware-validated behavior.

---

# 11. Release cadence слишком высокая для meaningful hardware validation

За несколько часов прошли 1.0.5 -> 1.0.11.

CI зелёный полезен, но CI не заменяет реальную Deck session.

Риск:
- каждый новый fix проверяется synthetic tests;
- следующий release появляется раньше, чем предыдущий получил полноценный field trace;
- несколько изменений смешиваются;
- становится сложнее понять, какое изменение реально улучшило/сломало поведение.

## Рекомендация

Разделить:

### Development builds
быстрые итерации, сколько угодно.

### Validation candidates
одна сборка фиксируется для real-world trace.

### Stable release
после прохождения минимального набора реальных сценариев.

Не обязательно тормозить разработку.
Нужно перестать считать номер релиза эквивалентом validation evidence.

---

# 12. Real-world replay должен стать обязательной частью каждого field fix

Проект уже фактически идёт в эту сторону.

Следующий шаг — формализовать:

`tests/replay/real/<case>/`

Для каждого реального бага хранить:
- sanitised telemetry/events;
- expected classification;
- expected policy decision;
- forbidden regressions.

Например:

```text
witcher3_oled_90_balanced_delivered_deeper
witcher3_oled_90_capacity_x3
witcher3_oled_90_repeated_9w_floor
witcher3_oled_90_low_draw_not_power_bound
```

Unit tests на вручную собранных `WindowVerdict` полезны, но replay должен прогонять максимально близкий к реальности поток.

---

# 13. Нужен Scene/Transient detector, иначе policy будет продолжать лечить краткие события

1.0.11 уже обнаружил проблему: low-FPS window не обязательно power shortage.

Следующий шаг нельзя делать ещё десятью исключениями.

Нужен отдельный detector:

```text
SCENE_STABLE
SCENE_CHANGE
LOADING
TRANSIENT_STUTTER
SUSTAINED_DEGRADATION
```

При SCENE_CHANGE:
- коротко наблюдать;
- не учить GameModel;
- не менять резко point.

При TRANSIENT_STUTTER:
- не покупать watts;
- не менять multiplier;
- не записывать failure.

При SUSTAINED_DEGRADATION:
- разрешать policy action.

---

# 14. Utility/Pareto слой всё ещё остаётся главным недостающим "мозгом"

Несмотря на улучшения, BudgetController всё ещё в основном rule/search controller.

Проект уже научился:
- пропускать плохие points;
- учитывать draw;
- учитывать heat;
- помнить failures;
- искать watts.

Следующий качественный скачок:

не "какое правило сработало следующим", а

> какой из доступных operating points сейчас имеет наибольшую ожидаемую utility?

Использовать:
- power saving;
- real FPS;
- p95 frametime;
- stutter;
- latency proxy;
- scale penalty;
- generation penalty;
- thermal headroom;
- transition cost;
- confidence.

Это позволит перестать наращивать if/else вокруг каждого нового реального лога.

---

# 15. Confidence должна быть не только UI-меткой

В исходной доктрине confidence задумывалась как часть decision making.

Нужно привязать её к действиям.

Например:
- low confidence -> наблюдать дольше;
- medium -> разрешать маленькие probes;
- high -> warm start / larger optimization step;
- stale context -> confidence decay.

Особенно это полезно для persistent GameModel, чтобы один короткий лог не превращался в вечную истину.

---

# 16. Session savings нужно считать как energy, а не только W

"Saving 9 W" понятно пользователю, но для сравнения сессий полезнее:

- average saved W;
- saved Wh;
- estimated battery minutes gained.

Например:

```text
Average saving: 7.8 W
Energy saved this session: 2.6 Wh
Estimated battery gained: +34 min
```

Это напрямую соответствует продуктовой цели.

---

# 17. UI: Recent Sessions не должна превращать Details в новую свалку

Добавление Recent Sessions логично именно в Details, не в Home.

Но держать границу:

Home:
- output;
- real;
- multiplier;
- frametime;
- TDP;
- temperature;
- savings;
- mode;
- Run/Stop;
- Details.

Details:
- why;
- live diagnosis;
- current decision;
- confidence;
- recent sessions;
- compact learned state.

Diagnostics:
- raw failures;
- floor timers;
- exact thresholds;
- engine capacity;
- raw timeline;
- pipeline.

Не переносить новые внутренние state-машины на Home только потому, что они появились в backend.

---

# 18. UI: history должна быть объясняющей, а не просто списком цифр

После исправления mixed-mode history полезный формат:

```text
Witcher 3 · 31 min
Battery 18m · Balanced 13m
Avg 89 FPS · 10.8 W · max 77 C
Saved ~2.9 Wh
```

Можно показывать 3–5 последних сессий.

Не превращать это в dashboard с десятками KPI.

---

# 19. governor_service.py всё ещё нужно удерживать от повторного разрастания

Вынос `governor_confirmation.py` — правильный шаг.

Продолжить по исходной архитектуре:

- TelemetryHub;
- StateEstimator;
- GameModelStore;
- GovernorPolicy;
- RuntimeActuator;
- PowerController;
- SessionEvaluator;
- Supervisor.

Каждый новый field-log fix сначала спрашивать:

> это новая политика, новое evidence или lifecycle plumbing?

И класть код в соответствующий слой.

---

# 20. Текущее главное правило

Новый реальный лог не должен автоматически означать:

`добавить ещё один if`.

Правильная последовательность:

1. определить новый наблюдаемый факт;
2. понять, к какому state он относится;
3. добавить signal/estimator;
4. проверить policy;
5. сохранить learned evidence;
6. сделать replay regression.

И только потом добавлять правило, если оно действительно универсально.

---

# Приоритет работ после 1.0.11

## P0 — consistency
1. Persistent floor-memory через controller rebuild/reload.
2. Correct mixed-mode session history.
3. Реальный test 60 Hz/LCD или dock.
4. Real replay fixtures для уже собранных Deck логов.

## P1 — StateEstimator
1. POWER_BOUND / CPU_BOUND / GPU_BOUND / THERMAL / TRANSIENT / UNKNOWN.
2. Confidence.
3. Scene/transient detector.
4. Thermal headroom.

## P2 — единый GameModel
1. stable/failed points;
2. floor evidence;
3. scale effectiveness;
4. context fingerprint;
5. confidence decay;
6. efficiency history.

## P3 — utility policy
1. candidate generation;
2. expected utility;
3. Pareto frontier;
4. minimum rational TDP;
5. experience floor.

## P4 — validation
1. OLED 90;
2. LCD 60;
3. dock/external;
4. CPU/GPU-bound game set;
5. 30–60 min thermal soak;
6. suspend/resume;
7. conflicting TDP tools.

---

# Итоговая оценка 1.0.11

Направление после реальных Deck-логов стало заметно правильнее.

Особенно важны:
- actual draw вместо слепой веры в TDP cap;
- per-game failure memory;
- thermal-aware policy;
- replay-like regression tests;
- разделение confirmation logic;
- пользовательские savings/session summaries.

Главный риск теперь не в том, что Governor "слишком тупой".

Главный риск — что интеллект будет расти как коллекция локальных memories, TTL и эвристических `if` вместо общей модели состояния игры.

Следующая архитектурная цель:

```text
Telemetry
-> StateEstimator
-> GameModel
-> Candidate Prediction
-> Utility
-> Apply
-> Verify
-> Learn
```

А не:

```text
new log
-> new exception
-> new TTL
-> new flag
```

Главная продуктовая метрика остаётся той же:

**максимум хорошего игрового опыта на каждый потраченный ватт.**
