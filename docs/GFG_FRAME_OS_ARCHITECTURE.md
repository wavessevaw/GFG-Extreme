# GFG Frame OS / Presentation Runtime

Status: research architecture  
Branch: `research/gfg-frame-os-2026-10-07`  
Base: GFG Extreme 1.1.0

## 0. Зачем это нужно

Текущая архитектура GFG Extreme всё ещё строится вокруг модели:

```text
Decky UI
  -> Python Governor
  -> config/runtime overlay
  -> game launch wrapper
  -> Vulkan layer / Render v4
  -> Gamescope
```

Governor выбирает параметры, но сам presentation pipeline ему не принадлежит.

Следующий уровень продукта:

```text
Game
  -> GFG Presentation Runtime
      -> real-frame scheduler
      -> Render v4 / FG backend
      -> scaling
      -> pacing
      -> latency policy
      -> frame admission
      -> presentation queue
  -> Gamescope
```

Decky при этом перестаёт быть "движком".
Он становится control plane:

```text
Decky UI
  -> GFG Supervisor
      -> Frame Runtime IPC
      -> Power / GameModel / policy
```

Главная цель:

> GFG управляет не настройками генерации кадров, а временем и стоимостью каждого presented frame.

---

# 1. Не строить полноценный Wayland compositor сразу

Полный nested compositor между игрой и Gamescope технически возможен, но как первый шаг слишком дорог:

- собственный Wayland server;
- XWayland lifecycle;
- input routing;
- HDR/color;
- DRM formats/modifiers;
- explicit sync;
- VRR;
- Steam Overlay;
- Gamescope-specific behavior;
- Proton edge cases.

Это несколько проектов, а не одна функция.

Поэтому первый реальный слой называется:

## GFG Presentation Runtime

Он должен владеть Vulkan presentation path и scheduling, но не брать на себя desktop/window-management функции Gamescope.

---

# 2. Точка внедрения

Самая перспективная точка уже существует в проекте:

Render v4 находится в Vulkan layer и уже видит:
- swapchain;
- acquire;
- present;
- real cadence;
- generated cadence;
- runtime transitions;
- generated frame capacity;
- present diagnostics.

Это значит, что новый runtime не должен обходить Render v4.

Нужно разделить:

```text
Render v4 = frame synthesis executor

GFG Presentation Runtime =
  scheduler
  admission controller
  pacing owner
  frame-classification owner
  latency owner
  backend broker
```

Render v4 становится одним из backend execution modules.

---

# 3. Целевая архитектура

```text
                  ┌──────────────────────┐
                  │      Decky UI        │
                  └──────────┬───────────┘
                             │ RPC
                  ┌──────────▼───────────┐
                  │   GFG Supervisor     │
                  │ Python control plane │
                  └──────┬──────┬────────┘
                         │      │
                  policy │      │ power
                         │      ▼
                         │  PowerController
                         │
                  ┌──────▼──────────────────┐
                  │   Frame Runtime IPC     │
                  └──────┬──────────────────┘
                         │
                  ┌──────▼──────────────────────────────────┐
                  │       GFG Presentation Runtime          │
                  │              native                     │
                  │                                         │
Game Vulkan ----> │  Frame Admission                        │
                  │  Real-Frame Scheduler                   │
                  │  Present Scheduler                      │
                  │  Latency Controller                     │
                  │  Backend Broker                         │
                  │  Telemetry Producer                     │
                  └──────────────┬──────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
             ┌──────▼──────┐          ┌──────▼──────┐
             │ Render v4   │          │ future FG   │
             │ backend     │          │ backend     │
             └──────┬──────┘          └─────────────┘
                    │
             scale / compose
                    │
             ┌──────▼──────┐
             │  Gamescope  │
             └─────────────┘
```

---

# 4. Главная революция: multiplier перестаёт быть центральным понятием

Сейчас:

```text
30 real x3 -> 90 output
```

Новая модель:

```text
FrameTimeline
  t0 real
  t1 generated
  t2 generated
  t3 real
  t4 generated
  t5 real
  t6 generated
  t7 generated
  ...
```

То есть runtime оперирует:

- real-frame admission;
- generated-frame admission;
- deadlines;
- present slots;
- confidence;
- input sensitivity;
- backend capacity.

А `x2/x3/x3.5` становится статистическим следствием scheduling, а не управляющим preset.

---

# 5. Frame Admission Controller

Для каждого presentation slot runtime решает:

```text
REAL
GENERATED
REUSE
DROP
RECOVER
```

Первый MVP может поддерживать только:

```text
REAL
GENERATED
```

Позже:

- REUSE — повтор предыдущего устойчивого region/frame;
- DROP — сознательное удаление просроченного кадра;
- RECOVER — аварийный real frame после confidence loss.

---

# 6. Deadline scheduler

Runtime должен работать по deadlines, а не по "среднему FPS".

Для 90 Hz:

```text
slot = 11.111 ms
```

Для каждого slot:

