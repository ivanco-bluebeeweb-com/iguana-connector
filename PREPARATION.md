# Iguana / iNTERFACEWARE Connector — Preparation

**Статус:** Фаза 1 (Discovery + архитектурные решения) завершена. Объём
релиза заявлен пользователем явно в исходном запросе задачи #2251 —
"делай это приложение в полном максимуме со всеми возможными функциями" —
трактуется как "максимум" (Ярус 1+2+3) по прецеденту GitLab CI/CD/MuleSoft/
PagerDuty/UiPath/Blue Prism/Automation Anywhere, где такая же явная
формулировка уже освобождала от повторного вопроса.

**Владелец продукта:** vlad@bluebeeweb.com
**Дата подготовки:** 2026-08-22, v0.1
**Vikunja task:** #2251 (BBW Imperal Apps), [App Development].

**Почему сейчас:** Iguana — устоявшийся healthcare/HL7 integration engine,
прямой конкурент Mirth Connect/Rhapsody/Cloverleaf, нишевый но глубоко
закреплённый в medical/healthcare IT (больницы, лаборатории, страховые).
В портфеле Imperal уже есть общие iPaaS-коннекторы (n8n/Make/Workato/
MuleSoft) — Iguana закрывает специфичный healthcare-интеграционный сегмент,
которого там ещё нет.

---

## 1. Паспорт приложения

**Название в Marketplace (display_name): «Iguana»**. Внутренний
app_id/папка: `iguana-connector`.

**Iguana Connector** — коннектор к HTTP API self-hosted инстансов Iguana
(iNTERFACEWARE) — healthcare integration engine на базе Channels
(интерфейсов), состоящих из Components (From/Translator/To). BYOK:
пользователь подключает свой собственный Iguana-инстанс (`base_url` +
admin username/password), Imperal ничего не хостит и не проксирует помимо
самого HTTP-запроса.

**⚠️ Заявленное ограничение вендора (не недоработка коннектора):** Iguana
имеет ДВЕ несовместимые генерации продукта. **Iguana 6** — полностью
документированный, стабильный HTTP API (Basic Auth, `POST <base_url>/
add_channel` и т.п.) — это то, против чего строится коннектор. **IguanaX**
(текущая активно развиваемая линейка) официально **не предоставляет
публичный REST API для внешнего управления** (подтверждено прямой цитатой
из официальной документации iNTERFACEWARE, см. `CONNECTOR_DISCOVERY.md`
§2) — управляется только Lua-скриптами внутри самого запущенного
инстанса или недокументированным веб-UI. Это объективная техническая
граница, а не пропуск с нашей стороны; отражена в UI (App settings →
"Совместимость") и в FAQ модалках.

## 2. Проблема в человеческих словах

> Когда **интеграционный инженер клиники/лаборатории** сталкивается с
> необходимостью **проверить статус десятков HL7-каналов, перезапустить
> упавший интерфейс, или экспортировать конфигурацию канала для бэкапа/
> миграции**, ей приходится **логиниться в веб-консоль Iguana вручную,
> канал за каналом**, из-за чего возникает **потеря времени на рутинные
> проверки и риск пропустить упавший канал, обслуживающий критичный
> клинический поток данных (лабораторные результаты, ADT-сообщения)**.

## 3. Аудитория, роли и доступ

- **Основная роль:** HL7/integration engineer, интеграционная команда
  больницы/лаборатории/страховой, управляющая своим Iguana-инстансом.
- **Вторичная роль:** DevOps/IT-администратор, отвечающий за uptime
  каналов и лицензирование инстансов.
- **Доступ:** BYOK — своя пара admin username/password к своему
  self-hosted инстансу. Нет мультитенантного облачного аккаунта у самого
  Iguana — коннектор ничего не роняет "по умолчанию".

## 4. Пользовательские сценарии и точки решения человека

- **Проверка здоровья интеграций:** `audit_server` — агрегированный отчёт
  (статус сервера, все каналы, какие остановлены/в ошибке, версия) одним
  вызовом вместо ручного обхода UI.
- **Реакция на инцидент:** канал упал → `get_channel_error_summary` →
  `update_channel`/`status(action=start)` — перезапуск после diagnosis,
  не вслепую.
- **Массовое обслуживание:** плановое окно обслуживания →
  `bulk_stop_channels` перед патчем сервера → `bulk_start_channels` после.
