# Governor / Autopilot / Pilot: аудит управления и эффективности

Продолжение [аудита GFG3.0.0](ANALYSIS.ru.md). Разобраны production wiring Service, Autopilot, PointPilot, PowerGovernor, PolicyCoordinator, Power Split, GPU clock control, actuator, GameModelStore, SessionStats и взаимодействие с Kedavra Auto. Исходники GFG — tag c0e7107; engine c264c28. Это анализ и воспроизведения, не патч контроллера и не аппаратные замеры.

## Решение

Сохранить разделение policy/actuator и контроллеры с явными состояниями. Добавить **одного владельца эксперимента** и единый контракт пригодности измерений. Главная проблема сейчас — разные блоки считают «здоровье», завершение пробы и достаточность данных по разным правилам. Оптимизировать пороги до устранения этих противоречий преждевременно.

Цель Balanced/Battery: уменьшать фактическую энергию при соблюдении реального FPS, физического output pacing, latency и заданного качества. Уменьшение установленного TDP само по себе не доказывает экономию; увеличение GPU MHz/W не доказывает полезную работу. Quality должен сохранять заявленную пользовательскую мощность после временного thermal ограничения, если нет другой явно выбранной политики.

## Как система устроена сейчас

| Блок | Решение | Частота/окно | Источник информации |
|---|---|---|---|
| Autopilot | objective: Quality/Balanced/Battery | tick около1s, dwell60s | preference, питание, charge20/25%, temperature85°C |
| Kedavra Auto | source cap по лестнице | vblank, окно около1s | интервалы latch и число source frames |
| PointPilot | measure→locked→guard→trial | stable12s; measure≤45s; guard5s; trial6s | cap Auto, real FPS, pace, policy confirmed, at_ceiling |
| Governor | TDP вниз1W / вверх2W; severe→ceiling | окно10s, settle2s | real/cap, pace, over_budget, ring_miss, temp |
| Power Split | ступени CPU max + A/B/A | trial10s; A/B окна8s | real, busiest core, GPU busy/clock, APU draw |
| GPU clock | manual-clock step−100MHz | observe20s, settle5s, verify20s | real, CPU/GPU busy, draw |
| PolicyCoordinator | применение convars/revision | tick; timeout3s/backoff | свежий engine echo |
| Actuator | PPT запись/readback/ownership/restore | по запросу | hwmon и SteamOSManager |

В90Hz Auto/Pilot использует24/30/35/40/45fps. Battery сразу выбирает24, Quality/Balanced стремятся вверх; explicit x2/x3/custom не меняются Pilot. В `autopilot.py` остались docstring/helper `engine_request` с Battery30: фактический Service вызывает PointPilot. Обновить документацию и убрать неиспользуемый альтернативный policy helper, чтобы следующий агент не исправлял неактивный код.

Полезное сохранить: подтверждение policy revision, fast/slow PPT readback, ownership при внешнем изменении, bounded ladder, asymmetric up/down, backoff после неудачной пробы, CPU A/B/A с контролем дрейфа. Нельзя терять эти свойства при переработке.

## Подтверждённые проблемы

Файлы ниже — `py_modules/gfg_plugin/`, если не сказано иначе. JSON с результатами: [governor-probes.json](evidence/governor-probes.json). Скрипт использует настоящий controller code, фиктивные actuators и sandbox; никаких системных записей на Deck.

### P1. Thermal recovery может застрять на минимальном TDP

`governor.py:201–211,242–279`. После98°C ставится thermal ceiling4W. Если затем70°C и `hold_ceiling=True`, ранний return не даёт дойти до ветки снятия thermal ceiling. Воспроизведение:35 следующих ticks — всё ещё4W и thermal ceiling4W, хотя Pilot просит full-power measurement.

Отдельный случай Quality: при охлаждении thermal ceiling снимается, но успешное окно сразу возвращает из `_decide` для Quality. Возврата к пользовательскому15W нет. В пробе, где real30 удерживается и на4W, через35s Quality остаётся4W, thermal ceiling ужеNone. Это несоответствие обещанию режима, даже если конкретная лёгкая сцена не теряет FPS.

