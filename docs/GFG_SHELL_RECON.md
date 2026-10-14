# GFG Shell — этап A: разведка и матрица возможностей

Дата: 2026-10-14. Источники изучены по исходному коду (не по памяти):
OpenGamepadUI (GPL-3.0), ValveSoftware/gamescope, ChimeraOS gamescope-session (gamescope-session-plus),
ShadowBlip InputPlumber. Также изучены материалы прошлой попытки (ветка
`feature/gfg-steamos-shell-20261013`: `GFG_SHELL_ARCHITECTURE.md`, `GFG_SHELL_FAILURE_POSTMORTEM.md`,
`GFG_SHELL_ENVIRONMENT_BLOCKER.md`, `GFG_SHELL_DESIGN_SPEC.md`).

Метки: **ПОДТВЕРЖДЕНО (код)** — найдено в исходниках; **ПОДТВЕРЖДЕНО (тест)** — проверено нашими
тестами в CI/контейнере; **ГИПОТЕЗА** — требует проверки на Steam Deck. Ни одна строка ниже
не является результатом испытаний на устройстве.

## 1. Аудит прошлой попытки (GFG Shell Lab v0.1)

Прошлая ветка внедряла CSS/JS в CEF самого Steam через порт Decky и меняла внешний вид
штатного Gaming Mode. Это не оболочка: интерфейс оставался интерфейсом Steam, ломался при
каждом обновлении клиента и не давал собственной навигации. Постмортем той ветки сам называет
это главной архитектурной ошибкой. **Из неё взято:** дизайн (макеты, геометрия) и карта вызовов
GFG Governor (Battery/Balanced/Quality → `set_governor_mode`, Frame Fusion → `set_governor_frame_fusion`,
Continuous Boost → `set_governor_frame_os_feature`). **Не взято:** CSS-инъекция в Steam.

## 2. Как это делает OpenGamepadUI

| Вопрос | Что в коде | Статус |
|---|---|---|
| Библиотека Steam | Провайдер Steam — отдельный плагин (`OpenGamepadUI-plugins`), в ядре его нет. Ядро ожидает `Library.get_library_launch_items()`; есть текстовый VDF-парсер (Rust, `extensions/core/src/vdf.rs`) | ПОДТВЕРЖДЕНО (код) |
| Запуск игры | `steam -silent steam://rungameid/<id>`, обёрнутый в собственный `reaper SteamLaunch AppId=<id> -- …` (`library_desktop.gd:84`, `reaper.gd:14`) | ПОДТВЕРЖДЕНО (код) |
| Steam в режиме «полной оболочки» | Steam запускается под каждую игру и **убивается** (`kill -15`) после её окончания (`running_app.gd:271-321`) | ПОДТВЕРЖДЕНО (код) — **нам не подходит** (ТЗ запрещает принудительно завершать Steam) |
| Steam в `--overlay-mode` | Steam постоянно работает как «underlay» (`steam -gamepadui -steamos3 -steampal -steamdeck`), OGUI — оверлей поверх (`card_ui_overlay_mode.gd`) | ПОДТВЕРЖДЕНО (код) — **ближайшая модель для этапов C/D** |
| Определение игры | Окна второго XWayland + `/proc` (переменная `OGUI_ID`), `STEAM_GAME`, `_NET_WM_PID`; чужие игры — по `GAMESCOPE_FOCUSED_APP` | ПОДТВЕРЖДЕНО (код) |
| Ввод на Deck | InputPlumber: прячет hidraw/event Deck-контроллера, отдаёт виртуальные устройства; режимы перехвата NONE/PASS/ALL; переключение PASS↔ALL при открытии меню | ПОДТВЕРЖДЕНО (код) |
| Питание | `systemctl suspend/poweroff/reboot`; UPower; яркость через `steamos-priv-write`; звук через `wpctl`; сеть через NetworkManager D-Bus | ПОДТВЕРЖДЕНО (код) |

## 3. Gamescope (атомы, подтверждено в `src/steamcompmgr.cpp`)

| Атом | Смысл |
|---|---|
| `STEAM_GAME` (на окне) | appID окна; учитывается только в steam-режиме (`-e/--steam`). 769 = сам Steam |
| `STEAM_OVERLAY` | окно-оверлей (полноэкранный — overlay, иначе — notification) |
| `STEAM_INPUT_FOCUS` | оверлей забирает ввод (2 = клавиатура остаётся у приложения) |
| `GAMESCOPE_EXTERNAL_OVERLAY` | внешний оверлей (mangoapp), никогда не получает фокус |
| `GAMESCOPECTRL_BASELAYER_APPID` / `_WINDOW` (root) | порядок приоритета фокуса по appID / явное окно |
| `GAMESCOPE_FOCUSED_APP`, `_FOCUSABLE_APPS`, `_FOCUSABLE_WINDOWS` (root) | публикует gamescope: что в фокусе и что может его получить |

Вывод: управление фокусом в gamescope — это набор X-свойств, которые штатно пишет Steam.
Кто пишет `BASELAYER_*` одновременно со Steam, тот с ним конкурирует. Поэтому всё это изолируется
в отдельном адаптере и включается только на этапе C, после проверки на устройстве.

## 4. Сессия (gamescope-session-plus)

- Файл сессии ищется в `/usr/share/…/sessions.d/$CLIENT`, `/etc/…/sessions.d/$CLIENT` и
  **`~/.config/gamescope-session-plus/sessions.d/$CLIENT`** (пользовательский override существует). ПОДТВЕРЖДЕНО (код).
- `CLIENTCMD` — главный клиент; Steam скрипт сам не поднимает. Короткие падения (<60 с) считаются,
  после 5 — `short_session_recover`. ПОДТВЕРЖДЕНО (код).
