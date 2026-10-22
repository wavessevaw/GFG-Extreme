# GFG Extreme 3.0.0 — независимый аудит для основного агента

Аудит 2026-10-21 UTC. Только анализ и воспроизведения; реализация продукта не изменена, релизы и теги не создавались.

## Объект и происхождение

- GFG Extreme tag `v3.0.0`: `c0e71075790e504f25aff23ec337f627ac07dcb2`.
- Опубликованный `GFG-Extreme-v3_0_0.zip`: SHA256 `ef2fdb002503b84e50bfaef5b6ebddcf051b8d42a2f09e8ac68233ba391cb26e`, совпадает с опубликованным SHA256SUMS.txt.
- Движок: `wavessevaw/GSF_Kedavra@c264c2877a15d9b3739a346432a4fae9b8ef479d`; runtime/VERSION = `kedavra-c264c28`.
- GFG main на момент проверки: `3448a9b1f0c53953be409767744b1ba608d1286a`.
- ZIP отличается от тега: README EN/RU, build_release.sh и изображения. Исправление executable bits уже есть в `d2c048f`; не предлагать его повторно. Последующие `3ad1a5e` и `3b630e1` меняют полноту телеметрии и UI focus. Они не устраняют перечисленные ниже проблемы движка.
- Архитектура 3.x — интеграция в Gamescope, а не старый Vulkan layer из PR133. Исторические выводы про layer нельзя механически переносить.

Ссылки исходников: GFG https://github.com/wavessevaw/GFG-Extreme/tree/c0e71075790e504f25aff23ec337f627ac07dcb2 ; движок https://github.com/wavessevaw/GSF_Kedavra/tree/c264c2877a15d9b3739a346432a4fae9b8ef479d . Ниже пути `kedavra/...` относятся к отдельному репозиторию движка.

Подробный план ускорения, уменьшения артефактов и задержки при фиксированном GPU-бюджете: [OPTIMIZATION.ru.md](OPTIMIZATION.ru.md).

Полный разбор Governor/Autopilot/Pilot и эффективности управления: [GOVERNOR_AUTOPILOT.ru.md](GOVERNOR_AUTOPILOT.ru.md), с отдельными воспроизведениями.

## Главный вывод и архитектурное решение

Сохранить compositor-owned Vulkan pipeline: Gamescope имеет источник кадров, лимитер, композицию и KMS. Это более подходящая точка управления физическим выводом, чем инъекция в каждую игру. Не начинать очередную смену генератора. Сначала исправить связь «решение → выполненная GPU работа → фактический flip → телеметрия → управление мощностью». Сейчас эта цепочка частично подменена предположениями, поэтому улучшение отдельного shader time не гарантирует улучшения вывода.

Основной путь: реальный commit → GPU copy в кольцо из 6 кадров → luma pyramid → двунаправленный hierarchical block matching → camera/cut statistics → фазозависимый selection/repair → warp → post filters → Gamescope composition → DRM flip. Анализ пары разделён между двумя submissions после композиции. x3 использует фазы 1/3 и 2/3; дробные режимы заполняют интервалы между источниками.

Уверенность в выборе точки интеграции высокая. Уверенность в текущей приёмке 30→90 низкая: нет нового запуска именно GFG 3.0.0 на оборудовании; старые Deck-трассы движка не прошли все собственные gates. Новый runtime с bundled glibc требует отдельной SteamOS ABI/boot проверки.

## Приоритетные дефекты

### P1 — опубликованный пакет не содержит инструментов диагностики

**Воспроизведено на скачанном ZIP.** `py_modules/gfg_plugin/kedavra/ctl.py:166` запускает `bin/kfg_pacing.py`; `install.py:354` ожидает `bench/kfg_vktest` и SPIR-V. Их нет в ZIP вообще. Вызов analyze возвращает Python ENOENT, bench — `the plugin zip has no bench/kfg_vktest`. Запись CSV может работать, но её анализ и GPU benchmark не работают.

Причина: `.github/workflows/release.yml` собирает только gamescope-runtime; `scripts/build_release.sh` копирует только runtime. Unit tests используют фиктивные runner/files, пакет целиком не проверяется.

