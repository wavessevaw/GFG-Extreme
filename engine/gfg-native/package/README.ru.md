# GFG FG3 — внутренняя GPU-сборка

**НЕ ЗАВЕРШЕНА. Не пользовательский релиз и не release candidate.** Аппаратные испытания Steam Deck OLED A–F не пройдены. 90 реально показанных FPS, игровое качество, энергия и input-to-display latency не подтверждены.

Внутренний пакет содержит самостоятельный Vulkan layer, открытый GPU interpolation core, исходники и SHA-256. Нет обязательных MAKO, Lossless Scaling или закрытых моделей. Путь: GPU copy → GPU LMC analysis/model fit → synthesis 1/3, 2/3 → GPU copy → WSI. Полноразмерного CPU transport нет.

Для изолированного внутреннего стенда: `bash install.sh`; запуск `~/.local/bin/gfg-native <command>`. Нужны Vulkan 1.2, 64-bit SDR8, FIFO, одна очередь с compute и один swapchain. По умолчанию используется lmc-gpu (ещё не аппаратно принят); tiles доступен для диагностики. Unsupported/busy path сохраняет real presentation и сообщает bypass; он не обозначается успешным 3×.

Откат предыдущей установки: `bash rollback.sh`. Удаление: `bash uninstall.sh`. Основная установка GFG Extreme не заменяется. Все изменения этого пакета относятся только к пользовательскому `gfg-native` и его launcher.

Логи различают `submitted_outputs`, `gpu_completed`, `present_handoffs` и `physical_display=unobserved`. Две последующие цифры не являются доказательством сканирования OLED. Запрещено интерпретировать software Vulkan measurements как Steam Deck performance.