- **Точка решения человека:** любое `remove_channel` (необратимо на
  стороне Iguana) и любое `import_project` (перезаписывает существующий
  Translator-проект) — риск-жест, помечены `call_builder_ability_risky`-
  эквивалентом (destructive), требуют explicit confirmation в чате.
- **Лицензирование:** активация/перенос лицензии (`license.activate`,
  `license.UpdateActivationInfo`) — явно риск-жест (может занять/освободить
  платный слот лицензии клиента), требует explicit confirmation.

## 5. Ценность и измеримый результат

- Время на еженедельную проверку здоровья N каналов: с ручного обхода
  UI (минуты на каждый) до одного вызова `audit_server`.
- Доля инцидентов с каналом, обнаруженных ДО жалобы клинического
  пользователя (через периодический `audit_server`/`get_stopped_channels_report`).
- Время восстановления канала после сбоя (from detection to restart).
- Неуспех: если пользователи Iguana не готовы дать Imperal admin-доступ
  к своему инстансу (compliance concerns в healthcare) — тогда P0 не
  наберёт adoption; это диагностируется через discovery-интервью (§11).

## 6. Границы: делает / не делает

**Делает (P0 + Ярус 1-3, полный охват Iguana 6 HTTP/Web/License API):**
- Управление каналами: create/update/remove/get_config/get_default_config.
- Контроль исполнения: start/stop/startall/stopall, per-channel и bulk.
- Мониторинг: server status, current_version, monitor query, log query
  (api_query), per-channel error summary.
- Source control: sc/commit, sc/bump.
- Экспорт/импорт: export_project (backup), import_project (restore/clone).
- Лицензирование: list entitlements, activate, list activations, transfer
  (UpdateActivationInfo), instance license detail.
- Value-add агрегаты (Ярус 3): `audit_server`, `bulk_start_channels`,
  `bulk_stop_channels`, `clone_channel`, `get_stopped_channels_report`,
  `get_channel_error_summary`.

**Не делает:**
- Не управляет живым IguanaX-инстансом через REST — вендор не
  предоставляет такой публичный контракт (см. §1 и `CONNECTOR_DISCOVERY.md`
  §2). Явно сообщается пользователю, не выдаётся за баг коннектора.
- Не пишет/не редактирует Lua-код Translator-компонентов (не текстовый
  редактор кода) — только конфигурацию канала целиком (get/update/add
  через `config=` XML blob), как и сам HTTP API это предоставляет.
- Не хранит и не индексирует содержимое HL7-сообщений (PHI) на стороне
  Imperal — `api_query`/`monitor_query` читаются "на лету" и не кешируются
  постоянно дольше одного ответа пользователю.

## 7. Данные, конфиденциальность и интеграции

- **Минимально необходимые данные:** `base_url` (host:port инстанса),
  admin `username`/`password` (BYOK, Vault-encrypted через `ctx.secrets`,
  никогда не логируются). Опционально отдельная пара для License API
  (my.interfaceware.com credentials — НЕ то же самое, что admin инстанса).
- **PHI-осторожность:** лог-сообщения (`api_query`) МОГУТ содержать
  реальные HL7-сообщения с данными пациентов. Коннектор не хранит их
  постоянно — передаёт ответ по запросу и всё. В App settings — явное
  предупреждение об этом (FAQ).
- **Retention:** только сами credentials хранятся (до `disconnect`);
  никакого кеша сообщений/логов.
- **Tenant isolation:** каждый Imperal-пользователь хранит свой список
  подключений (`iguana_connections` secret, JSON-массив) — тот же паттерн,
  что GitLab CI/CD/PagerDuty/MuleSoft.
- **Интеграции:** нет сторонних Imperal-приложений, зависящих от этого
  коннектора на момент P0. Статус: `available` (Iguana 6 HTTP API — прямой
  публичный контракт, подтверждён живой документацией 2026-08-21/22).
  IguanaX REST-управление: статус `blocked` — вендор не публикует
  контракт, не наш блокер, честно отражено в UI.

## 8. P0 — минимальный законченный полезный путь

**Главный use case:** интеграционный инженер подключает свой Iguana 6
инстанс и получает агрегированный отчёт о здоровье всех каналов одним
запросом (`audit_server`), затем при необходимости управляет отдельным
каналом (start/stop/update) без похода в веб-консоль.

- Сущности: Connection (base_url+credentials), Channel, Server status.
- Server-side safety gates: подтверждение на `remove_channel`,
  `import_project`, `license.activate`/`UpdateActivationInfo`.
