# Iguana Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`,
`concepts/panels.md`. Основано на функционале интеграционного движка (HL7/X12/FHIR channels).

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Column`(align="start") + `ui.Text`(server instance) + `ui.Divider` + navigation `ui.ListItem`(Channels/Messages/Logs) + `ui.Button`("App settings") | Без карточек по стандарту. |
| Channel List (center, `center_overlay=True`) | `ui.Stats`(Running/Stopped/Errors today) + `ui.DataTable`(name, status Toggle-колонка editable, messages processed; sortable) | Запуск/остановка канала прямо из таблицы через editable toggle-колонку. |
| Channel Detail | Back-button + `ui.KeyValue`(source type/translator/destination) + `ui.Graph`(nodes=from/to connectors, edges=flow) + `ui.Row`(Button "Start", "Stop", "Restart") | `Graph` — визуализация топологии from/to канала Iguana. |
| Message Browser | `ui.Select`(status_filter) + `ui.DataTable`(message id, status Badge processed/error/queued, received date; sortable) | Табличный обзор потока сообщений через канал. |
| Message Detail | Back-button + `ui.Tabs`(Source/Translated/Destination) → `ui.Code`(language="text", содержимое по вкладке) + `ui.Timeline`(processing stages) | `Code` для сырого HL7/X12; `Timeline` для этапов обработки. |
| Reprocess Dialog | `ui.Dialog`(title="Переотправить сообщение?", content=`ui.Text`("Сообщение будет обработано каналом заново."), confirm_label="Переотправить") | Повторная обработка может дублировать данные — обязателен `Dialog`. |
| Translator/Script Library | `ui.List`(translators: name, language) | Простой список Translator-скриптов (Annotator/Lua/JS). |
| System Log Viewer | `ui.Code`(language="text", server log tail, readonly) | Моноширинный вывод системного лога сервера Iguana. |
| App Settings | `ui.Accordion`([Connections+Disconnect, Server URL/API Key Config]) | Централизованные настройки по стандарту. |

## 2. User flow (валидно по panel lifecycle)

1. **SESSION INIT** → `__panel__iguana_sidebar` рендерит список каналов, `auto_action`
   открывает Channel List с live-статусами.
2. Channel List: editable toggle "started" → `on_cell_edit` вызывает `start_channel`/
   `stop_channel` напрямую (обратимо) → `refresh_panels`.
3. Клик на строку канала → Channel Detail — `Graph` рендерит топологию from→to.
4. Из Channel Detail клик "Messages" → Message Browser с фильтром по статусу.
5. Клик на сообщение → Message Detail — `Tabs` переключает Source/Translated/
   Destination.
6. "Переотправить" → `ui.Dialog` подтверждение → `ui.Call("reprocess_message")` →
   `refresh_panels`.
7. App Settings — только через кнопку в сайдбаре, единственное место с disconnect.

## 3. Экраны/карточки (артефакты для реализации)

- `panels.py`: `__panel__iguana_sidebar` (left).
- `panels_channels.py`: `__panel__channel_list` (center, `center_overlay=True`),
  `__panel__channel_detail` (center, параметризован `channel_id`).
- `panels_messages.py`: `__panel__message_list` (center, параметризован `channel_id`),
  `__panel__message_detail` (center, параметризован `message_id`).
- `panels_logs.py`: `__panel__system_log` (center).
- `panels_settings.py`: `__panel__app_settings` (center overlay, Accordion,
  единственное место с disconnect).
