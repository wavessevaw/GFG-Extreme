# GFG Shared Flow — вычислительный прототип

Основное решение: [Architecture Decision 1.0](ARCHITECTURE_DECISION_1_0.md).
GSF (`te-bench --algo gsf`) использует coarse-to-fine двунаправленное движение,
один robust affine candidate, сохранённую dominant-motion palette, dense visibility
и bounded orphan refinement. Общий анализ пары выполняется один раз; выходы
`t=1/3` и `t=2/3` реконструируются отдельно. Это offscreen prototype, не prerelease.
В native layer алгоритм не выбран и не включён в default.

## Что проверяется

- Одни и те же input arrays и held-out targets для GPU LMC tier0 и GSF.
- Synthetic reference: собственный renderer, 90 Hz, stride3, 1280×800.
  Отдельные окна: strafe, objects, fast turn, HUD update, post-cut, crossing cut.
  Первые пять окон по 40 кадров, последнее — 11. Это не запись коммерческой игры.
- Реальные camera clips Intel IoT DevKit `sample-videos`, CC-BY-4.0:
  `bolt-multi-size-detection.mp4`, `worker-zone-detection.mp4`.
  Их native rate — 60000/1001 Hz; stride3 означает 19.98→59.94, не 30→90.
  Окна от 5 и 10 секунд, decode/scale Lanczos в 384×216, 31 и 61 кадр.
- Quality run: GPU execution с Vulkan validation и download, PSNR-Y/SSIM-Y,
  temporal error, motion ROI, moving-edge ROI, HUD rectangles, endpoint duplicates.
  Motion ROI берётся из разницы endpoint/target >5 RGB levels; это только oracle
  для оценки качества, не скрытая информация для runtime алгоритма.
- Sharing ablation: тот же source stride/history, но только один выход.
  Первый выход должен совпасть побитно с первым выходом FG3 на каждой паре.
  Это проверяет корректность переиспользования анализа, не скорость дисплея.
- Timing: отдельные `--no-download` запуски, порядок методов меняется между
  повторениями. Из каждого контекста убирается только первая пара; raw первая
  пара сохраняется. Median/p95 берутся из оставшихся пар, не из средних проходов.
  Измеряются analysis, S1, S2, first/pair-ready GPU timestamp spans, CPU submit/wait.
- Upload GPU copy расположен до analysis timestamp; CPU copies и output readback
  не входят в no-download compute interval. Поэтому это не полная end-to-end цена.
  Pair-ready включает межпроходные/межвыходные queue gaps и малую telemetry copy.
  Сумма медиан отдельных проходов не обязана равняться медиане общего span.
- `allocation_bytes` — сумма реально запрошенных Vulkan allocations контекста,
  включая host staging. Это не измерение полного VRAM residency: driver/pipelines,
  игра и Gamescope сюда не входят. У выбранного GSF память не меньше GPU LMC.

## Отрицательные результаты и пересмотр

| Контрольное упрощение | Наблюдение | Вывод |
|---|---|---|
| Compact block field / собственная компактная реконструкция | bolt −2.207 dB; synthetic small strafe −1.188 dB; видимое раздвоение малого объекта | Не заменяет dense visibility |
| Dense visibility без fit и palette | small post-cut −0.492 dB | Удаление всей глобальной информации не обосновано |
| Dense + один affine, без palette | native strafe −1.670 dB | Малые сцены скрывали полезность global hypotheses; нельзя квалифицировать 1280×800 по 384 px |
| Dense + affine + palette (выбранный GSF) | первый native probe 32.093 dB против 31.914 у LMC | Palette возвращена; нужны остальные сцены и cost gates |

Предыдущий `scene cut` segment начинался **после** cut и не проверял сам переход.
В новом корпусе crossing cut выделен отдельно. Дубликаты при recovery не считаются
двумя успешными synthetic кадрами. Detector — эвристика, а не гарантия обнаружения
любых монтажных склеек; ложные срабатывания и пропуски требуют отдельного учёта.

