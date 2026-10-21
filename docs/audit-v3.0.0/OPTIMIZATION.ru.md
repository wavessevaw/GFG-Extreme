# Ускорение, качество и задержка при фиксированной стоимости кадра

Дополнение для основного агента к [аудиту](ANALYSIS.ru.md). Объект: GSF_Kedavra c264c28 в GFG3.0.0. Это план реализации и проверки, не результаты ускорения. Условия: не увеличивать измеренную GPU-стоимость полного конвейера, не ухудшать игру и физический pacing. Новых релизов не делать в рамках аудита.

## Что считать стоимостью

Измерять отдельно analysis/pair, reconstruction/output, post/output, composition, queue wait и source→flip latency. При x3 и30fps средняя загрузка FG за секунду =30×analysis +60×generation +90×post (плюс copy/прочие расходы). Среднее не заменяет p99 времени отдельного вывода. Уменьшение времени shader при увеличении queue wait — не улучшение.

Старый Deck microbench (не текущий HDR runtime): analysis4.7731ms, два outputs0.9907ms. Примерно83% этой суммы составляет анализ; крупный резерв — ME. Это ориентир приоритета, не обещание ускорения. Сначала устранить пропуск analysis в timestamps, иначе невозможно проверить условие «без роста стоимости».

## Конкретные изменения в порядке внедрения

| Приоритет | Изменение и место | За счёт чего оплачивается | Основной риск и gate |
|---|---|---|---|
| 1 | `kfg_select.comp`: согласовать score/refinement/repair | Использовать уже рассчитанные ошибки; убрать логически лишнюю работу, не добавлять full-screen pass | Проверить stairs, thin edges и обе x3-фазы |
| 2 | `kfg_warp.comp`: убрать обязательный blur из режима качества | На fast-motion пути исчезают 4 дополнительных bilinear taps/pixel | Ошибки flow становятся заметнее; сравнивать без маскирующего размытия |
| 3 | `kfg_me.comp`: adaptive finest refinement | Пропуск дорогого поиска на достоверных tiles; средства направить на сложные boundaries | Low SAD не гарантирует правильный flow на периодических текстурах |
| 4 | `kfg_select.comp`/`kfg_plan.h`: conditional repair и phase-common candidates | Меньше candidate evaluations/лишних repair rounds; общие данные пары не считать дважды | Visibility и позиции sampling зависят от t: результат G1 нельзя выдавать за G2 |
| 5 | `kfg.cpp`: completion-driven ранняя готовность пары | Использовать свободное окно для part2, не ждать обязательный следующий paint | Дополнительный GPU submit может вытеснить игру/следующий composite |
| 6 | `kfg_warp.comp`: visibility-aware reconstruction и edge-local clamp | Заменить текущие решения, использовать освобождённый blur/ME бюджет | Нельзя незаметно добавлять дорогие neighbourhood taps на все пиксели |

### 1. Исправить противоречие в confidence без новой текстуры/прохода

В `kfg_select.comp` финальный `.w` — `best_cost`, включающий consistency и preference penalties. Repair сравнивает собственный `nb[4].w` с `cost(c1,v)` соседей, то есть raw photometric cost без этих же штрафов. Из-за разных шкал сравнения решение может меняться не из-за более точного соответствия. Дополнительно subpixel refinement меняет `best`, но `best_raw/best_cost` остаются от исходной целочисленной позиции; confidence уже не относится точно к записанному вектору.

Реализация: явно разделить photometric residual и selection score в локальных переменных. Для repair сравнивать одну и ту же метрику всех кандидатов; для output confidence хранить согласованный residual. Для refined vector либо сделать одну проверку refined cost, либо отказаться от уточнения на плоской/недостоверной кривизне. Один добавленный cost вызов оплатить пропущенными evaluations на принятом seed; сначала попробовать вариант без новых fetch. Не выдавать предполагаемое улучшение качества за доказанный bugfix без A/B последовательностей.