- Исключено из P0 (доступно в Ярусе 2/3, не блокирует P0): source control
  commit/bump, лицензирование, value-add отчёты — доступны сразу при
  релизе "максимум", но не входят в узкий P0 acceptance test.
- Acceptance: пользователь подключает инстанс → видит список каналов
  с реальным статусом → может остановить/запустить канал → видит успех/
  ошибку в чате.

## 9. UX-карта Imperal panel

- **Точка входа:** сайдбар приложения "Iguana" → форма подключения
  (base_url, username, password, label) с лейблами и контекстными
  плейсхолдерами, растянута на всю ширину сайдбара (по
  `UI_INTERFACE_STANDARD.md`/`DESIGN_LANGUAGE...`).
- **Первый экран после подключения:** список подключений + быстрая кнопка
  "Запустить проверку здоровья" (`audit_server`).
- **Primary next action:** просмотр списка каналов с их статусом.
- **Empty state:** "Нет подключённых инстансов — подключите свой Iguana
  сервер, чтобы начать".
- **Blocked/error state:** явное сообщение при 401 (неверные
  credentials) vs недоступности хоста (timeout/connection refused) —
  разные причины, разные сообщения.
- **App settings:** единственная secondary-кнопка в сайдбаре, все
  настройки (управление подключениями, лицензионные credentials, FAQ про
  Iguana 6 vs IguanaX) — в центральном слоте, без дублирования инструкций
  в сайдбаре.

## 10. Safety, approvals и audit trail

- Webbee может сама: list/get/status-проверки, start/stop одного канала
  (recoverable), export_project (read-only backup).
- Требует explicit confirmation в чате: `remove_channel`, `import_project`
  (перезаписывает существующий проект), bulk stop/start (широкий радиус
  действия), лицензионные операции (activate/transfer).
- Audit trail: каждый risky-вызов — через `call_risky`-эквивалентный
  паттерн (отдельная явная risky-функция), с описанием последствий в
  самом описании функции.

## 11. Discovery и проверка гипотезы

- Кого интервьюировать: реальные HL7/интеграционные инженеры в клиниках/
  лабораториях, использующие Iguana (не в рамках этой сессии — до pilot).
- Вопросы: готовы ли дать admin-доступ third-party AI-инструменту к
  своему production Iguana-инстансу (compliance/HIPAA concerns);
  используют ли ещё Iguana 6, или уже мигрировали на IguanaX (критично —
  если большинство уже на IguanaX, P0 функция сильно теряет охват).
- Артефакты: анонимизированный пример XML-конфигурации канала.
- Порог: 3-5 интервью до решения расширять ли Ярус 3 value-add отчёты.

## 12. План воплощения и live-критерии

| Срез | Статус |
|---|---|
| Connection management (connect/disconnect/list) | planned |
| Channel CRUD (add/update/remove/get_config/get_default_config) | planned |
| Channel control (status start/stop/startall/stopall, bulk) | planned |
| Monitoring (status report, current_version, monitor_query, api_query log) | planned |
| Source control (sc/commit, sc/bump) | planned |
| Project export/import | planned |
| Licensing (my.interfaceware.com) | planned |
| Value-add отчёты (audit_server, clone_channel, error summary, stopped report) | planned |
| Pricing + submit for review | planned |

### Roadmap — куда развивать дальше и почему

| Priority | Срез | Entry condition |
|---|---|---|
| P1 | Webhook/event уведомления о падении канала (если Iguana когда-либо начнёт поддерживать push-уведомления вовне) | вендор публикует такой механизм — сейчас его нет |
| P2 | IguanaX REST-управление | вендор публикует официальный внешний REST-контракт для IguanaX (сейчас `blocked`, см. §1) |
| P3 | Готовые дашборды/алертинг на основе `audit_server` (интеграция с PagerDuty Connector — уже в портфеле) | 3+ реальных pilot-пользователя просят проактивные алерты, а не pull-запросы |

## 13. Decision log

- 2026-08-22: коннектор строится строго против Iguana 6 HTTP API — не
  IguanaX — по объективной причине отсутствия у IguanaX публичного REST-
  контракта для внешнего управления (см. `CONNECTOR_DISCOVERY.md`).
- 2026-08-22: License API (my.interfaceware.com) — отдельные credentials
  от admin-доступа к инстансу, отдельный secret store.

## 14. Live verification log

_(заполняется после деплоя и ручной проверки в Imperal panel)_