**Исправление:** отдельная thermal state machine normal/hot/critical/recovering до веток hold/no-cap; снять ограничение только после устойчивого охлаждения, затем плавно вернуться к допустимой policy target. Не ждать неуспешного FPS окна для восстановления Quality. При неизвестном sensor не объявлять охлаждение. Не менять safety thresholds наугад; аппаратный SteamOS thermal management остаётся независимым.

### P1. Governor не замораживает TDP во время CPU/GPU экспериментов

`service.py:96–140`: settling передаётся Pilot, но отсутствует в Governor sample. `epoch` перезапускает окно только при изменении cap; он не запрещает следующий10s TDP probe во время20s GPU verify/A-B-A. `settled()` смотрит на последнее verdict и время последней TDP записи, а не на действующий transaction owner.

**Воспроизведено на Service с injected active split interface:** `split.settling()=True`, за15ticks TDP12→11W. Это доказательство отсутствия арбитража в wiring; не утверждение, что каждый реальный CPU probe обязательно конфликтует. Настоящий PowerSplit замечает часть таких изменений и abort A/B, GPU controller при not-steady восстанавливает clock: данные могут теряться, изменения отменяться и повторяться вместо сходимости.

**Исправление:** transaction lease `(owner, epoch, baseline, deadline, restore_state)`; одновременно изменяется только одна координата: base cap, TDP, CPU cap или GPU clock. Во время lease остальные прекращают optimization steps, но safety/thermal/ручное управление имеют право отменить probe с причиной. Удерживать фиксированный TDP на всем A/B/A; после restore — quarantine/settle, затем новый epoch. Lease bounded и отменяется при stale/focus/mode change. Простого флага «последнее изменение было давно» недостаточно.

### P1. Точка принимается без достаточных и свежих измерений

`governor.healthy:41–63`: missing pace допускается, missing over_budget/ring_miss превращается в0. `tick:228–240`: время окна достаточно, число свежих samples/coverage не проверяется. Два samples с разницей10s приводят к step-down15→14W. Среднее29.7fps из9×30+1×27 признаётся healthy при cap30; это допустимость конкретного порога, но она скрывает краткие заметные просадки и не доказывает smoothness.

`gpu_clock_control.py:138–166`: `_judge` не требует minimum coverage; по одному real30/draw9 sample против baseline10 можно принять GPU step. Проба вызывает `_judge` напрямую для проверки отсутствующего gate; в production она достижима после прошедших20s с редкими valid samples. Baseline тоже может быть набран при меняющейся нагрузке, поскольку buffers не разделены на непрерывные valid segments.

**Исправление:** timestamp/sample ID/epoch + valid coverage и max consecutive gap. Окна time-weighted, одинаковые sensor intervals не считать независимыми: HostSensors кэширует значения2s. Unknown для обязательных physical pacing/GPU-completion метрик запрещает probe-down/commit, но не emergency rollback. Учесть finite/range validation. Добавить short-window tail gate и burst miss gate, а не только1s FPS average.

### P1. Pilot фиксирует cap по устаревшему Auto значению

`pilot.py:_measure` добавляет caps только при confirmed, но затем проверяет старый deque независимо от текущей пригодности. `stable_from` отсчитывается от прошлой записи до now; отсутствие новых данных выглядит как стабильность. Воспроизведение: один confirmed cap45, затем13s без подтверждения/real/engine — phase становится locked45 с текстом «measured: the game holds45fps».

**Исправление:** стабильность означает непрерывную последовательность новых подтверждённых samples, а не отсутствие изменений; при stale/unconfirmed/menu/gap invalidate segment и не увеличивать stable duration. Deadline45s должен приводить к unknown/degraded policy, не «измеренной» точке. Если fallback нужен, явно отметить его estimated и не использовать для learning/экономии. При QAM сохранять выбранную точку, но приостанавливать её измерение.