Исправить в build/package: включить pacing tool, ABI-совместимый benchmark, полный комплект shader dependencies; benchmark должен запускаться с подходящим loader/library path, а не просто быть скопирован. Добавить manifest/hash/source SHA и проверку **распакованного конечного ZIP**. Gates: analyze валидного CSV действительно создаёт JSON; benchmark действительно запускается и называет устройство; отсутствующий инструмент даёт понятную недоступность, не успешную диагностику.

### P1 — отсутствующие физические flip не входят в missed_fraction

**Воспроизведено.** `kedavra/tools/kfg_pacing.py:159` считает `repeat / number_of_rows`. Если экран 90 Hz получает flip раз в 22.222 ms, отсутствующие слоты не имеют строк. Проба 400 строк на 45 flip/s возвращает `missed_fraction=0`, `missed_below_0.5pct=true`. Важно: общий `pass=false`, поскольку interval-error gate отдельно ловит этот пример. Ошибка именно в величине и отдельном gate, не утверждение, что весь тест проходит.

В сохранённом `trace-run2-x3-manual.report.json` 9205 строк /168.06 s ≈54.77 записанных flip/s, однако missed=0.152%. Пропуски/исключённые сегменты требуют анализа исходного CSV; это иллюстрация несостоятельности текущего определения, а не точный пересчёт hardware drop rate.

Исправить: сегментировать по display/mode/epoch/явным исключениям; считать ожидаемые refresh slots по sequence/timestamp; отдельно отдавать missing flips, повторённый контент, trace loss и успешные уникальные outputs. Не выкидывать длинные паузы без явной причины/метки исключения. Проверить 45/90, burst drops, DPMS, refresh switch, gaps в записи. Сохранить старую метрику под честным именем repeat_row_fraction, пересчитать архивные отчёты без перезаписи оригиналов.

### P1 — pace для управления мощностью не измеряет физическую плавность

**Воспроизведено через настоящий live_for.** `kedavra/hud.py:216–230`: при flips=45, sources=30, real=30, gen=60, repeat=0 возвращает fps=45, но **pace=1.0**, gen_share=2/3. real/gen/repeat — решения scheduler, не подтверждённые KMS outputs. `pilot.py:170–187` признаёт точку хорошей по real>=95% cap и pace>=0.99; физический output fps в этом gate не используется. Поэтому игра может держать 30, а вывод — не держать 90, при этом контроллер будет считать cadence здоровым. Аналогичный риск у power optimizers, оценивающих в основном real FPS.

Исправить контракт: раздельные scheduled/submitted/completed/displayed counters; pace считать по KMS interval distribution и missing slots на фиксированном окне. Pilot/Governor/CPU split/GPU ceiling должны отвергать пробы с ухудшением физического вывода, неизвестной телеметрией, trace loss или ростом очереди. В `service.py:155` заменить `(pace or 1.0)` на явную обработку None: сейчас реальный 0 превращается в «не stuttering».

### P1 — готовность GPU анализа объявлена заранее, overload guard слепой

**Подтверждено кодом; GPU starvation на Deck в этом аудите не воспроизводился.** `kedavra/gamescope/src/kfg/kfg.cpp:1156–1162` при latch сразу вызывает `kfg_sched_on_me(..., nVBlank + 2, true, false)`. Это не completion event. Реальная отправка происходит позже в `SubmitAnalysis:1320–1339`. Единственный production вызов on_me всегда даёт success и ровно budget=2; scheduler механизм `me_late_hist/degrade_pending` не получает фактического опоздания/failure.

Одна Vulkan queue и barriers упорядочивают данные; из этого **не следует** доказанная гонка чтения неготовых изображений. Проблема: при перегрузке следующая композиция ждёт очередь и пропускает vblank, а scheduler считает анализ готовым. Модельный insufficient_compute тест подаёт реальные задержки модели и потому не доказывает этот production путь.

Исправить: pair ID + generation/epoch + completion timeline value; опрашивать завершение без блокировки критического paint path. Если pair не готов к deadline, держать корректный предыдущий output/реальный кадр и учитывать причину. Политику деградации привязать к фактическим completion/deadline/flip, не к фиксированному +2. Не добавлять CPU WaitIdle в render loop. Сначала deadline-aware admission на существующей queue; отдельная compute queue — только после измерений contention и полной схемы ownership/semaphores.

### P1 — GPU cost не включает анализ движения

