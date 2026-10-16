# GFG Frame Generator: Architecture Decision 1.0

Дата: 16.10.2026. Решение: **GFG Shared Flow (GSF)** — иерархический
двунаправленный optical flow с проверкой доверия, ограниченным локальным уточнением
и двумя реконструкциями из общего анализа пары. LMC сохраняется как контрольная
реализация. Новый backend сначала существует только в вычислительном benchmark;
нативная интеграция и публикация продукта не выполняются до экспериментальных gates.

## Основания, которые уже есть

- В аппаратном архиве 074536Z старый GPU LMC при 1280×800 имел median готовности
  первого выхода 7.171 ms, второго 8.052 ms, p95 8.863/10.005 ms. Это выборка
  GPU timestamp intervals, включающая паузы очереди; не чистое время исполнения,
  не полная стоимость игры/transport и не physical scanout.
- Средние этапы той выборки: pyramid 0.494, analyze 4.072, classify 1.754 ms.
  Внутренние LMC интервалы: search B/A 0.928/0.944, layers 0.255, model 1.945,
  field 0.982, masked 0.245, orphan 0.337, field2 0.180 ms. Выборки/границы
  различаются; нельзя безусловно складывать эти средние с median всей пары.
  Неподвижный дополнительный global-model pipeline заметен в бюджете даже
  до полезной реконструкции; пользу каждого его прохода нужно оправдывать.
- Тот же запуск: 7339 real, 4051 synthetic, 10613 skipped WSI handoffs.
  В последнем bridge потери ring/history/acquire: 2986/2986/4183. Это прежде
  всего backpressure и транспорт, а не доказательство плохого optical flow.
- Следующий архив 082931Z не инициализировал генератор: MAILBOX + packed10 HDR.
  Число dispatch или ускорение анализа не исправляет позицию hook в Gamescope.
- `docs/TEMPORAL_ENGINE_BENCHMARK.md`: старый adaptive tile path на lavapipe
  был существенно дешевле full-everywhere при близкой средней метрике.
  Но быстрые повороты оставались плохими, а сокращение цены в простых областях
  не доказывает качество на motion boundaries. Эти числа не являются Deck times.
- Текущий LMC **уже** анализирует пару один раз, затем отдельно выполняет
  SELECT/COMPOSE для каждого t. Само по себе shared analysis не новая оптимизация
  относительно него. Проверять нужно сокращение общего анализа и per-output work.
- Предыдущие аппаратные ~520 ms `rgba_to_rgb` были CPU обработкой mapped staging.
  GPU resident capture/compute/output сохраняются. Возвращать CPU pixel bridge нельзя.
- MAKO подтверждает отдельные временные fractions и presentation policy, но FG
  использует пользовательский proprietary payload. AMD даёт открытые optical-flow,
  visibility/inpainting идеи и Vulkan presenter; полный FSR3 требует игровых
  ресурсов, которых обычный present hook не получает. Подробнее —
  [REFERENCE_REIMPLEMENTATION.md](REFERENCE_REIMPLEMENTATION.md).

## Сравнение и выбор

Оценки в таблице — ожидания конструкции. Сравнительных Deck измерений нет.

| Направление | GPU cost | Задержка | Качество / главный риск | Интеграция | Решение |
|---|---|---|---|---|---|
| A: dense flow + тяжёлая реконструкция везде | высокая, масштабируется с пикселями и числом кандидатов | lookahead + GPU work | детали хороши при правильном flow, ошибки occlusion остаются | RGB-only возможно | Не основной путь для ограниченного APU |
| B: дешёвый общий flow + сложные области | зависит от доли сложных блоков; нужен жёсткий предел | тот же lookahead | classifier может пропустить тонкий объект | RGB-only, явные confidence masks | Основа адаптивной стоимости |
| C: coarse-to-fine flow | дешёвый coarse search, уточнение локально | тот же lookahead | aliasing, малые быстро движущиеся детали | хорошо сочетается с B | Основа движения |
| D: история / предсказание | может сократить search, не гарантированно | экстраполяция уменьшает lookahead ценой ошибки | cuts, ускорение, newly visible content | история должна инвалидироваться на GPU | Только проверяемый predictor, не автономный генератор |
| E: GSF = B+C + ограниченная D | ожидается меньше global/model/dense-field passes | один реальный интервал + compute/presentation margin | границы, неизвестная глубина, шум и ошибочная уверенность | reuse Vulkan infrastructure, новый compute backend | **Выбрано** |
| Текущий GPU LMC | измеренная аппаратная выборка выше; solver/fields обязательны | lookahead + текущая очередь | global planes могут помогать камере; их цена не всегда оправдана | уже реализован, WSI ещё не принят | Контроль, не выбрасывается |