**Тест:** искусственная сцена с двумя близкими кандидатами, один получает prior fee; verify одинаковая шкала при перестановке own/neighbor. Slow pan + диагонали/лестницы: temporal edge displacement и flicker, а не один PSNR. Static HUD должен оставаться exact.

### 2. Убрать маскирующий blur, сохранить резкость осмысленно

Текущий warp всегда добавляет blur при |v|>10 pixels/source frame. Он размывает generated outputs, но не обязательным образом real, создавая периодическое изменение детализации. Выключение снижает texture traffic только там, где выполнялась ветка blur; static сцены не ускорятся. Сделать явно выбираемый motion-blur effect вместо скрытой части interpolation.

Оставить sharp resampling на достоверных smooth-flow tiles. На неоднозначной границе выбирать видимую сторону, не увеличивать sharpening: sharpening усиливает двоение и ringing. Ограничение overshoot делать по уже доступным samples, если этого достаточно; отдельные min/max neighbourhood fetch требуют собственного бюджета. Для scRGB не обрезать физически допустимые отрицательные компоненты глобальным max(0).

**Тест:** temporal spectrum/contrast на real,G1,G2,real; тексты, тонкие провода, панорама и быстрый объект. Сравнить sharpness с baseline, не только среднюю ошибку. Не смешивать изменение blur с ME в одном коммите.

### 3. Тратить поиск там, где он нужен

ME уже имеет pyramid, bidirectional flow, temporal и camera seeds. Не добавлять их заново. Нужен ранний выход для хороших seeds и ограничение finest search на согласованных tiles. Условия early acceptance: низкий residual **и** forward/backward agreement **и** достаточная texture discrimination; на плоском фоне/повторяющейся решётке хорошее SAD недостаточно. Вблизи occlusion, границы векторов и после cut — полный baseline поиск.

Первый вариант — ветка внутри существующего dispatch, confidence из доступных данных, без отдельной classification texture. Проверить divergence/register pressure: уменьшение fetch не гарантирует уменьшения milliseconds. Только если branch вариант неэффективен, рассмотреть compact active tiles; учесть counter reset, indirect dispatch и barriers, иначе оптимизация создаст больше overhead, чем уберёт.

Бюджет качества: освобождённые evaluations направить на thin geometry/occlusion tiles, а не глобально увеличить radius. Если второй минимум почти равен первому — не считать вектор надёжным; second-best margin можно поддерживать при уже выполняемом переборе, но надо исключить почти одинаковые кандидаты. Не делать глобальную temporal smoothing: она даёт запаздывание на ускорении и ghost trails.

### 4. Сократить повторную работу, не сломав x3

`kfg_plan.h` всегда планирует select→repair→repair→warp на каждый generated output. Repair shader уже имеет early return для согласованных блоков: обещание «добавить early return» было бы повторением существующего кода. Следующий резерв — не запускать вторую repair round там, где первая ничего существенного не изменила, или оплачивать её только сложным tiles. Глобальное чтение counter на CPU запрещено: это stall. GPU changed mask/indirect dispatch может стоить дороже saved work на1280×800 — измерить.

Общий per-pair набор motion candidates и их признаки можно подготовить один раз. Но `cost(c1,v)` в select зависит от `u_t`; photometric cost/visibility для1/3 не равны cost/visibility для2/3. Нельзя просто кэшировать готовый G1 selection. Сначала переиспользовать только phase-independent candidate source/duplicates. Сейчас exact duplicate candidate suppression уже реализован; уменьшение radius/приближённая дедупликация — новая quality tradeoff, не бесплатное улучшение.

На motion boundaries ограничивать смешивание разных направлений. Существующий spread gate в warp уже есть. Улучшение: согласованная принадлежность foreground/background и видимость сторон вместо выбора только минимального photometric mismatch. Не averaging flow через силуэт. Hole pixels получать из видимого endpoint; для невидимого в обоих кадрах содержимого достоверной реконструкции без дополнительной информации не существует.

