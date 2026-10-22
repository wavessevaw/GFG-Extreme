<div align="center">

[English](README.md) · **Русский**

<img src="docs/img/logo.png" alt="GFG Extreme" width="144">

# GFG EXTREME 3.0.0

**MOST POWERFUL DECKY PLUGIN EVER.**

Compositor-Native Frame Generation · Intelligent APU Control · Gamescope Integration

[**Скачать последнюю**](https://github.com/wavessevaw/GFG-Extreme/releases/latest) · [Установка](#установка) · [Kedavra](#02--gsf-kedavra) · [Autopilot](#04--gfg-autopilot) · [Режимы](#06--performance-modes) · [HUD](#08--observability)

[![Release](https://img.shields.io/github/v/release/wavessevaw/GFG-Extreme?include_prereleases&style=flat-square&color=fb0d00&label=release)](https://github.com/wavessevaw/GFG-Extreme/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/wavessevaw/GFG-Extreme/total?style=flat-square&color=20242e)](https://github.com/wavessevaw/GFG-Extreme/releases)
[![Steam Deck](https://img.shields.io/badge/Steam%20Deck-OLED%20%7C%20LCD-20242e?style=flat-square)](#установка)
[![Decky](https://img.shields.io/badge/Decky%20Loader-plugin-20242e?style=flat-square)](https://github.com/SteamDeckHomebrew/decky-loader)
[![Engine](https://img.shields.io/badge/engine-GSF%20Kedavra-fb0d00?style=flat-square)](https://github.com/wavessevaw/GSF_Kedavra)
[![No Lossless Scaling](https://img.shields.io/badge/Lossless%20Scaling-not%20needed-20242e?style=flat-square)](#02--gsf-kedavra)
[![License](https://img.shields.io/badge/license-GPL--3.0-20242e?style=flat-square)](LICENSE.md)
[![Telegram](https://img.shields.io/badge/Telegram-gfg__extreme-26a5e4?style=flat-square&logo=telegram&logoColor=white)](https://t.me/gfg_extreme)

<img src="docs/img/card-overview.png" alt="GFG Extreme 3.0.8: Dash, Graphics, Engine and Setup tabs" width="900">

<sub>Настоящий интерфейс GFG Extreme 3.0.0, отрисованный в браузере на примерных данных. Это не замер игры.</sub>


<table>
<tr>
<td width="33%" align="center"><b>GSF KEDAVRA</b><br><sub>Своя генерация кадров внутри Gamescope. Auto, ×2, ×3, ×3.75, Custom. SDR и HDR.</sub></td>
<td width="33%" align="center"><b>AUTOPILOT</b><br><sub>Измерить, закрепить, охранять, адаптировать. Минимальный TDP, который держит FPS.</sub></td>
<td width="33%" align="center"><b>ОДИН ZIP</b><br><sub>Ставится из Decky. Сам ставит свой Gamescope и сам откатывается.</sub></td>
</tr>
</table>

</div>

---

## FRAME GENERATION HAS MOVED INTO THE COMPOSITOR.

### A FUNDAMENTAL SHIFT IN STEAM DECK PERFORMANCE.

GFG Extreme 3.0.0 объединяет собственный движок кадровой генерации GSF Kedavra и интеллектуальную систему управления производительностью GFG Autopilot / Governor.

Генерация кадров, планирование их вывода и оптимизация энергопотребления теперь рассматриваются как взаимосвязанные процессы в рамках одного графического конвейера.

Kedavra выполняет GPU motion estimation и реконструкцию промежуточных кадров непосредственно внутри Gamescope. GFG анализирует производительность игры, вычислительную стоимость генерации и доступный энергетический бюджет Steam Deck.

Lossless Scaling, MAKO и сторонние слои генерации не нужны: весь кадровый конвейер работает внутри собственного Gamescope.

В основе версии 3.0 лежат три технологических направления:

**FRAME RECONSTRUCTION**
Собственный Vulkan Compute pipeline для оценки движения и создания промежуточных изображений.

**PRESENTATION CONTROL**
Планирование кадров на уровне композитора с учётом обновления дисплея и готовности GPU-вычислений.

**INTELLIGENT POWER MANAGEMENT**
Замкнутый контур управления TDP с обратной связью и проверкой эффективности принимаемых решений.

**ONE ENGINE. ONE CONTROL PLANE. ONE PERFORMANCE TARGET.**

---

## Установка

1. Скачайте последний **GFG-Extreme-v3_x_x.zip** со страницы [Releases](https://github.com/wavessevaw/GFG-Extreme/releases/latest).
2. В Decky Loader: **Settings → Developer → Install Plugin from ZIP**, выберите файл.
3. Откройте GFG Extreme → **Setup** → **Engine install**, установите Kedavra и перезагрузитесь, когда плагин попросит.
4. Запустите игру и выберите режим на вкладке **Dash**. Больше ничего настраивать не нужно: ни параметров запуска, ни скриптов в Desktop Mode.

Переход с 2.x: настройки переносятся с резервной копией, MAKO удаляется, система восстанавливается автоматически.

> 3.0.0 это pre-release. Если Gaming Mode не поднимется с Gamescope от Kedavra, при следующей загрузке вернётся штатный композитор.

---

## 01 / GENERATION PHILOSOPHY

### MORE GENERATED FRAMES ISN'T ALWAYS BETTER.

### WHY WE DELIBERATELY STOP AT ×4.

Максимальный коэффициент генерации не является показателем эффективности графической системы.

С ростом множителя увеличивается доля синтетических кадров, повышаются требования к реконструкции движения, а итоговая отзывчивость всё сильнее зависит от частоты оригинального рендеринга.

Можно получить высокий Output FPS, сохранив недостаточный Real FPS. В результате численные показатели растут быстрее, чем фактическое качество игрового процесса.

В GSF Kedavra установлен архитектурный предел генерации ×4: не больше трёх синтетических кадров на один настоящий.

На практике нижняя граница ещё строже. Auto и Battery не опускают игру ниже 24 FPS на 90 Гц, то есть дальше ×3.75 не идут. Это «золотая середина»: экономия энергии без слайд-шоу. Ручной режим Custom принимает любую базовую частоту от 20 FPS, но не глубже ×4.

Множитель не обязан быть целым. Kedavra ограничивает игру базовой частотой, а генерация заполняет каждое обновление дисплея. Поэтому на 90 Гц 40 FPS дают ×2.25, 35 FPS дают ×2.6, а 24 FPS дают ×3.75.

**Engineering priorities**

* **Original FPS first.** Сохранение достаточной частоты настоящих игровых кадров.
* **Bounded latency.** Контроль дополнительной задержки интерполяционного конвейера.
* **Consistent pacing.** Минимизация повторов и пропущенных интервалов.
* **GPU budget awareness.** Учёт вычислительной стоимости генератора.
* **Performance per watt.** Оптимизация потребления без ухудшения полезной производительности.

**WE DON'T MAXIMIZE THE MULTIPLIER.**
**WE MAXIMIZE THE USEFUL RESULT.**

---

## 02 / GSF KEDAVRA

### COMPOSITOR-NATIVE FRAME GENERATION.

GSF Kedavra — собственный графический движок GFG Extreme с интеграцией непосредственно в Gamescope.

Он объединяет получение оригинальных кадров, многомасштабную оценку движения, реконструкцию промежуточных изображений и управление их предъявлением.

**Processing pipeline**

```
                    GAME RENDERING
                          │
              Base FPS cap (Kedavra limiter)
                          │
                          ▼
                   ORIGINAL FRAMES
                          │
          ┌────────── GAMESCOPE ──────────┐
          │                               │
          │          GSF KEDAVRA          │
          │                               │
          │     Frame History (ring)      │
          │              ↓                │
          │   Luma Pyramid (4 levels)     │
          │              ↓                │
          │   Multi-Resolution Motion     │
          │   Estimation (bidirectional)  │
          │              ↓                │
          │  Scene-Cut & Camera Motion    │
          │              ↓                │
          │     VBlank-Aware Scheduler    │
          │  (real / generated / repeat)  │
          │              ↓                │
          │    Temporal Reconstruction    │
          │   (motion-compensated warp)   │
          │              ↓                │
          │   Post Filters (after FG)     │
          │              ↓                │
          │  Frame Composition + HUD      │
          │                               │
          └──────────────┬────────────────┘
                         │
                         ▼
                      DRM / KMS
                         │
                         ▼
                       DISPLAY
```

Анализ движения выполняется один раз на каждый настоящий кадр, отдельной отправкой на GPU после композиции. Каждое обновление дисплея планировщик решает, что показать: настоящий кадр, сгенерированный или (если данных не хватило) повтор. Только после этого строится нужный промежуточный кадр.

**Engine capabilities**

| Component | Implementation |
|---|---|
| Graphics API | Vulkan |
| Processing | GPU Compute Shaders |
| Motion Estimation | Multi-resolution, bidirectional, with temporal seeding |
| Frame Reconstruction | Motion-compensated interpolation |
| Multipliers | Auto / ×2 / ×3 / ×3.75 / Custom base FPS (fractional, up to ×4) |
| Automatic Mode | Base FPS chosen from the game's measured frame rate |
| Source FPS Control | Kedavra base FPS cap inside Gamescope (Steam's limiter is not used) |
| Frame Scheduling | VBlank-aware |
| Color | SDR (8/10-bit) and HDR: HDR10 PQ and scRGB in float frames |
| Diagnostics | KMS flip tracing (Pace capture) |
| Target Hardware | Steam Deck OLED (90 Hz); Steam Deck LCD and docked 60 Hz |

**Target operating points**

| Display | Original FPS | Multiplier | Output |
|---|---|---|---|
| 90 Hz | 45 | ×2 | 90 FPS |
| 90 Hz | 40 | ×2.25 | 90 FPS |
| 90 Hz | 35 | ×2.6 | 90 FPS |
| 90 Hz | 30 | ×3 | 90 FPS |
| 90 Hz | 24 | ×3.75 | 90 FPS |
| 60 Hz | 30 | ×2 | 60 FPS |
| 60 Hz | 25 | ×2.4 | 60 FPS |
| 60 Hz | 20 | ×3 | 60 FPS |

При целом множителе (×2, ×3) между каждой парой настоящих кадров стоит одинаковое число промежуточных: один при ×2, два при ×3 (на 1/3 и 2/3 интервала). При дробном множителе настоящие кадры приходят через 2 и 3 (или 3 и 4) обновления дисплея, и генерация заполняет каждое обновление.

Kedavra также поддерживает автоматический выбор базовой частоты игры (Auto). Выбранная рабочая точка зависит от доступности оригинальных кадров и их стабильности.

Указанные значения являются целевыми режимами. Реальный Output FPS определяется производительностью игры, доступным GPU-временем и соблюдением сроков композиции.

---

## 03 / PRESENTATION-LEVEL CONTROL

### FRAME GENERATION IS ONLY HALF THE PROBLEM.

Готовый промежуточный кадр должен не просто существовать в GPU-памяти. Он должен быть предъявлен дисплею в правильный момент.

При частоте обновления 90 Гц интервал между обновлениями составляет 11,111 мс.

Kedavra использует планировщик, связанный с циклами обновления Gamescope, для координации оригинальных и синтетических кадров.

**VBlank-aware scheduling**

Планировщик учитывает:

* время поступления оригинальных кадров;
* готовность GPU-вычислений;
* временные позиции синтетических изображений;
* текущую частоту дисплея;
* пропущенные слоты;
* повторные предъявления;
* изменения исходного FPS;
* смену сцены (через склейку кадры не смешиваются);
* восстановление после длительных разрывов кадрового потока.

**GPU execution & synchronization**

Промежуточные кадры создаются в Vulkan Compute pipeline, интегрированном с процессом композиции.

Такое расположение позволяет согласовывать генерацию с графическими операциями Gamescope и контролировать стоимость дополнительных вычислительных проходов. Если анализ движения систематически не успевает, генерация временно отключается и потом включается снова, а не ломает ритм.

**KMS-level diagnostics**

Трассировка событий вывода предоставляет данные для анализа кадрового ритма, пропусков и поведения планировщика под нагрузкой.

Архитектурная цель — стабильное предъявление полезных кадров при минимально необходимой дополнительной задержке.

Интерполяции нужен следующий настоящий кадр, поэтому изображение показывается примерно на один исходный кадр позже плюс время анализа. Реальная end-to-end latency зависит также от частоты оригинального рендеринга и дисплея, поэтому подлежит отдельному аппаратному измерению.

**GENERATE. SCHEDULE. PRESENT.**
**EVERY FRAME HAS A DEADLINE.**

---

## 04 / GFG AUTOPILOT

### CLOSED-LOOP PERFORMANCE OPTIMIZATION.

GSF Kedavra управляет кадровым конвейером.

GFG Autopilot управляет производительностью системы, обеспечивающей его работу.

CPU, GPU, игра, вычислительные шейдеры и композитор используют общий энергетический бюджет Steam Deck.

Оптимальная рабочая точка зависит от реальной нагрузки, стоимости генерации и доступной мощности.

GFG Autopilot объединяет Auto движка Kedavra и Autopilot GFG Extreme. Он выбирает рабочую точку (базовую частоту и множитель) и координирует решения с GFG Governor, который управляет TDP.

**Control loop**

```
              GAME + GSF KEDAVRA
                       │
                       ▼
                UNIFIED TELEMETRY
  Real FPS / Pacing / GPU time / CPU & GPU load
           Power / Temp / Clocks
                       │
                       ▼
                 GFG AUTOPILOT
             Operating Point Selection
                       │
                       ▼
                  GFG GOVERNOR
               TDP Optimization
                       │
                       ▼
                 STEAM DECK APU
                       │
                       └──── Feedback
```

**Operating principles**

**MEASURE** — Замер на полном TDP: какую частоту игра стабильно держит.
**LOCK** — Фиксация устойчивой рабочей точки (базовая частота + множитель).
**GUARD** — Страховка точки: Governor снижает TDP, пока точка держится, и возвращает мощность при первых признаках просадки.
**ADAPT** — Если точка не держится даже на полной мощности, переход на ступень ниже; со временем осторожная проверка ступени выше.
**STABILIZE** — Сохранение эффективной рабочей точки и ограничение ненужных вмешательств.

Governor стремится использовать минимально необходимый энергетический бюджет, достаточный для устойчивой работы игры и генератора.

**Распределение мощности между CPU и GPU**

Каждую секунду GFG измеряет загрузку самого занятого ядра CPU, загрузку GPU и его частоту и использует их на зафиксированной точке:

- **Power Split** (игра упирается в GPU): CPU и GPU делят один лимит мощности, поэтому GFG ступенями снижает максимальную частоту CPU (100 / 85 / 70 / 60 / 50 %, не ниже 1,6 ГГц) и отдаёт освободившиеся ватты GPU. Каждая ступень подтверждается окнами A/B/A; ограничение снимается сразу, если просели настоящие кадры или самое занятое ядро подошло к пределу.
- **Потолок частоты GPU** (игра упирается в CPU): когда предел задаёт CPU, а GPU загружен слабо, GFG снижает частоту GPU шагами по 100 МГц через штатное управление частотой GPU в SteamOS (ползунок в меню быстрого доступа) и оставляет шаг, только если частота кадров держится, а потребление APU падает.

Оба механизма работают только на зафиксированной точке при успокоившемся Governor, по одному, и каждое изменение перезапускает окна измерений. Собственные ограничения CPU и ручная частота GPU игрока всегда возвращаются и никогда не перезаписываются.

Снижение потребления, сопровождающееся ухудшением оригинального FPS, кадрового ритма или стабильности генерации, не считается успешной оптимизацией.

**EFFICIENCY WITHOUT SACRIFICING FRAME STABILITY.**

---

## 05 / UNIFIED CONTROL ARCHITECTURE

### TWO INTELLIGENT SYSTEMS. ONE CONTROL PLANE.

GFG Extreme и Kedavra используют специализированные управляющие алгоритмы.

Их ответственность разграничена на уровне системы.

| GSF Kedavra | GFG Extreme |
|---|---|
| Source FPS limiting | Operating point selection (Autopilot) |
| Generation multiplier | TDP optimization (Governor) |
| Motion estimation | Performance analysis |
| Frame reconstruction | APU power, temperature, CPU & GPU load telemetry |
| Presentation scheduling | Power Split (CPU clock) & GPU clock ceiling |
| | Thermal protection |
| GPU generation diagnostics | Operating-point history per game |
| Post filters & HUD layer | Filter, HUD and profile settings |

Kedavra является владельцем FPS limiter и механизмов кадровой генерации.

GFG передаёт движку согласованную политику (множитель, базовую частоту, фильтры) и считает её применённой только после подтверждения от движка. GFG управляет энергетической политикой системы (TDP, ограничение частоты CPU и потолок частоты GPU).

При изменении базовой частоты или множителя Governor получает новую рабочую точку. Энергетические испытания не смешивают измерения несовместимых состояний.

Если другой инструмент (например, отдельный плагин GSF Kedavra) меняет те же настройки, GFG не вступает с ним в борьбу: он отступает и предлагает забрать управление.

**ONE OWNER PER CONTROL. ONE CONSISTENT SYSTEM STATE.**

---

## 06 / PERFORMANCE MODES

### EXPLICIT PRIORITIES. ADAPTIVE EXECUTION.

<p align="center"><img src="docs/img/card-modes.png" alt="Battery, Balanced, Quality and Autopilot" width="900"></p>

GFG Extreme предлагает четыре стратегии управления производительностью.

| Mode | Optimization objective |
|---|---|
| Autopilot | Один адаптивный режим: не выше 15 Вт, держит базу 35–40, если игра её тянет, минимум ×3, ×3.75 только если ×3 требует все 15 Вт или батарея садится |
| Battery | Приоритет эффективности: ×3.75 на 90 Гц (×3 на 60 Гц) и минимальный TDP, который её держит |
| Balanced | Самая высокая базовая частота, которую игра держит, без избыточных изменений; не ниже x3 |
| Quality | Приоритет оригинальных кадров и качества движения; не ниже x2.5 |

Стратегия определяет цели оптимизации.

Kedavra исполняет согласованную политику кадровой генерации, а Governor оценивает доступный энергетический бюджет.

Один и тот же целевой Output FPS может достигаться разными сочетаниями оригинальной частоты и множителя, но выбор учитывает их фактическую стоимость и качество.

Плагин запоминает каждую игру: на какой точке она держалась, её класс и медианы последних сессий. Знакомая игра сразу встаёт на свою точку, без повторного замера на полной мощности.

* **Лёгкие игры** (DuckTales, Terraria, Hades, Celeste и другие игры из встроенного списка или игры, которые на вашем Deck оказались лёгкими): 4–7 W и не выше ×2 в Balanced, Quality и Autopilot.
* **Тяжёлые игры** (The Witcher 3, Elden Ring, Cyberpunk 2077, Death Stranding и другие): сессия стартует с 15 W.
* **Док (TV)**: с внешним геймпадом важна задержка, поэтому выше ×3 там не идёт ни один режим. Высокий TDP на TV допустим, температура всё равно под контролем.
* **Steam Deck LCD**: 60 Гц или собственная частота разлоченной панели (например 75 Гц).

### МЫ БЕРЕЖЁМ ВАШ STEAM DECK.

SteamOS позволяет процессору часами работать при 85–89 °C. Мы с этим не согласны и хотим, чтобы ваш Deck прослужил дольше.
GFG Extreme намеренно сдерживает игры начиная с 80 °C, в любом режиме:

| Температура APU | Что делает GFG Extreme |
|---|---|
| 80 °C | Ни один режим не переходит на более тяжёлую точку: никаких лишних ватт ради лишних кадров |
| 85 °C | Потолок TDP снижается по ватту, пока Deck не остынет до 80 °C |
| 97 °C | TDP сразу падает до минимума |

Кроме того, ни один режим не поднимает TDP выше 15 W, даже если SteamOS разрешает 20 W.

---

## 07 / IMAGE PROCESSING

### A UNIFIED VISUAL PIPELINE.

GFG Extreme сохраняет систему графических фильтров, перенесённую внутрь Gamescope. vkBasalt больше не нужен.

Фильтры применяются после генерации к кадру, который выводится на экран. Анализ движения никогда не видит отфильтрованные пиксели, поэтому зерно и резкость не создают ложного движения. Настоящие и сгенерированные кадры получают одинаковую обработку, а HUD и оверлеи Steam остаются без фильтров.

**Color & Tone**
HDR Look · Vibrance · Colourfulness · Curves · Technicolor · Technicolor 2 · DPX · Levels Plus

**Sharpness & Anti-Aliasing**
CAS · DLS · Clarity · FXAA · SMAA

**Creative Processing**
Film Grain · Vignette · Chromatic Aberration · Deband · Noir · Sepia · Monochrome · Bleach Bypass · Cartoon · Nostalgia

Пресеты: Sharp · Vivid · HDR Look · Cinema · Noir · Retro · Smooth.

Порядок графических проходов фиксирован: цвет и тон → резкость → сглаживание → финальные эффекты (виньетка, зерно, хроматическая аберрация).

Фильтры работают с закодированными значениями пикселей (sRGB), как в ReShade и vkBasalt. Двойного sRGB-декодирования нет.

**HDR.** HDR-игры (HDR10 PQ и scRGB) поддерживаются генерацией кадров. Цветовые фильтры — художественные SDR-эффекты и к HDR-кадрам не применяются. На HDR10 работают резкость, сглаживание и финальные эффекты, на scRGB фильтры не применяются. HDR Look — это SDR-фильтр «под HDR», а не режим HDR-вывода.

---

## 08 / OBSERVABILITY

### MEASURE THE PIPELINE. NOT JUST THE FPS.

<p align="center"><img src="docs/img/hud-rings-gfg3.png" alt="In-game HUD: minimal and standard" width="700"></p>

Единая телеметрия GFG Extreme охватывает оригинальный рендеринг, генерацию, предъявление кадров и аппаратные ресурсы.

| Metric | Description |
|---|---|
| Real FPS | Оригинальная производительность игры |
| Output FPS | Новые кадры на экране (настоящие + сгенерированные) |
| Effective Multiplier | Текущий режим генерации |
| Pace | Доля обновлений дисплея без повторов |
| KMS Flip Events | Зарегистрированные события предъявления |
| GPU Generation Time | Стоимость вычислений генератора и фильтров |
| APU Power Draw | Фактическое потребление APU |
| TDP Limit | Установленный энергетический бюджет |
| APU Temperature | Температура и тепловой запас |
| CPU / GPU Load | Загрузка самого занятого ядра CPU, загрузка и частота GPU |
| CPU Clock Cap / GPU Clock Ceiling | Текущий потолок частоты CPU (Power Split) и GPU |
| Autopilot State | Фаза управляющего контура (замер, фиксация, страховка, адаптация) |

Система разделяет внутренние события генерации и фактически подтверждённые события вывода.

Диагностические трассы позволяют исследовать пропуски кадров, переходы между рабочими точками, перегрузку GPU и эффективность изменения TDP.

Результаты аппаратных испытаний могут быть воспроизведены и сопоставлены с решениями управляющей системы.

**REAL METRICS. REPRODUCIBLE RESULTS.**

---

## 09 / NATIVE STEAMOS INTEGRATION

### ONE ENGINE. ONE INTERFACE.

<p align="center"><img src="docs/img/card-ring-sizes.png" alt="Tap the ring: Side, Classic, Compact, Arc" width="900"></p>

GFG Extreme 3.0.0 — единая система управления генерацией и производительностью через Decky Loader. Один zip, устанавливается из Decky, без скриптов в Desktop Mode.

Kedavra интегрируется на уровне Gamescope, поэтому в штатном Gaming Mode генерация не требует отдельной команды запуска для каждой игры.

**Core capabilities**

* Compositor-native frame generation, SDR and HDR.
* Kedavra Off / Auto / ×2 / ×3 / ×3.75 / Custom base FPS.
* GFG Governor & Autopilot.
* Adaptive TDP management.
* Per-game profiles.
* Graphics filters & image enhancement after generation.
* Unified performance HUD (drawn by Gamescope, after generation).
* GPU and APU telemetry.
* Session diagnostics and Pace capture.
* Controlled Gamescope installation, automatic rollback and recovery.
* Settings migration from GFG Extreme 2.x (with a backup).

Целевая платформа: Steam Deck OLED / SteamOS.

Для работы нужен Gamescope с Kedavra, плагин ставит его сам. Установка проверяет систему, а загрузка, которую Gamescope Kedavra не подтвердил, автоматически откатывается к штатному композитору.

---

## 10 / ENGINEERING INDEPENDENCE

### OUR ENGINE. OUR FRAME PIPELINE. OUR ROADMAP.

GFG Extreme 3.0.0 использует собственное ядро кадровой генерации GSF Kedavra.

Алгоритмы оценки движения, реконструкции изображений и планирования синтетических кадров развиваются в рамках единой кодовой базы GFG / GSF.

Это обеспечивает независимость направления разработки генератора и позволяет непосредственно оптимизировать его взаимодействие с Gamescope, Vulkan и управляющими алгоритмами GFG.

**Technology stack**

| Subsystem | Technology |
|---|---|
| Frame Generation | GSF Kedavra |
| GPU Processing | Vulkan Compute |
| Motion Estimation | Multi-resolution |
| Frame Reconstruction | Motion-compensated |
| Scheduling | Gamescope / Kedavra |
| Presentation | DRM / KMS |
| Power Management | GFG Governor (TDP), Power Split, GPU clock ceiling |
| Intelligent Control | GFG Autopilot |
| Interface | Decky Loader |

Основные технологии остаются частью открытого графического стека Linux.

Разработка генератора, управление его вычислительной стоимостью и взаимодействие с системой предъявления кадров объединяются в одном проекте.

**A NEW ENGINE.**
**A NEW PRESENTATION MODEL.**
**A NEW FOUNDATION FOR GFG EXTREME.**

---

## GFG EXTREME 3.0.0

### THE COMPOSITOR-NATIVE GENERATION RELEASE.

Крупнейшее архитектурное обновление GFG Extreme объединяет собственную кадровую генерацию GSF Kedavra, управление предъявлением внутри Gamescope и интеллектуальную оптимизацию APU.

Версия 3.0.0 формирует единую платформу для дальнейшего развития GPU-реконструкции, кадрового планирования и энергетического управления на Steam Deck.

**NATIVE FRAME GENERATION.**
**PRESENTATION-LEVEL CONTROL.**
**INTELLIGENT POWER MANAGEMENT.**
**POWERED BY GSF KEDAVRA.**
**ENGINEERED FOR STEAM DECK.**

---

## Development & Validation

Результаты версии 3.0.0 оцениваются по измеримым характеристикам:

* Original FPS stability.
* Presentation interval P95/P99.
* Frame generation GPU cost.
* Missed presentation deadlines.
* End-to-end latency.
* APU power consumption.
* Image reconstruction quality (SDR and HDR).
* Long-session stability.

Целевые показатели и фактические бенчмарки сборки 3.0.0 (включая ×3.75 и HDR) публикуются после проверки на реальном оборудовании.

---

## Project

* Repository: https://github.com/wavessevaw/GFG-Extreme
* GSF Kedavra: https://github.com/wavessevaw/GSF_Kedavra
* Community: https://t.me/gfg_extreme
* Platform: Steam Deck / SteamOS
* License: GPL-3.0-or-later, с соблюдением лицензий используемых компонентов

README описывает GFG Extreme 3.0.0 (pre-release). Возможности становятся частью подтверждённого релиза только после испытаний на реальном оборудовании.

---

<div align="center">

<img src="docs/img/logo.png" alt="GFG Extreme" width="56">

<sub>GFG EXTREME 3.0.0 · POWERED BY GSF KEDAVRA · Сделано для Steam Deck · GPL-3.0-or-later</sub>

</div>