**Подтверждено кодом.** Query timestamps в `kfg.cpp:1286–1315` охватывают RecordGenerate и post. Основной `analysisPlan` исполняется после этого в SubmitAnalysis без этих timestamps. `gpu_us_*` и `over_budget` обычно не включают pyramid/ME/stats. Если новый source пришёл до окончания отправки старого анализа, хвост внезапно включается в RecordGenerate (`1197–1202`), поэтому одинаковое поле имеет плавающий состав.

Исправить separate timestamp scopes: copy, analysis part1/part2, select/repair/warp на каждый output, filters, whole composition; pair lifetime/end-to-end queue delay отдельно. Отдавать скользящие p50/p95/p99, количество/возраст samples, clock validity, не только lifetime average. Бюджет: на каждое vblank 11.111 ms при90Hz, включая игру, очередь, композицию и запас; средняя стоимость пары /33.333 ms не доказывает попадание каждого output в слот.

### P1 — небезопасная для восстановления замена установленного runtime

**Воспроизведено fault injection на временном root.** `install.py:205–220`: после loader/version preflight удаляется runtime, затем ставится новая копия и выполняются setcap/systemctl. При ошибке setcap предыдущая рабочая VERSION уже потеряна, rollback copy отсутствует. Открытый inode бинарника не сохраняет удалённые по абсолютному пути dlopen dependencies и interpreter для новых запусков.

Исправить immutable version directories + last-known-good + атомарное переключение после проверки capabilities/unit, с учётом зашитого ELF interpreter/RUNPATH. Нельзя просто переименовать каталоги и считать bundled loader переезжающим автоматически. Rollback должен возвращать coherent binary+libraries, не только stock mount на следующем boot. Испытать fault injection copy/full disk/setcap/daemon-reload/enable и update при работающем compositor. Сейчас boot watchdog означает восстановление только после следующего reboot; это не полноценная transaction rollback.

### P1 — unsupported/отключённый HDR сохраняет FG-лимит игры

**Кодовый путь; требуется интеграционная проверка с Gamescope.** `kfg.cpp:979–995` SourceCapFPS/WantsEveryVBlank зависят от запрошенного multiplier. При неподдержанном layer0 `OnPaint:1083–1098` делает ResetHistory и return, но не меняет requested multiplier/эффективную eligibility. HDR при `kfg_hdr=0` становится unsupported; x3 всё ещё требует 30 cap на90Hz и принудительную композицию, хотя генерации нет. Аналогичный риск allocation_failed.

Исправить requested policy отдельно от effective policy/eligibility. При unsupported/alloc failure — реальный passthrough, снять именно FG-owned cap, сохранить пользовательский Steam limit; отдать reason. При восстановлении формата сделать warmup без колебаний. Gate: x3+HDR disabled, unsupported format, allocation failure, resize, HDR toggle должны сохранять запуск и честный вывод/лимитер.

### P2 — trace не связывает решение с конкретным DRM commit

`kfg.cpp:1343–1376`: решение кладётся в FIFO после Present, а OnPageFlip снимает первый элемент; `uSequence` игнорируется. Вызов SubmitAnalysis происходит ещё до добавления trace row. Нет commit cookie/framebuffer/display identity, нет классификации ring_miss/shader cut replacement как фактически real/repeat. Scene-cut shader возвращает endpoint (`kfg_warp.comp:54–60`), но scheduler получает cut=false и считает gen. При задержанном/постороннем flip или заполнении FIFO возможна неверная атрибуция; точное проявление race надо воспроизвести.

Исправить trace metadata связывать с DRM commit до его отправки; callback получает ровно этот объект. Учесть отказ commit, reset epoch, display ID, dropped trace records. Счётчик физического gen подтверждает и успешно выполненный warp, и представленную фазу, а не только намерение scheduler. KMS timestamp всё равно не доказывает оптическую уникальность пикселей; optical marker — отдельная проверка.

### P2 — цветовая реконструкция HDR и обязательный motion blur

`kfg_copy.comp` сохраняет encoding, `kfg_warp.comp:1–5,116–143` ресэмплирует и смешивает непосредственно PQ-коды; scRGB линейный, но не PQ. Это явно выбранная реализация, а не скрытая декодировка. Catmull-Rom и смешивание PQ не сохраняют световую энергию: сравнивать с линейным luminance oracle, не только perceptual PSNR против blend. Для scale: среднее PQ кодов 0 и1 даёт ~92 nit, физическое среднее 0 и10000 nit —5000 nit; не применять этот пример к exact-static/cut bypass, он про filtering/blend.