### P1. Ошибка restore забывается при завершении сессии

`governor.py:106–112`: `stop()` всегда `_reset_session()`, даже если actuator.restore_if_owned вернул failure. На следующей сессии новый claim может сохранить пониженный TDP как пользовательский исходный. Fault injection:15→10W, transient restore failure, новая игра — initial=10W, предыдущие15W забыты контроллером. Probe с FakeActuator; production `_claim` также перезаписывает initial, если `_keep_initial` не установлен, а обычная ошибка restore этот флаг не устанавливает.

**Исправление:** persistent restore-pending с сохранённым original и ownership evidence; блокировать новый claim до успешного restore или доказанного внешнего изменения. Retry ограниченный, не перетирать пользовательский override. В unload закрыть actuator для новых запросов и дождаться pending tick. Сейчас `plugin._unload` отменяет task с `to_thread`, что само по себе не останавливает работающий поток; Service.stop не использует `actuator.shutdown()`. Последнее — кодовый concurrency риск, interleaving в этом аудите не воспроизводился.

### P1. Saved energy вычисляется из лимита, не из baseline потребления

`session_stats.py:84–98`: saved_wh=(reference_TDP−measured_draw)×duration. При неизменных15W cap и8W draw за60s выдаёт0.12Wh «экономии». Это headroom относительно лимита, который мог никогда не потребляться без GFG. Воспроизведено без единого изменения TDP. Нулевые FPS также отбрасываются условием `value>0`, завышая средние; stutter в Service использует `(pace or1.0)`, превращая pace0 в отсутствие stutter.

**Исправление:** назвать cap difference «снижение лимита», удалить causal saved_wh без matched measured baseline. Измерять APU joules отдельно от всей батареи, интегрировать только covered duration. Battery_minutes_gained допустимо только с доказанной saving estimate и coverage; сейчас Service не передаёт battery_w в SessionStats, так что поле обычно вообще не вычисляется. Нули FPS валидны, None означает unknown; отдельные total/game/observed/unknown seconds. Baseline invalidation при сцене/яркости/AC/refresh/thermal change.

### P2. Краткий нагрев вызывает качание objective при smoothness

`autopilot.py:56–65`: fixed preference всегда urgent, поэтому dwell60s не действует. Последовательность84.9/85.1/84.9/85.1°C при smoothness выдаёт Quality/Balanced/Quality/Balanced по одномуtick. Каждая смена может перезапускать окна/менять TDP. `auto` имеет dwell, но отдельного thermal recovery hysteresis нет.

**Исправление:** urgency относится к смене настройки пользователем и входу в опасный thermal state, а не к каждому tick fixed preference. Отдельные enter/exit thresholds, minimum cool duration, явная reason при удержании. Charger disconnect/charge20% должны иметь определённый приоритет, не случайно ждать предыдущий dwell; это продуктовая политика, её выбрать и зафиксировать, не менять скрыто.

### P2. Реакция на severe FPS drop не мгновенная

`governor.py:230–268` severe рассматривается после10s окна. После начала real=0 в fixture возврат10→15W занял8s; задержка зависит от положения в окне. Комментарий «at once» описывает действие после verdict, а не скорость обнаружения. CPU/GPU guards тоже используют сглаживание; это надо учитывать в общих SLA.

**Исправление:** отдельный быстрый guard по нескольким новым samples/source deadlines; сперва rollback последнего собственного изменения, а не безусловно максимум мощности при любом сбое. Для ring_miss/engine error/source starvation повышение TDP может не помочь. Long-window optimizer остаётся медленным. Испытать load screen/menu: отсутствие source без workload не должно вызывать гонку за full power.

### P2. Failure floor и warm-start память имеют неверный срок/контекст