- **SteamOS использует собственный `gamescope-session` Valve, а не ChimeraOS-скрипт.** Есть ли в
  SteamOS 3.x пользовательская точка расширения сессии без записи в `/usr` — ГИПОТЕЗА, проверяется
  диагностикой этапа B (`session.txt`: `loginctl`, юниты `gamescope*`, `/etc/sddm.conf.d`).
- Возврат в штатный режим: `steamos-session-select gamescope|plasma`. ПОДТВЕРЖДЕНО (код OGUI, ветка SteamOS).

## 5. Матрица возможностей GFG Shell

| Требование ТЗ | Решение | Этап | Статус |
|---|---|---|---|
| Steam — игровой клиент (DRM, Steam Input, оверлей, Proton, параметры запуска, облако, достижения, обновления) | Каждая игра запускается **только** через `steam steam://rungameid/<id>` — Steam делает всё сам | B | Механизм ПОДТВЕРЖДЕН (код OGUI); на Deck — ГИПОТЕЗА H1 |
| Обнаружение игр | Чтение файлов Steam: `libraryfolders.vdf`, `appmanifest_*.acf` (StateFlags&4), `loginusers.vdf`, `localconfig.vdf` (LastPlayed/Playtime), бинарный `shortcuts.vdf`, избранное из `cloud-storage-namespace-1.json`, обложки `appcache/librarycache` (старая плоская и новая папочная схема) и `userdata/*/config/grid` | B | ПОДТВЕРЖДЕНО (тест, на фикстурах). Точные имена новых файлов кэша и формат избранного — ГИПОТЕЗА H4 |
| Игра запущена / закрыта | `/proc/*/cmdline` с маркером `reaper SteamLaunch AppId=<id>` (Steam оборачивает каждую игру так же, как OGUI имитирует) | B | ПОДТВЕРЖДЕНО (тест, имитация /proc); на Deck — ГИПОТЕЗА H2 |
| Автовозврат в оболочку | Этап B: оболочка — non-Steam игра; после выхода из игры gamescope возвращает фокус оставшемуся приложению | B | ГИПОТЕЗА H3 |
| Не дублировать ввод, Steam Input сохранён | Этап B: оболочка читает **виртуальный геймпад Steam Input** (как любая игра). Устройства не захватываются, InputPlumber не нужен | B | По построению; проверка — H5 |
| Падение оболочки | Этап B: Steam остаётся главным клиентом, падение оболочки = выход «игры» → штатный Gaming Mode | B | По построению; проверка — H6 |
| Сон/пробуждение | Через logind (`systemctl suspend`), как штатное меню | B | ГИПОТЕЗА H7 |
| Своя сессия Gaming Mode | Вариант «overlay-mode»: Steam работает постоянно (без убийства), GFG Shell — `STEAM_OVERLAY`-окно поверх, фокус через `STEAM_INPUT_FOCUS`; включение только обратимо (пользовательский файл сессии / выбор сессии), без изменения `/usr` | C | Механизм ПОДТВЕРЖДЕН (код OGUI/gamescope); применимость к сессии SteamOS — ГИПОТЕЗА |
| Быстрая панель поверх игры | То же overlay-окно; кнопка — сочетание, которое Steam не занимает (Steam и «…» остаются у Steam) | D | ГИПОТЕЗА |
| InputPlumber | Только если этап C/D покажет, что без него нельзя получить кнопку поверх игры. Не включается безусловно | D | Не нужен для B |
| GFG Bridge | Локальный TCP 127.0.0.1 + токен в файле 0600 (у Godot нет клиента Unix-сокетов); чтение статуса Governor и белый список: режим (без Extreme), Frame Fusion, Continuous Boost. TDP/GPU не трогает | E (ядро уже в B) | ПОДТВЕРЖДЕНО (тест: Python unit + Godot↔Python e2e) |
| Восстановление, установщик | Установка только в `$HOME`, удаление одним скриптом, диагностика в zip | F (основа в B) | ПОДТВЕРЖДЕНО (тест: установка/запуск/удаление в контейнере) |

Обновление Steam от 13.10.2026 проверить офлайн невозможно: всё, что зависит от версии клиента
(имена файлов кэша, формат избранного), читается терпимо к отсутствию и проверяется диагностикой.

## 6. Гипотезы для проверки на Deck (этап B)

| # | Гипотеза | Как проверить | Что смотреть в диагностике |
|---|---|---|---|
| H1 | Steam запускает игру по `steam://rungameid`, пока оболочка (non-Steam игра) открыта | Нажать «Играть» на установленной Steam-игре | `[runner] launch …`, затем `game … running` |
| H2 | У игры есть процесс `reaper SteamLaunch AppId=<id>` (Steam и Proton, non-Steam) | Запустить нативную, Proton и non-Steam игру | `processes.txt`, `[runner]` |
| H3 | После выхода из игры фокус возвращается в оболочку | Выйти из игры штатно | `exited`, toast «С возвращением» |
| H4 | Обложки/избранное читаются в текущем Steam | Открыть Библиотеку | `summary.json: library_counts.with_grid/with_hero` |
| H5 | Нет двойного ввода, Steam/«…» работают | Нажимать Steam/«…» поверх оболочки и игры | субъективно + `joypads` в `summary.json` |
| H6 | Падение оболочки → штатный Gaming Mode | Настройки → Диагностика → «Аварийно завершить оболочку» (2 нажатия) | Steam UI остаётся рабочим, в журнале `user-triggered crash test` |
| H7 | Сон из меню питания и пробуждение | Питание → Спящий режим | журнал `[power] suspend`, работа после пробуждения |
| H8 | Лаунчер-игры (EA/Ubisoft через Proton) | Запуск такой игры | маркер reaper живёт, пока жив лаунчер |