План качества: сохранить perceptual luma для motion search, отдельно линейный HDR reconstruction cache или decode taps перед weighted resampling с encode на выходе; измерить bandwidth/ALU, проверить metadata и gamut. Обязательный blur при |v|>10 pixels/frame может прятать ошибки и создавать чередование резких real/размытых gen; сделать независимый quality flag, по умолчанию оценивать без него. Не обещать выигрыш без одинаковых motion sequences/ROI и temporal flicker metrics.

### P2 — воспроизводимость и coverage выпуска

ZIP не соответствует исходному tag по части файлов; workflow_dispatch использует исходники ref запуска, хотя название выпуска задаётся inputs.tag. Текущий отличающийся код объясним исправлением сборки, но artifact provenance должен быть однозначным. `archlinux:latest` + pacman -Syu даёт неприкреплённый toolchain/syslibs; bundled glibc не гарантирует совместимость с host Mesa plugins, Wayland, Gamescope CLI и system session.

Исправить: immutable build commit, engine SHA, Gamescope SHA, контейнер digest, package manifest/SBOM и source archive, проверка, что ref сборки равен заявленному source. CI GFG запускает Python/sandbox/frontend и собирает Gamescope; не запускает `kedavra make test` как gate этого pinned engine и не проверяет extracted ZIP функционально. Добавить обе проверки. Существующие тесты полезны, но sandbox подаёт идеализированные статусы; это не «виртуальный Steam Deck», подтверждающий DRM/GPU/boot.

## Исторические аппаратные данные: что действительно имеется

В GSF_Kedavra `docs/kedavra/evidence/deck-20261021*/` есть импортированные Deck данные, не новые измерения автора аудита и не приёмка пакета GFG3.0.0.

- Старый bench: RADV VANGOGH/Mesa26-devel,1280×800; analysis 4.7731ms, two outputs0.9907ms. Finest ME2.3582ms, coarseME1.5516ms. Это конкретный старый microbench; новые HDR/filters/repair и нагрузка игры меняют картину.
- Auto `105329`: 75214 строк/839.929s ≈89.55 записанных flip/s; p99 interval error0.002617ms; repeat-row0.2686%; irregular content steps0.6439%; итог **false**. origin unlabelled, source latency неизвестна. Не переименовывать это в принятую сборку.
- Более ранний Auto `043758`: p99 error22.221383ms, irregular content14.11%, итогfalse.
- x3 manual `run2`: p99 error22.223383ms, irregular content24.39%, итогfalse.

Сохранённые отчёты не устанавливают throughput текущего HDR runtime и отсутствие накопления latency. Требуются единая версия code+package, exact trace provenance, скорректированный анализатор и данные о фактических outputs. Нового Deck endpoint/GPU здесь нет; hardware acceptance не проводилась.

## Оптимизация по ожидаемой отдаче

1. **Сначала измерения/сроки.** Timestamp весь pipeline и deadline misses. Самая дорогая операция по старому bench — ME (~4.50ms из4.77ms анализа), а не Python/HUD. Устранить непредсказуемое вливание хвоста анализа в следующую композицию. Сравнивать p99 физического output и queue delay под игрой, не idle average.
2. **ME conditional refinement.** Сохранить coarse/temporal/camera seeds; уточнять finest level только в tiles с ошибкой/low confidence/occlusion. Не отключать поиск для движущихся текстур, частиц, HUD boundaries по одному low SAD. Сначала classifier stats, потом compact work lists/indirect dispatch. Измерять overhead compaction и divergent occupancy на RDNA2.
3. **Перенос повторной работы в per-pair cache.** Pyramid/flow/stats общие для G1/G2 уже есть — не продавать это как новый выигрыш. Проверить разделение phase-independent candidate/consistency данных и phase-dependent selection; не использовать поле G1 как готовое поле G2 у occlusions. Сохранить separate phase tests.
4. **Bandwidth/память.** При1280×800 только 6 color frames+2 outputs: SDR31.25MiB, HDR62.5MiB, без flow/luma/post. Оценить minimum ring по реальным live pair dependencies прежде сокращения; query slots/epochs важнее угадывания размера. Рассмотреть reuse pyramid для уже скопированного кадра, fused cheap reductions, исключение лишней full-screen post при пустом фильтре. Не объединять проходы ценой увеличения worst dispatch latency.
5. **Warp и filters.** Сравнить 5-tap sharp с bilinear по temporal ROI, ограничить expensive boundary search confidence mask, отключить незаказанный blur. Cheap CAS возможно объединить с финальной композиционной стадией; SMAA требует зависимых проходов. Filters идут на90 outputs/s и должны входить в power governor budget.
6. **Энергия.** A/B/A контролировать не только real FPS и watts, но unique displayed FPS, p99, latency, temperature, confidence. Снижение base до24 увеличивает межкадровое движение/интерполяционную задержку и долю синтетики; «Battery x3.75» не универсальный sweet spot. Измерить J/unique displayed frame плюс J/second при фиксированном качестве.