`governor.py:131–134` загружает `(tdp,age,count)`, но игнорирует age/count; локальный floor_fail вообще без expiry. Проба: floor13W, прошло4000s, Balanced всё ещё блокирует снижение ниже15W. GameModelStore имеет TTL1800s, но текущая сессия его не применяет. `floor_hot` имеет временное ограничение для floor, однако `again` использует сохранённый tdp без проверки срока — старый эпизод может изменить классификацию следующей просадки.

Service key=`app|refresh`; learned cap добавляется, но отсутствуют resolution/HDR/filter preset/engine build/power topology. Policy epoch меняется только для multiplier/base/auto_floor; HDR/post меняют cost, но не epoch. Warm-start может переносить устаревшее состояние. Floor не должен пожизненно блокировать экономию после тяжёлой сцены; успешный новый режим должен supersede соответствующий failure.

**Исправление:** monotonic expiry с переносом оставшегося TTL из persisted age, decay и bounded re-probe. Контекст fingerprint: app,refresh,resolution,transfer,FG quality/filter cost tier,engine schema и active CPU/GPU constraints. Не создавать ключ на каждую случайную sensor величину. Warm-start считать prior с запасом и быстрым guard, не доказанным optimum; один confirmation недостаточен для агрессивной стартовой экономии.

### P2. Оценка Power Split может награждать лишний GPU boost

`power_split.py:281–314`: benefit=`GPU MHz / APU draw`; реальные FPS должны удерживаться, но увеличение clocks при тех же полезных кадрах может трактоваться как gain даже без экономии joules. CPU-bound inference по busy% также не видит отдельную стоимость FG/композиции. GPU ceiling включает SteamOS manual clock; это не обязательно «только верхняя граница DVFS» и может мешать idle экономии. Точный hardware эффект требует замера.

**Исправление:** MHz/busy использовать как predictor eligibility, verdict строить по measured energy на сопоставимой useful throughput и latency. CPU A/B/A уже лучше single A/B — сохранить matched checks, заменить primary objective. GPU trial тоже A/B/A или эквивалентная matched baseline, достаточная coverage, confidence interval на независимых парных окнах; не принимать выигрыш0.3W по одному окну при шуме питания. Guard должен учитывать physical pacing и compositor queue даже когда real30 сохраняется.

## Что исправить в общей стратегии

### Один управляющий цикл с разными временными масштабами

1. **Safety/ownership:** ручное изменение, restore pending, device lost, thermal emergency отменяют active experiment и ставят безопасный action. Нельзя использовать optimization dwell для задержки защиты.
2. **Validity/epoch:** snapshot всех engine/sensor полей одного контекста; оценка fresh/unknown/menu/transient. Не обновлять обучение по невалидным данным.
3. **Fast performance guard:** actual output deadlines/real deficit и rolling latency. При собственной недавней пробе rollback; иначе классифицировать source-vs-FG-vs-display проблему.
4. **Pilot:** меняет operating point только на подтверждённых измерениях, просит explicit lease full-power и ждёт actuator readback/settle. Thermal ceiling и пользовательский limit могут сделать trial невозможным — результат limited, не «игра не тянет».
5. **Governor:** медленный поиск TDP при фиксированных cap/CPU/GPU/filters; границы последнего held и failed. После найденной области — поддержание с hysteresis, bounded periodic re-probe.
6. **CPU/GPU refinement:** только после устойчивой точки, lease фиксирует TDP на весь эксперимент. После успешного clock изменения заново оптимизировать TDP уже в новом контексте, не одновременно.

Ввести statuses `observing`, `measuring`, `settling`, `stable`, `limited`, `unknown`, `restore-pending`, `user-owned` с конкретной причиной. UI должен объяснять «не хватает данных»/«ограничено температурой», а не обозначать всё healthy/confirmed. Policy confirmation подтверждает значения convars, не физическую способность держать90FPS.

### Экономичнее искать и меньше мешать игре