Новый тест независимого noise cut сначала провалился: coarse luma сгладила шум,
поэтому порог её matching cost не обнаружил смену сцены. Исправление считает
полноразмерный RGB residual после компенсации движения блока. Cut vote: более
75% блоков имеют mean RGB residual >0.15. На cut выводятся ближайшие endpoints;
предыдущий cut запрещает temporal predictor следующей пары. No-cut bit-exact
и выход из recovery проверяются тестом, не предполагаются.

Fresh VVL также выявил ArrayStride на Function array `seen[4]`, когда shader стал
читать globals. glslang 15.2.0 объединил его тип с SSBO palette[4]. Локальный массив
расширен до пяти элементов (используются четыре), чтобы разделить типы. Validation
не отключалась. Ранее использован такой же обход для двух Workgroup arrays.

## Воспроизведение

Нужны Vulkan 1.2 compute/timeline, glslangValidator, spirv-val, C11 compiler,
make, ffmpeg/ffprobe; Python numpy, Pillow, moderngl, scikit-image. Для software
сравнения выбрать Mesa lavapipe ICD и Khronos validation; при сравнении методов
не запускать параллельно renderer, сборку и другие CPU/GPU workloads.

```sh
make -C engine/gfg-temporal all lib
python3 tools/temporal_bench/prepare_shared_flow_corpus.py --out /tmp/gsf-corpus
python3 tools/temporal_bench/compare_shared_flow.py \
  --bench engine/gfg-temporal/build/te-bench \
  --sequence /tmp/gsf-corpus/target-strafe \
  --sequence /tmp/gsf-corpus/target-objects \
  --sequence /tmp/gsf-corpus/target-fastturn \
  --sequence /tmp/gsf-corpus/target-hud \
  --sequence /tmp/gsf-corpus/target-postcut \
  --sequence /tmp/gsf-corpus/target-crosscut \
  --sequence /tmp/gsf-corpus/bolt-small \
  --sequence /tmp/gsf-corpus/worker-small \
  --algorithms lmc-gpu,gsf --pairs 12 --timing-repeats 3 \
  --check-sharing --work /tmp/gsf-results
GFG_TEST_SHARED_FLOW=3 engine/gfg-temporal/build/te-tests
```

Camera revision и SHA-256 clips/license зафиксированы в preparer. Manifest сохраняет
полные hashes и metadata каждого input; comparison — commit, code diff hash,
binary hash, input/output hashes и raw command logs. `--reuse` использует имеющиеся
arrays и заново сохраняет их hashes. Renderer зависит от Mesa/font versions:
другой драйвер не обязан дать побитно тот же корпус; оба метода обязаны получать
**одинаковые локальные arrays**. В repository не включаются большие videos/NPY.

## Границы результата

Cloud device — llvmpipe (LLVM 19.1.7), четыре CPU worker threads. Это не RADV APU
Steam Deck. Даже уменьшение software timestamp span не доказывает экономию Deck
power или достижение p95 ≤6 ms. Первый shader JIT тоже сохранён отдельно:
первоначальный compact cold probe занимал около 17 секунд; steady-state timing
не описывает стартовую готовность.

Латентность двукадровой интерполяции требует будущего настоящего кадра: около
одного source interval lookahead (33.333 ms при 30 FPS) плюс readiness и display
margin. Здесь измеряется вычислительная готовность; input-to-photon, contention
с игрой, HDR/PQ dynamic quality и physical 90 Hz не измерены. Новый prerelease
не публикуется, пока аппаратная приёмка отсутствует.

## Состояние проверки

Source checkpoint `75ca946` опубликован в ветках `codex/fg3-integration` и
`claude/native-gpu-bridge` (PR #133). Выбранный GSF: 182 native compute checks,
0 failures с fresh VVL, включая static exactness, timeline, hold/discontinuity,
pan/HUD и cut recovery. Расширенное сравнительное измерение сохраняется до
решения о native integration. Порог ускорения 15% не понижается по результату.
