<div align="center">

[English](README.md) · **Русский**

<img src="docs/img/logo.png" alt="GFG Extreme" width="180">

# GFG Extreme

### Генерация кадров на Steam Deck, которая настраивает себя сама.

Нажмите **Run**. GFG выберет частоту кадров под ваш экран, решит, сколько кадров генерировать,<br>
и опустит TDP настолько, насколько позволяет игра, — а потом будет подстраиваться, пока вы играете.

[**Скачать последний релиз**](https://github.com/wavessevaw/GFG-Extreme/releases) · [Быстрый старт](#быстрый-старт) · [Что-то не работает?](#что-то-не-работает)

![release](https://img.shields.io/github/v/release/wavessevaw/GFG-Extreme?style=flat-square&color=fb0d00&label=release)
![platform](https://img.shields.io/badge/Steam%20Deck-OLED%20%C2%B7%20LCD%20%C2%B7%20Dock-111?style=flat-square)
![decky](https://img.shields.io/badge/Decky%20Loader-plugin-111?style=flat-square)
![license](https://img.shields.io/badge/license-GPL--3.0-111?style=flat-square)

<br>

<img src="docs/img/home-adapting-oled.png" width="270">&nbsp;&nbsp;
<img src="docs/img/page-details.png" width="270">&nbsp;&nbsp;
<img src="docs/img/page-setup.png" width="270">

<sub>Главный экран во время игры · Details · Check setup. Отрисовано настоящим интерфейсом на примерных данных.</sub>

</div>

---

## Что он делает

**30 настоящих кадров, 90 на экране, 9 ватт.** На Steam Deck OLED Governor может отрисовывать игру с 30 кадрами, догенерировать остальное до 90 и держать APU на 9 Вт. Если сцена становится тяжелее, он примерно за две секунды добавляет ватты или сгенерированные кадры. Пока игра держится, каждые 45 секунд пробует на ватт меньше.

- **Знает ваш экран.** OLED → 90 FPS, LCD → 60 FPS, док или внешний монитор → 60 FPS.
- **Проверяет каждое изменение.** Каждая настройка подтверждается по данным самого рендерера и откатывается, если не держится.
- **Помнит ваши игры.** Следующая сессия начинается с того, что сработало в прошлый раз, а не с нового поиска.
- **Видит устройство.** Температура, нагрузка GPU и CPU, скачки времени кадра, потребление от батареи. Главный экран одной строкой говорит, во что упирается игра.
- **Не трогает ваши настройки.** Сохранённый профиль не меняется никогда, Stop возвращает всё как было. Никакого разгона, никогда выше потолка мощности вашей Deck, а если TDP постоянно меняет другой инструмент, GFG перестаёт с ним спорить.

## Три режима

| | Настоящие кадры | Мощность | Когда выбирать |
|---|---|---|---|
| **Battery** | от 24 | идеально 9–11 Вт, больше только в крайнем случае | нужна максимальная автономность |
| **Balanced** | от 30 | старт с 12 Вт, никогда выше обычного диапазона | нужна более ровная картинка |
| **Quality** | сколько получится | снижается после того, как выбрано качество | Deck на зарядке |

## Быстрый старт

Нужны [Decky Loader](https://decky.xyz/) и [Lossless Scaling](https://store.steampowered.com/app/993090/Lossless_Scaling/) из Steam (обычная публичная версия).

1. Скачайте `GFG-Extreme-v1_0_0.zip` (или новее) со страницы [Releases](https://github.com/wavessevaw/GFG-Extreme/releases) и установите в Decky (*Install from zip*). Разрешите доступ root — он нужен только для установки TDP.
2. Откройте GFG Extreme и нажмите **Install engine**.
3. В Steam откройте у игры **Свойства → Параметры запуска** и вставьте:
   ```text
   /home/deck/.local/bin/gfg %command%
   ```
   (GFG сам показывает эту команду с кнопкой **Copy**, пока игра не подключена.)
4. Запустите игру и нажмите **Run**.

Heroic, Lutris, EmuDeck и другие Flatpak-приложения: **Settings → System**, включите GFG для приложения.

## Оверлей в игре

<img src="docs/img/hud-ingame-standard.png" width="620">

`90 FPS  x3  (30)  sc100  TDP 9W  APU 8W  2h32  easy` — кадры на экране, множитель, настоящие кадры, масштаб рендера, лимит TDP и измеренное потребление APU, оставшееся время от батареи, насколько тяжело работает GFG. Включается в **Settings → In-game overlay**; варианты Minimal, Standard, Detailed.

## Что-то не работает?

1. **Settings → Diagnostics → Check setup.** Одно нажатие проверяет движок, лаунчер, оверлей, лог диагностики и доступ к TDP и для каждого проваленного пункта говорит, что исправить.
2. **Запишите лог.** Settings → Diagnostics → **Record log**, поиграйте минуту, **Stop**. На рабочем столе Steam Deck появится zip, сверху в нём `summary.txt` с выводами простым языком. [Создайте issue](https://github.com/wavessevaw/GFG-Extreme/issues) и приложите его.

## Статус

**Стабильная версия (1.0.x).** Каждый релиз покрыт автоматическими тестами (Python-бэкенд, сгенерированный лаунчер в bash, интерфейс в headless-браузере) и проверяется на настоящей Steam Deck. Логи из других игр и конфигураций очень пригодятся. Известные ограничения: [docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md](docs/GFG_GOVERNOR_KNOWN_LIMITATIONS.md).

<details>
<summary><b>Что ещё умеет</b></summary>

- Профили для каждой игры, выбираются автоматически по Steam app ID или имени процесса.
- Генерация кадров через **GFG Engine**, **OptiScaler**, **встроенную в игру** или **выключена**; пространственное масштабирование и шейдеры vkBasalt — независимо от неё. С внешним backend GFG только наблюдает.
- **Pipeline Inspector**: сохранённое vs. действующее vs. Governor vs. то, что реально загрузил процесс игры.
- **Журнал конфигурации** с безопасным откатом и **All settings** для любой опции движка.
- Совместимость с Gamescope WSI, MangoHud, Flatpak-расширения и доступ для отдельных приложений.

</details>

<details>
<summary><b>Для разработчиков</b></summary>

```bash
npm ci
npm test              # тесты бэкенда, сборка и смоук-тест интерфейса
npm run build         # frontend/ → dist/index.js (CI падает, если файл устарел)
npm run screenshots   # перерисовать docs/img из настоящего интерфейса
python3 tools/gfg_log_report.py <log.zip>   # прочитать записанный лог на ПК
```

Документация: [архитектура Governor](docs/GFG_GOVERNOR_ARCHITECTURE.md) · [телеметрия](docs/GFG_TELEMETRY_CAPABILITIES.md) · [интерфейс](docs/GFG_UI_REDESIGN.md). Каждое слияние в `main` с новой версией автоматически публикует релиз (0.x — как пре-релизы, начиная с 1.0.0 — как официальные).

</details>

## Благодарности

GFG Extreme продолжает работу **MAKO** и **lsfg-vk**: он пришёл на смену [Decky LSFG-VK Experimental](https://github.com/eugeniosegala/decky-lsfg-vk-experimental), а встроенный движок основан на проекте MAKO, который приносит генерацию кадров LSFG, пространственное масштабирование и шейдеры в Linux. Спасибо их авторам. GFG Extreme не содержит и не распространяет Lossless Scaling; исходные имена `mako-*` сохранены там, где этого требует совместимость с рендерером.

GPL-3.0-or-later · [Лицензия](LICENSE.md) · [Сторонние компоненты](THIRD_PARTY_NOTICES.md)