- Не делать полный15→4W staircase на каждую сессию: использовать validated prior+margin и bracket held/failed, но большие шаги только при подтверждённом запасе. Точное число watts определить реальными trial curves, не обещать заранее.
- Прекращать search, если уменьшение cap не меняет measured draw или marginal saving ниже шума; дальнейшие пробы расходуют время/энергию и могут портить pacing.
- Bound exploration: максимум времени/числа writes за интервал и минимальное удержание после успеха. Долгие стабильные периоды не должны бесконечно A/B переключать clock.
- Energy break-even: `probe_energy_cost / expected_saving_w`; если оставшаяся предполагаемая сессия короче, эксперимент не окупится. Без надёжного прогноза duration использовать консервативный probe budget, не выдумывать остаток игры.
- Для fixed30→90 приоритет именно physical90 и latency; увеличение x3→x3.75 не считать бесплатной экономией. Battery24 увеличивает spacing источников и качество/latency tradeoff. При отсутствии доказанной экономии фиксированный lowest cap — policy preference, не оптимум.
- Balanced: выбирать точку по Pareto frontier `(measured watts, real FPS, output p99, latency, quality)` с явно закреплёнными ограничениями; не обязательно всегда наивысший cap, если +5fps резко увеличивает draw без полезного выигрыша для выбранной цели.
- Состояния charging/external power различать: подключённый слабый адаптер может не покрывать нагрузку. Для прогноза времени использовать батарейный discharge, покрытие и smoothed trend, а не разность TDP caps.
- Контроллер остаётся вне render critical path. Собирать hwmon данные пакетно с timestamps; не плодить polling/subprocess ради каждого property. Не терять существующий кеш датчиков, но учитывать его actual cadence в confidence.

## План реализации и критерии приёмки

| Этап | Изменение | Проверка, которая должна падать до исправления |
|---|---|---|
| G1 | Thermal recovery + restore lifecycle | critical→cool+hold, critical→cool+Quality, restore failure→next game/unload |
| G2 | Validity/coverage/epoch | stale Auto cannot lock; sparse20s GPU trial cannot pass; unknown pacing cannot lower TDP |
| G3 | Experiment arbiter | fixed TDP во всём CPU/GPU A/B/A; emergency отменяет lease и сохраняет restore intent |
| G4 | Honest statistics | untouched cap/draw не создаёт claimed energy saving; real/output0 входят в среднее |
| G5 | Memory/fast guard | expiry действует внутри long session; повторный старый thermal/floor не блокирует восстановление; bounded severe recovery |
| G6 | Efficient constrained search | меньше probe writes/energy при не худших actual pacing,latency и measured draw на повторяемых сценариях |

Дополнительные transitions: menu/open/close, suspend/resume, game switch, clock external override, sensor missing/NaN/future timestamp, repeated engine status, partial PPT write, late manager completion, thermal decline во время trial, toggles HDR/filter, charger changes. Окна warmup/transitions учитывать отдельно, не исключать из пользовательской статистики молча.

Hardware A/B/A должен фиксировать точный ZIP/engine/SteamOS/driver, temps/clocks, battery versus APU power, actual source and display counters. Модели полезны для state-machine invariants; нельзя из формулы sandbox, где watts растут монотонно с FPS, вывести реальную оптимальность24fps или экономию в Wh. Нового аппаратного измерения здесь не проводилось.

## Доказательства и передача

- [governor_probes.py](governor_probes.py): `python3 governor_probes.py /path/to/extracted-GFG-v3.0.0-source`. Нужны source `py_modules`, `tests`, `sandbox`, а не stripped release ZIP.
- [governor-probes.json](evidence/governor-probes.json):13 диагностических случаев. Прямой вызов private method отмечен в скрипте; test doubles не выдаются за аппаратный тест.
- Приоритет основному агенту: G1–G4 до настройки порогов и демонстрации «экономии». Затем G5/G6 совместно с исправлением GPU/display метрик из основного аудита.

Код продукта не менялся. Релизы/теги не создавались. Все предложения требуют реализации и проверки; подтверждённые воспроизведениями результаты относятся только к указанному исходному snapshot.