Предыдущий LMC не объявляется ошибочным целиком. Ошибочны ожидания, что меньше
CPU work автоматически даст 90 scanouts; что planes/orphans нужны каждой паре;
что неподвижность одного пикселя доказывает HUD; что FP16 сохраняет правильную
физическую HDR-интерполяцию; что software throughput переносится на RADV.

## Вычислительный путь

```text
R[n-1], R[n] (GPU images)
  -> обновление luma/RGB pyramid только для нового R[n]
  -> coarse-to-fine B->A и A->B, predictor из предыдущей пары
  -> residual / forward-backward agreement / ограниченное локальное уточнение
  -> общие flow + confidence + cut state
       -> visibility-aware reconstruction(t=1/3) -> G1
       -> visibility-aware reconstruction(t=2/3) -> G2
  -> history update; source images остаются неизменными
```

1. **Вход и история.** Два RGB изображения. Глубина/MV игры не выдумываются.
   История переиспользует allocation и pyramid предыдущего кадра. Никакого
   full-resolution GPU→CPU→GPU в runtime. Upload/download benchmark — явно
   отдельные операции, не заявляются производственным transport.
2. **Движение.** Пирамида до 1/16; block matching в обе стороны. Старые векторы —
   кандидаты, которые должны выиграть по текущей фотометрии. Нельзя доверять им
   без проверки или переносить через gap/cut/resize.
3. **Адаптивное уточнение.** На block grid оценить residual и disagreement.
   Для уверенных блоков оставить вектор; для остальных — ограниченное число
   локальных/subpixel кандидатов. Нет обязательного глобального RANSAC/IRLS,
   палитры и dense half-resolution field на каждой паре. Общий worst-case budget
   должен быть конечным даже когда всё изображение сложное.
4. **Реконструкция.** Перенести координаты к t; проверить A/B trajectories,
   границы и agreement обратного flow. Уверенный участок обрабатывается дёшево;
   сложный — соседние motion hypotheses и односторонняя видимость. Не усреднять
   произвольно движения разных поверхностей и не растягивать край за image bounds.
   Истинно статичные области сохраняют точные пиксели. Thin detail / HUD /
   полупрозрачность требуют отдельных локальных метрик, не только mean PSNR.
5. **Cut/неуверенность.** Не интерполировать заведомо разные сцены. Recovery/drop
   классифицируется отдельно; endpoint duplicate не считается выполненным 3×.
6. **HDR.** Prototype сначала SDR. Сохранить проверенные packed10/FP16 transport
   primitives для будущего пути; quality HDR потребует явного transfer-function
   преобразования, а PQ-code interpolation остаётся помеченной approximation.

Для 3× анализ A выполняется один раз: `cost_pair=A+S(1/3)+S(2/3)`.
Не нужно повторять A, но нельзя переиспользовать visibility result одного t
как универсальную маску другого t. Локальная реконструкция зависит от времени.

## Что сохраняется, что заменяется

Сохраняются Vulkan loader/dispatch, timeline API, timestamp queries, image/buffer
allocation, benchmark NPY input/output, тестовые сцены, input hashes, CPU/reference
LMC, borrowed-device tests и сохранённый native transport как отдельный workstream.
Coarse block search и history из LMC переиспользуются без переименования авторства.

В новом compute backend заменяются обязательный global-model fit, palette,
dense fields, orphan list search и half-res per-output SELECT на компактное
pair confidence/refinement и собственную time-aware реконструкцию. Если качество
падает, выяснять конкретную отсутствующую motion hypothesis; нельзя объявлять
экономию победой и скрывать regression средним показателем.