Отдельная compute queue или новая архитектура допустима только если измерения покажут, что same-queue admission нельзя уложить без ущерба игре. Это не бесплатный параллелизм: общий GPU, memory bandwidth и приоритеты остаются общими.

## План продолжения для основного агента

1. Packaging + provenance + exact-ZIP smoke; transactional runtime update с failure tests. Не менять старый release asset молча.
2. В движке: pair completion и actual display accounting; corrected pacing analyzer и пересчёт архивов. Связать readiness, degradation, HDR fallback с effective cap. Regression suite воспроизводит пять дефектов из приложенного JSON.
3. Full-cost queries + детерминированные stall/failure интеграционные проверки, включая ×2/×3/24→90, mode/format/focus/suspend transitions. Sanity: отсутствие данных — unknown, не healthy.
4. Только затем ME/bandwidth/warp оптимизации, отдельными изменениями с одинаковыми inputs и quality/latency gates.
5. Hardware приёмка именно окончательного ZIP: startup/rollback на SteamOS, locked30→90 с source IDs и output phases, corrected KMS gaps/p99 и duration, optical uniqueness где нужна, game-under-load cost/power. Отдельно HDR/scRGB/filters и boot/update recovery. До этого не называть продукт принятым.

Приоритет реализации: инженер GFG — package/install/pilot/CI; инженер GSF — completion/timing/DRM trace/fallback/analysis. Менять status schema согласованно и versioned, с fail-closed interpretation старых данных. Это разделение задач, не запрос пользователю выбирать архитектуру.

## Выполненные проверки и воспроизведение

- GFG tag: `python3 -m unittest discover -s tests -p 'test_*.py'`: **88 tests OK**, 6.671s.
- `python3 -m sandbox.run`: **29 сценариев PASS**, [отчёт](evidence/SANDBOX_REPORT.md). Это модели policy/power, не SteamOS.
- Pinned Kedavra: сборка всех standalone shaders/engine и `make test`: scheduler/auto ASan+UBSan, сценарии с seeds=3, Vulkan interpolation HDR/SDR и postprocessing — **exit0, 0 failures**; [полный лог](evidence/engine-tests.log). Vulkan ICD: lavapipe; никаких чисел скорости этого запуска не использовать как Deck benchmark.
- [Негативные воспроизведения](evidence/reproductions.json) и [скрипт](reproduce.py): отсутствующие инструменты, 45/90 missed gate, неверный pace, failure atomicity installer. Скрипт ничего не устанавливает в систему; installer проверяется с FakeSystem во временном каталоге.
- Gamescope/KMS/boot/capability и физический90FPS в этой среде не проверялись: `/dev/dri` отсутствует, Deck endpoint не настроен. Полная сборка Gamescope в этом аудите не запускалась; проверен standalone engine и исходный integration path.

Для воспроизведения подготовить каталог AUDIT: `source/` = git archive GFG v3.0.0; `kedavra/` = checkout GSF_Kedavra c264c28; `package/` = распакованный проверенный release ZIP. Запустить `python3 reproduce.py AUDIT`. Результат AUDIT/reproductions.json. Выполнение встроенных фиктивных installer tests не требует root.

Статус передачи: отчёт и доказательства предназначены основному агенту. Исправления продукта здесь не внесены; рекомендации с кодовым обоснованием и воспроизведённые дефекты отмечены отдельно. Никаких release/tag/workflow_dispatch операций.

Практическая перепроверка: [Governor 2.0](../governor2/CONCEPT.ru.md) и [исправления с red/green тестами](../governor2/IMPLEMENTATION.ru.md).