```text
present_deadline
predicted_real_ready
predicted_fg_ready
input_age
queue_depth
frame_importance
thermal/power state
```

Решение:

```text
if real frame reliably lands before deadline
    and its value > generated alternative:
        use real
else:
        synthesize / reuse
```

---

# 7. Frame Importance

Первоначально без AI.

Прозрачный score:

```text
importance =
    input_activity
  + camera_motion
  + scene_change
  + UI_change
  + recent_generation_error
  + prediction_uncertainty
```

Высокий importance:
- чаще real frame;
- ниже generation depth;
- меньшая очередь;
- latency priority.

Низкий importance:
- глубже temporal generation;
- больше power saving.

---

# 8. Input-aware scheduling

Это один из ключевых будущих уровней.

Runtime должен уметь получать хотя бы агрегированный input state:

```text
stick magnitude
mouse delta
trigger/button activity
time since last input
```

Не нужно передавать raw key log в persistent storage.

Использование:

```text
high interaction
=> raise real-frame density
=> shorten queue
=> latency priority

low interaction
=> deeper generation
=> power priority
```

---

# 9. Energy-per-slot model

Вместо:

```text
TDP = 10 W
```

долгосрочная цель:

```text
next 250 ms energy budget = X joules
```

Runtime/Supervisor распределяют бюджет между:

- real render;
- FG;
- scaling;
- CPU headroom;
- thermal reserve.

Это превращает TDP из главного управляющего параметра в ограничение сверху.

---

# 10. IPC contract

Decky/Python policy не должна писать TOML и ждать логов, чтобы управлять новым runtime.

Нужен двусторонний IPC.

Рекомендуемый transport для MVP:

```text
Unix domain socket
/run/user/<uid>/gfg-frame-runtime.sock
```

Почему не DBus:
- лишняя зависимость/политика;
- Flatpak/SteamOS нюансы;
- socket проще тестировать и version.

Почему не файлы:
- нет атомарного request/ack protocol;
- плохо для high-frequency state.

---

# 11. IPC messages

## Runtime -> Supervisor

```json
{
  "type": "frame_state",
  "seq": 182991,
  "real_fps": 31.2,
  "output_fps": 89.8,
  "real_density": 0.347,
  "queue_depth": 1,
  "present_lateness_ms_p95": 0.8,
  "generation_miss_rate": 0.002,
  "backend": "render_v4",
  "capacity": 2,
  "confidence": 0.94
}
```

## Supervisor -> Runtime

```json
{
  "type": "policy",
  "generation": 418,
  "target_hz": 90,
  "min_real_fps": 28,
  "latency_budget_ms": 45,
  "max_generation_depth": 3,
  "scale_floor_pct": 90,
  "mode": "battery"
}
```

Главное:
policy задаёт ограничения и цель.

Runtime сам принимает per-frame решение.

---

# 12. Versioned protocol

Любое сообщение:

```text
schema
generation
session_id
```

Runtime обязан:
- reject unknown incompatible schema;
- ack policy generation;
- сохранять last-known-safe policy;
- fail open или fail safe в зависимости от типа ошибки.

---

# 13. Failure model

Presentation Runtime никогда не должен быть единственной причиной отсутствия картинки.

Fail-safe:

```text
runtime crash
=> Vulkan layer / wrapper returns to direct real-frame presentation
```

IPC loss:

```text
=> keep last safe policy for short grace
=> then conservative direct/Render-v4 mode
```

Bad scheduler state:

```text
=> force REAL frames
=> disable speculative generation
```

---

# 14. Совместимость с текущим GFG 1.1.0

Нельзя переписывать работающий Governor сразу.

Migration:

## Phase A — Observe-only runtime

Native runtime подключается к presentation path, но ничего не меняет.

Собирает:
- acquire timing;
- submit timing;
- present timing;
- queue depth;
- missed deadlines;
- actual present cadence.

Сверяется с текущим Render v4 telemetry.

Цель:
доказать наблюдаемость.

## Phase B — Shadow scheduler

Runtime рассчитывает:

```text
would_present = real/generated
```

но реальный pipeline не меняет.

Логируем divergence:
- current Governor decision;
- shadow per-frame decision;
- estimated latency/power consequence.

## Phase C — Bounded scheduling

Runtime получает право менять только cadence внутри текущего разрешённого multiplier envelope.

Например:
- Governor разрешил x1..x3;
- runtime динамически распределяет REAL/GENERATED внутри этого диапазона.

## Phase D — Runtime owns multiplier

Multiplier исчезает из policy.

Supervisor задаёт:
- min real cadence;
- max generation depth;
- latency/quality floor.

## Phase E — full Frame OS

Добавляются:
- frame importance;
- input-aware density;
- predictive scheduling;
- energy-per-slot;
- backend switching.

---

# 15. Где оставить Python

Python остаётся хорошим местом для:

- GameModel;
- long-window policy;
- power control;
- thermal model;
- persistent learning;
- UI/RPC;
- diagnostics;
- session evaluation.