Первый prototype может разделять descriptor ABI с LMC ради малого изменения.
Неиспользуемые bindings получают маленькие валидные buffers/images; экономию
памяти считать по реальным Vulkan allocations, не по сумме размеров struct.

## Подача кадров и временной бюджет

Compute backend и Gamescope delivery проверяются отдельно. Выбранный продуктовый
путь — timestamped ordered output с отдельным владельцем deadlines и bounded
source credit, по подтверждённой WSI topology. Lower MAILBOX может сочетаться с
compositor FIFO. Простая downstream замена MAILBOX на FIFO не принята как решение.
Нужны согласованные queue provisioning/ownership и корректные app present-ID/fences.

30 FPS дают 33.333 ms между источниками; 90 Hz дают 11.111 ms между выходами.
Двукадровая интерполяция требует будущего реального кадра. Проектный scheduler
резервирует около одного source interval lookahead плюс GPU/readiness margin;
это не обещание нулевой задержки. Для примера, когда R1 готов в 33.333 ms,
его промежуточные значения могут быть показаны в 44.444 и 55.556 ms, R1 —
в 66.667 ms при задержанной общей шкале. Это условный график, не измерение.

Предварительный compute gate на Deck: p95 пары ≤6 ms при 1280×800 как цель
оптимизации, а не установленная возможность. Не жертвовать настоящими 30 FPS:
мерить FG-off/on, queue contention, power, input-to-display и p99 отдельно.
Даже 6 ms compute не доказывают cadence или качественные 90 FPS.

## Эксперимент до интеграции

Одинаковые сохранённые RGB входы и held-out targets для `lmc-gpu` и GSF.
Контролируемая сцена 90 FPS проверяет фактический stride 3 (30→90). Реальные
camera clips с native 60 FPS при stride 3 проверяют 20→60; их нельзя подписывать
как записанные 90 FPS. Нужны pan/rotation, независимые объекты, occlusion,
тонкие детали/HUD, cuts и static exactness. Реальные game captures отсутствуют;
это ограничение нельзя скрыть camera/synthetic corpus.

Измерять: pair analysis GPU ms, S1 и S2 GPU ms, ready1/ready2 и суммарный span,
CPU submission/wait отдельно, upload/readback отдельно от compute, allocation
bytes, source/output hashes, PSNR/SSIM, temporal error, boundary/ROI errors,
endpoint duplicates в динамике. Для timing — отдельный no-download прогон.
Prototype сравнивается с LMC tier0, не с произвольно ухудшенным baseline.
GPU timestamps lavapipe публикуются исключительно как software Vulkan.

Promotion gates до native integration:
- оба времени действительно различаются и уменьшают ошибку относительно endpoint;
- static exactness; отсутствие NaN/OOB/Vulkan validation ошибок;
- на одинаковых сценах ≥15% сокращения GPU span относительно LMC как гипотеза;
- mean PSNR regression ≤0.3 dB, ни один motion/HUD ROI не теряет >1 dB;
  temporal error не ухудшается >5%; отдельный просмотр артефактов;
- cuts/recovery и partial outputs не засчитываются как 3×;
- при провале хотя бы одного gate новый backend не становится default.

Architecture chosen; аппаратная эффективность, динамическое качество и итоговый
паритет — открытые гипотезы. Результаты первого прототипа добавляются рядом с
решением, включая отрицательные результаты и последующий пересмотр.

## Первый отрицательный результат — прототип 0.1

Компактный block-field вариант на 4 парах реальной bolt последовательности
384×216: mean PSNR-Y 43.864 против 46.071 у GPU LMC (−2.207 dB).
На 6 парах synthetic strafe 384×240: 31.534 против 32.722 (−1.188 dB).
Визуализация показывает раздвоение малого движущегося объекта. Простого
block-level confidence и соседних block vectors недостаточно вместо dense
visibility refinement. Вариант отклонён для default/native integration.
Следующий ablation сохраняет проверенные dense visibility/orphan этапы LMC,
отдельно проверяя необходимость обязательного global-model fit. Итоговые
решение и gates будут обновлены по сравнению всех сцен, не только этих двух.