### 5. Уменьшить задержку: убрать искусственное ожидание, не переставлять кадры

Сейчас `OnPaint` объявляет pair usable на `nVBlank+2`, а анализ отправляется двумя частями после successive composites. При90Hz один vblank —11.111ms. Потенциал устранения **одного** такого ожидания — до11.111ms на подходящих парах; это верхняя оценка структурной задержки, не измеренный выигрыш input-to-photon.

Реализация по шагам:

1. Pair token `(sourceA, sourceB, epoch, completionValue)` и честное ready/deadline; отдельный timestamp source arrival, не только paint latch.
2. После текущего composite определить оставшееся окно до next output deadline, с запасом и p99 analysis, плюс учитывать конкуренцию игры. Если part1+part2 помещаются — отправить оба после текущего composite. Если нет — baseline split. Само время до vblank не равно гарантированному свободному GPU времени.
3. Scheduler использует фактическую readiness и монотонную content timeline. Нельзя внезапно показать G1 после B или уменьшить delay скачками каждый кадр. Изменение delay — контролируемая редкая коррекция с отметкой skipped.
4. Ограничить количество незавершённых pairs/output работ; не генерировать уже просроченную фазу ради красивого счётчика. Dropped phase видна в telemetry. Не терять нужные references при освобождении ring.
5. Фильтры/HUD/запись файлов не должны добавлять CPU wait в критическом пути. `WriteStatus` делает filesystem IO в OnPaint: при подтверждённых CPU stalls передавать snapshot в ограниченную mailbox для отдельного writer, без очереди исторических status. Не обещать GPU-выигрыш от этого.

Интерполяция A→B причинно требует B: нулевую задержку и точную промежуточную картинку одновременно обещать нельзя. Extrapolation может уменьшить lookahead, но увеличивает ошибки на новых объектах, ускорении и disocclusion; для текущего quality target это не основной путь. Не включать её скрыто в x3.

## Как принять «меньше артефактов без роста стоимости»

Сначала исправленный baseline с полной cost telemetry; тот же package/driver/resolution/refresh/TDP, одинаковый reproducible input, порядок A/B/A. Самостоятельные варианты по одному изменению, затем их совместная проверка. У каждого варианта должны быть:

- Не хуже full FG GPU p50/p95/p99 и физические missed-slot/p99 interval; game real FPS тоже не хуже. Не выбирать одну удачную сцену, скрыв худшую.
- Не больше source→display latency и pending depth. Если source timing отсутствует — latency unknown, не0.
- Меньше boundary ghost area/edge displacement/flicker на sequence ROI; static HUD unchanged, cut без blending, обе x3 фазы различимы и идут в правильном порядке.
- Режимы SDR/PQ/scRGB отдельно. Ровный PSNR на perceptual шкале не оправдывает неверное HDR filtering.
- Учёт неизвестности и повторяемости измерений: малые различия ниже шума не считать улучшением; фиксировать температуру/частоты, shader warmup и изменения мощности.

Минимальный набор сцен: slow subpixel pan; fast pan; rotating camera; independently moving foreground; disocclusion; repeating fence/stairs; thin wires/text; particles/transparency; cut/flash; freeze/resume. Дополнительно записанный игровой фрагмент с ground-truth temporal frames, если доступен. Не создавать новую бесконечную исследовательскую серию: выбирать изменение по устранённому механизму дефекта и одному заранее определённому gate.

## Что сделать первым основному агенту

Первый implementation PR: **полная стоимость + completion/display accounting**, без quality retuning. Второй: **согласованный residual/repair и optional blur**, с отдельными A/B результатами. Третий: **adaptive ME**, оплачивающий boundary quality тем же бюджетом. Четвёртый: **early-ready scheduling**, сохраняющий deadline safety и порядок real/G1/G2. Эти этапы не требуют смены архитектуры или нового публичного релиза до приёмки.

Статус: предложенные ускорения и улучшения качества не измерены на Deck автором аудита. Ветка содержит инженерный план для реализации; product code не изменялся.
