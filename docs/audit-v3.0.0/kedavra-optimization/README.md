# Kedavra: отчёт для основного агента GFG

Полная копия [отчёта оптимизации](OPTIMIZATION-2.ru.md) и результатов трёх сравнений находится в этой папке. Исходный коммит Kedavra: `1486387`. Относительные команды сборки в отчёте выполняются в репозитории Kedavra, а не GFG.

- [Код исправлений и оригинал отчёта](https://github.com/wavessevaw/GSF_Kedavra/blob/1486387/docs/deep-review/OPTIMIZATION-2.ru.md).
- [Скрипт повторения экспериментов](https://github.com/wavessevaw/GSF_Kedavra/blob/1486387/docs/deep-review/run_shader_variants.sh).
- [Полный аудит интеграции](https://github.com/wavessevaw/GSF_Kedavra/blob/codex/kedavra-deep-review/docs/deep-review/ANALYSIS.ru.md).
- [Governor 2.0 и исправления контроллеров](../../governor2/CONCEPT.ru.md).

Исправлены undefined read в repair и лишние вычисления длины для порогов. Простая замена confidence отклонена по результатам качества. Ускорение на Steam Deck не измерено; проверки выполнены на llvmpipe. Новых релизов нет. Перенос производственного кода и аппаратная приёмка не выполнены этим документированием.