Python НЕ должен делать:

- per-present scheduling;
- per-frame deadlines;
- queue synchronization;
- Vulkan ownership;
- high-frequency present decisions.

---

# 16. Где нужен native code

Новый runtime должен быть native.

Предпочтительные варианты:

## C++
Плюсы:
- Vulkan headers/tooling естественны;
- проще интеграция с существующим Render v4 lineage;
- меньше FFI.

## Rust
Плюсы:
- memory safety;
- хороший IPC/state-machine code;
- строгая ownership model.

Минус:
- интеграция с Vulkan/Wayland потребует больше инфраструктуры;
- repo сегодня не имеет Rust toolchain.

Для быстрого PoC предпочтительнее C/C++ рядом с существующим Vulkan layer ecosystem.

---

# 17. Не делать отдельный renderer

Это принципиально.

Не нужно:
- писать собственную optical flow FG;
- копировать Render v4;
- создавать второй генератор.

Нужно:

```text
scheduler > backend abstraction > Render v4
```

Если позже появится другой backend, runtime сможет выбирать его через тот же contract.

---

# 18. Backend API

Минимальная абстракция:

```cpp
struct BackendCapabilities {
    uint32_t maxGeneratedPerReal;
    bool supportsFractionalCadence;
    bool supportsRuntimeReconfigure;
    bool supportsScaling;
};

struct FrameRequest {
    uint64_t presentSlot;
    FrameKind kind;
    double deadlineMs;
    double targetTimestampMs;
};

struct BackendResult {
    bool ready;
    double predictedReadyMs;
    double confidence;
};
```

Render v4 adapter реализует этот contract.

---

# 19. Telemetry, которую новый runtime должен дать сразу

Это важнее первой оптимизации.

Нужно получить:

- acquire wait;
- GPU submit -> present latency;
- present deadline miss;
- present interval distribution;
- actual queue depth;
- real-frame age at display;
- generated-frame age;
- generation turnaround;
- swapchain recreation;
- compositor backpressure;
- frame admission decision;
- reason;
- scheduler confidence.

Это даст GFG реальные "глаза" в presentation pipeline.

---

# 20. Новая ключевая метрика

Не FPS.

## Presented Information Freshness

Приблизительно:

```text
age_of_latest_real_information_at_present
```

Два режима могут оба показывать 90 FPS:

A:
```text
real 45 -> x2 -> 90
freshness ~22 ms
```

B:
```text
real 30 -> x3 -> 90
freshness ~33 ms
```

Но при низком движении B может быть визуально почти равен A и потреблять намного меньше.

Governor должен оптимизировать именно trade-off:
- freshness;
- pacing;
- power;
- quality.

---

# 21. Революционная конечная модель

Сегодня:

```text
choose x3
choose 9 W
choose 90% scale
```

Будущее:

```text
For the next 250 ms:

90 Hz display
8 presentation slots
3 real frames
5 generated frames
scale 100%
latency ceiling 42 ms
energy budget 2.1 J
predicted experience confidence 91%
```

И scheduler сам размещает реальные кадры там, где они наиболее ценны.

---

# 22. Первый PoC

Не пытаться сразу управлять кадрами.

Первый PoC должен доказать только это:

> GFG может наблюдать каждый present slot и построить независимый timeline точнее текущего log-based Governor.

Deliverables:

```text
native/presentation_runtime/
  runtime
  present_timeline
  ipc
  protocol

Python:
  runtime_client.py

tests:
  recorded timeline parser
  protocol compatibility
  disconnect/fallback
```

PoC output:

```json
{
  "slot": 191282,
  "present_interval_ms": 11.11,
  "real_age_ms": 31.4,
  "queue_depth": 1,
  "backend_generated": true,
  "late_ms": 0.2
}
```

Никаких runtime modifications на Phase A.

---

# 23. Условие перехода к управлению

Phase B/C запрещены, пока observe-only runtime не докажет:

- стабильную работу 30+ минут;
- отсутствие изменений картинки;
- отсутствие влияния на latency/pacing;
- корректную работу при game exit;
- swapchain recreation;
- fullscreen/window transitions;
- suspend/resume;
- telemetry loss;
- Render v4 enabled/disabled.

---

# 24. Как это меняет сам продукт

Decky UI больше не показывает "Governor сделал x3".

Он показывает:

```text
90 FPS
31 real FPS average
Freshness: 29 ms
Power: 8.7 W
Latency mode: Interactive
Scheduler confidence: 94%
```

А x2.7/x3.1 становится внутренней статистикой.

---

# 25. Итог

GFG Frame OS не должен быть "ещё более умным Governor".

Он должен стать:

> presentation scheduler, который решает, когда реальный кадр действительно стоит затрат CPU/GPU/энергии.

Render v4 остаётся сильным frame-synthesis backend.

Gamescope остаётся системным compositor.

Decky остаётся UI/control plane.

Новый GFG Presentation Runtime становится слоем, который связывает их в одну управляемую temporal system.
