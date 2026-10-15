# GFG Native FG 3× — GPU implementation

**Статус: НЕ ЗАВЕРШЕНА. Внутренняя разработка, не RC.** Приёмка A–F на Steam Deck OLED, физические 90 Гц, игровое качество и input-to-display latency не подтверждены. Ни CI, ни приведённые ниже проверки не являются сдачей продукта. Публичные промежуточные релизы запрещены.

## Реальный путь изображений

`application swapchain → GPU copy → two private source images → shared GPU analysis → synthesis(1/3), synthesis(2/3) → GPU copies → WSI present handoff`

`src/gpu_bridge.c` использует существующий application VkDevice и ту же compute-capable очередь. Нет полноразмерного readback/staging, `rgba_to_rgb`, CPU motion fitting, второго VkDevice, FD transport, MAKO или Lossless.dll. CPU-версия остаётся историческим кодом и **не компилируется в GPU-сборку по умолчанию**. `ENABLE_CPU_BRIDGE=1` — отдельная legacy-сборка, запрещённая GPU-packager.

Borrowed API Temporal Engine не требует, чтобы игра включала timeline semaphore или другие optional features. Внутренний путь использует R32F luma и порядок команд одной очереди. Источники чередуются, outputs имеют отдельные GPU command/fence lifetimes. BGRA packing выполняют шейдеры; copy сохраняет encoded bytes также для sRGB swapchain, без повторной gamma-конверсии. Instance/device dispatch принадлежат одному уровню цепочки Vulkan layers; созданные layer command buffers получают loader dispatch data. Это проверяется при обоих порядках native/validation. Выбор device dispatch локален потоку, включая worker standalone-движка.

Основной цикл не вызывает QueueWaitIdle/DeviceWaitIdle. Временные GPU-ресурсы не пересоздаются на каждом кадре. Ring ограничен тремя slots; занятой slot не блокирует игру, а приводит к явному real-frame bypass и сбросу истории. При недоступном WSI image нет ожидания бесконечного acquire: zero-timeout refusal отражается отдельно. Такой bypass не является достижением 3×. QueueWaitIdle используется при retirement, не в горячем пути.

Счётчики различают submitted outputs, GPU completed и present handoffs. Физический показ всегда `unobserved` без независимого наблюдения. GPU timestamps отдельно покрывают capture, output copies, анализ пары и каждый synthesis; они не обозначаются полной задержкой/энергией.

## Внутренние проверки

- Native core: 168 checks, 0 failures на lavapipe.
- Borrowed device без optional features: пиксели t=1/3 и 2/3, BGRA, запрет LMC/timeline paths, сохранение application device после удаления backend. Для текстурированной трансляции PSNR 37.125/35.835 dB против endpoint 20.801/20.813 dB; статичный кадр побитно точен. Это синтетический тест, не оценка игрового качества.
- WSI/validation: RGBA/BGRA SDR8 UNORM и sRGB; native loader path.
- Независимый observer: 4 real и 6 synthetic handoffs; проверка цветов всех пикселей, отличие промежуточных от endpoints и порядок; 96×64 и 1280×800. Только этот тест читает pixels на CPU.
- Async reuse: 300 real calls, 598 GPU completed/handoffs, 0 bypasses при 96×64 на software Vulkan; приложение не дренирует очередь между кадрами. Это не 30-минутный Deck game test и не доказательство 90 FPS.

- Lifecycle: три последовательно пересозданных swapchain 96×64 → 112×72 → 128×80 с oldSwapchain, оба порядка layers. Отключение/включение GPU mode сбрасывает историю и повторяет warmup; смена очереди сохраняет real presentation. Смена очереди пока проверена только анализом кода.
- 19 portable/installer checks: повреждённый пакет не меняет установку, точный rollback, выключенный режим, аргументы запуска и совместимость Steam launch option после удаления.
- Внутренний архив: проверка SHA-256, запуск установленного GPU payload и пересборка соответствующих исходников из архива.

Сырые логи: [results/fg3-gpu-20261015](results/fg3-gpu-20261015/README.md).

## Сборка и воспроизведение

```sh
make -C engine/gfg-temporal all lib
make -C engine/gfg-native ENABLE_TE=1 BUILD=build-gpu VULKAN_HEADERS=/path/to/Vulkan-Headers/include layer build-gpu/borrowed-device build-gpu/gpu-wsi-observer build-gpu/gpu-wsi-stress
VK_INSTANCE_LAYERS=VK_LAYER_KHRONOS_validation engine/gfg-native/build-gpu/borrowed-device
VK_INSTANCE_LAYERS=VK_LAYER_KHRONOS_validation xvfb-run -a engine/gfg-native/build-gpu/gpu-wsi-observer
GFG_NATIVE_FG=1 GFG_NATIVE_GPU=1 VK_INSTANCE_LAYERS=VK_LAYER_GFG_native:VK_LAYER_KHRONOS_validation VK_LAYER_PATH=$PWD/engine/gfg-native/build-gpu:/usr/share/vulkan/explicit_layer.d xvfb-run -a engine/gfg-native/build-gpu/gpu-wsi-stress
```

## Непройденные границы

Текущий GPU backend допускает один SDR8 swapchain, exclusive sharing, FIFO и compute-capable presentation queue. Нет собственной виртуализации swapchain/асинхронного presentation worker, измеренной cadence 90 Гц, законченной Decky-интеграции выбора 3×, аппаратной оценки качества/мощности/latency и испытаний A–F. HDR, Proton/gamescope extensions, смена fullscreen/resolution и suspend/resume требуют дальнейшей проверки. Resize проверен только в XCB/lavapipe, не в Proton/Gamescope. Сценарий 300 кадров не закрывает эти требования.

FidelityFX SDK изучен на SHA 60f4ea81909200d8542eca14dccb2628b763a9a3: frame interpolation API принимает depth, dilated motion vectors и reconstructed previous depth; эти данные не поступают автоматически из QueuePresent-only слоя. Их нельзя объявить доступными или заменить фиктивными нулями с заявлением равноценного качества. Открытый optical-flow компонент остаётся кандидатом следующего измеряемого сравнения; его код пока не заимствован.

До аппаратной приёмки packager допускает только `0.0.0-fg3-internal.N`, фиксирует `hardware_acceptance=false` и не публикует сборки. Старый prerelease workflow в этой ветке удалён. Стабильный main не изменён.
