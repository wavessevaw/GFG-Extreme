# GFG Shell: архитектурное решение после аудита

Статус: исследование, реализация renderer не заявлена. База — shell-fix-5, `980da65ea3cc0643df9022a70a0380bc4841c57a`. Предлагаемую привязку к API Steam необходимо подтвердить на реальном SteamOS до скрытия его UI.

## Steam Adapter

Один адаптер на версию клиента и контекст. Контракт snapshot: route, library с appId/названием/artwork/installed/favorite, recent games, game details, downloads, storage, user, battery/time/network, display/audio, keyboard и focus. Каждое значение имеет observedAt, source и availability; неизвестные значения не заменяются данными макета.

Контракт действий: launch/openGame/navigate/filter/sort, pause/resume download, system/display/audio changes, sleep, native text input. Конкретные внутренние функции Steam не угадываются. Для каждой binding нужны наблюдение на устройстве, схема аргументов, подписка/read-back и обратимость. Наличие функции в объекте не доказывает, что она безопасно выполняет нужное действие.

Нельзя использовать чтение пикселей как источник прогресса, копировать токены Steam, логировать тексты переписки или всю память клиента. Диагностика содержит разрешённые capabilities, версии, причины отказа и обезличенные структуры. Служебный SharedJSContext используется только для подтверждённых bindings; его DOM не выдаётся за видимый экран.

## Renderer

Собственный React-root с отдельными Home, Library, GameDetails, QuickAccess, Settings, Downloads, SteamMenu, KeyboardHost. Геометрия задаётся эталонами `GFG_SHELL_REFERENCE_GEOMETRY.json`, не расположением нативных элементов. Произвольная новая навигация и демонстрационные игры запрещены.

Монтирование двухфазное: подготовить данные/навигацию и невидимый root → получить успешную раскладку и зарегистрировать input/focus → лишь затем переключить видимость native surface. При отказе остаётся работающий Steam. Реальная клавиатура/IME и системные клавиши сохраняют владельца; собственная визуальная рамка не подменяет композицию текста отправкой отдельных букв.

Состояния каждого экрана: loading, ready, unavailable, action-pending, action-confirmed, action-failed. Pending не отображается как confirmed. Незавершённый запрос отменяется либо игнорируется при смене route/document epoch. Данные обложек берутся из подтверждённого artwork provider; при отсутствии изображения сохраняется геометрия и явный fallback, без выдуманной игры.

## GFG Bridge

Использует существующие RPC и их подтверждённые результаты, а не прямую запись конфигов из injected document. Не создаёт незащищённый сетевой RPC. Привязка к активному профилю/игре должна быть явной; при неизвестном profile запись запрещена.

Из существующего кода подтверждены следующие операции:

| Элемент | RPC / значение | Подтверждение |
|---|---|---|
| Battery | set_governor_mode(profile, `budget`) | get_governor_status |
| Balanced | set_governor_mode(profile, `balanced`) | get_governor_status |
| Quality | set_governor_mode(profile, `quality`) | get_governor_status |
| Autopilot | mode `autopilot` и enabled | последовательные ответы + read-back |
| Frame Fusion | set_governor_frame_fusion(enabled) | setting_enabled и scope_active раздельно |
| Continuous Boost | set_governor_frame_os_feature(profile, `continuous_boost`, enabled) | сохранённое значение и активный scope раздельно |

Battery/Balanced/Quality не являются тремя подрежимами Autopilot в текущем Governor. По новому ТЗ кнопки действительно выбирают соответствующий Governor mode. Переключение с Autopilot на один из них снимает активный Autopilot; Fusion и Boost остаются Autopilot-only. UI должен отражать это read-back, а не оставлять ложный включённый Autopilot ради картинки. Сохранённое пожелание включить Fusion отличается от активного выполнения.

## Recovery Layer

Журналирует только изменения, которыми владеет Shell: собственный root/styles/listeners/subscriptions и временные атрибуты видимости. Не перемещает и не удаляет чужие DOM-узлы без возможности точно вернуть их владельцу. Сохраняет прежний focus/route и освобождает захват ввода. Не сбрасывает настройки игры и профиля при возврате темы.

Истечение lease, unload, update, navigation и исключение renderer завершаются одним идемпотентным teardown. Устройство с остановленным event loop восстанавливается при его возобновлении: нельзя обещать точные 15 секунд во сне. Нативные Steam/QAM buttons остаются доступными для выхода. Незавершённая системная операция не повторяется автоматически после reconnect.

## Диагностика и приёмка

Четыре независимых состояния, каждое с timestamp и reason:

1. transport: disconnected / connected, target/session identity.
2. injection: none / acknowledged / failed, revision и document epoch.
3. renderer: unmounted / mounting / visible / failed, screen и root bounds.
4. device_validation: not_run / failed / passed, artifact manifest, exact commit, device/Steam/SteamOS/Decky versions.

Наличие injected STYLE не может установить renderer.visible. Наличие renderer.visible не может установить device_validation.passed. Материалы другого коммита, другой темы или синтетического браузера не принимаются за device validation.

Порядок: исследовать реальные bindings → Home/Library с запуском игры и input → ещё шесть экранов → переходы/recovery/sleep → визуальная сверка → ZIP из проверенного коммита. Без среды SteamOS первый переход сейчас заблокирован; новый демонстрационный renderer вместо этого перехода не создаётся.
