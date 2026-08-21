# Iguana / iNTERFACEWARE Connector — Connector Discovery

**Дата discovery:** 2026-08-21/22
**Статус:** Ярусы 1-3 пройдены по официальной документации
help.interfaceware.com (Iguana 6 HTTP/Web/License API — полностью открытая,
стабильная HTTP-поверхность) и interfaceware.atlassian.net/wiki (IguanaX —
актуальная линейка). Задача #2251 явно заявляла "делай это приложение в
полном максимуме со всеми возможными функциями" — трактуется как "максимум"
(Ярус 1+2+3), по прецеденту GitLab CI/CD/MuleSoft/PagerDuty/Power Automate/
Automation Anywhere/UiPath/Blue Prism, где такая же явная формулировка уже
освобождала от повторного вопроса Владу.

---

## 1. Целевой сервис и источники

Iguana (iNTERFACEWARE) — healthcare/HL7 integration engine: self-hosted
продукт (как GitLab self-managed/UiPath Orchestrator/Blue Prism), не
облачный SaaS с единым API-эндпоинтом. Управляет ЧУЖИМ инстансом клиента —
`base_url` обязан быть параметризуемым полем подключения.

Источники (прочитаны 2026-08-21/22):
- `help.interfaceware.com/v6/http-api-reference` — Iguana 6 HTTP API,
  полный список функций (Channel API + Server API)
- `help.interfaceware.com/web_api/` — тот же API в современной подаче
  (Log/Monitor/Channel/Source Control API)
- `help.interfaceware.com/license_api/` — License API (my.interfaceware.com,
  отдельная от самого инстанса поверхность для активации/переноса лицензий)
- `help.interfaceware.com/kb/1477`, `/kb/1477/2`, `/kb/1477/3` — детальный
  постраничный референс тех же функций с полными сигнатурами параметров
- `interfaceware.atlassian.net/wiki/spaces/IXB` (IguanaX Documentation) —
  актуальная линейка продукта: "Calling IguanaX APIs", "Introduction
  IguanaX's APIs", "Shim functions", "Iguana 6 Channel Importer",
  "Deprecated APIs"

## 2. ⚠️ КРИТИЧЕСКИЙ БЛОКЕР — две несовместимые генерации продукта

Это САМЫЙ важный вывод discovery и прямая причина, почему объём этого
коннектора ограничен ниже, чем "управлять живым IguanaX через REST":

1. **Iguana 6** (легаси, но всё ещё широко используется в проде у клиентов)
   имеет полноценный, стабильный, годами документированный **HTTP API**:
   HTTP Basic Auth на каждый запрос (`auth={username=..., password=...}`),
   набор эндпоинтов вида `POST <base_url>/add_channel`,
   `POST <base_url>/status`, и т.д. Это классический REST-подобный API,
   вызываемый напрямую любым HTTP-клиентом (curl/httpx/requests) — идеальная
   база для BYOK-коннектора.

2. **IguanaX** (текущая, активно развиваемая линейка) **принципиально
   изменила архитектуру**: подтверждено прямым цитированием официальной
   документации ("Iguana 6 Channel Importer", `interfaceware.atlassian.net/
   wiki/spaces/IXB/pages/2646999054`) — *"IguanaX no longer provides
   Iguana 6-style HTTP API endpoints ... because channels don't exist in
   IguanaX"*. IguanaX управляется через:
   - **Lua-скрипты внутри Translator**, вызывающие `iguana.call()` —
     работает ТОЛЬКО изнутри того же самого запущенного инстанса, без
     аутентификации, НЕ вызываемо снаружи как внешний HTTP API;
   - веб-UI IguanaX (браузерная админка) — не документированный публичный
     REST-контракт;
   - временный **`iguana_shim.lua`** — эмулирует часть старых Iguana 6
     HTTP-эндпоинтов ("Shim functions" wiki-страница) для облегчения
     миграции — явно временное, не гарантированное на будущее решение,
     не тот фундамент, на который стоит опираться для нового коннектора в
     2026 году.

**Практический вывод:** внешний, стабильный, официально документированный
HTTP API существует только для **Iguana 6**. Для IguanaX нет опубликованного
REST-контракта, вызываемого извне тем способом, каким работают все
остальные коннекторы Imperal (httpx/ctx.http против чужого base_url).
Пытаться реализовать "полное управление IguanaX" означало бы либо
полагаться на недокументированный веб-UI (хрупко, может сломаться на любом
обновлении, не является контрактом), либо на temporary shim (не гарантирован
вендором).

**Решение по объёму:** коннектор строится против **Iguana 6 HTTP API**
(полностью документированная, стабильная поверхность) — это ОБЪЕКТИВНАЯ
техническая граница возможностей сервиса, а не недоработка коннектора.
Пользователю в UI явно указывается: "работает с Iguana 6 (классический HTTP
API); IguanaX пока не предоставляет публичный REST API для внешнего
управления — Imperal не может обойти это ограничение вендора". Это отражено
в `app.py` описании и будет зафиксировано отдельным пунктом FAQ в панели.

## 3. Классификация функционала (по CONNECTOR_DISCOVERY_STANDARD.md)

| Функция | Тип | Ярус |
|---|---|---|
| `add_channel` | Egress | 1 |
| `update_channel` | Egress | 1 |
| `remove_channel` | Egress | 1 |
| `get_channel_config` | Ingress | 1 |
| `get_default_config` | Ingress | 1 |
| `status` (report) | Ingress | 1 |
| `status` (action=start/stop/startall/stopall) | Egress | 1 |
| `current_version` | Ingress | 1 |
| `get_server_config` | Ingress | 2 |
| `get_server_salt` | Ingress | 2 |
| `monitor_query` | Ingress | 2 |
| `api_query` (log query) | Ingress | 2 |
| `export_project` | Ingress | 2 |
| `import_project` | Egress | 2 |
| `save_project_milestone` | Egress | 2 |
| `sc/commit` (source control commit) | Egress | 2 |
| `sc/bump` (source control bump) | Egress | 2 |
| License API: `session.login` | Egress (auth) | 2 |
| License API: `license.listentitlements` | Ingress | 2 |
| License API: `license.activate` | Egress | 2 |
| License API: `license.listActivations` | Ingress | 2 |
| License API: `license.UpdateActivationInfo` (transfer) | Egress | 2 |
| License API: `GET /license/detail` (instance details) | Ingress | 2 |
| License API: `POST /license/update` (apply license) | Egress | 2 |
| Value-add: audit_server (aggregate status+monitor+version) | Both (нами) | 3 |
| Value-add: bulk_start_channels / bulk_stop_channels | Egress (нами) | 3 |
| Value-add: clone_channel (get_channel_config→rename→add_channel) | Egress (нами) | 3 |
| Value-add: get_stopped_channels_report | Ingress (нами) | 3 |
| Value-add: get_channel_error_summary (api_query type=errors, per channel) | Ingress (нами) | 3 |

## 4. Авторизация

**Iguana 6 instance connection:** HTTP Basic Auth per-request
(`username`+`password` sent as `auth=` param on every call, confirmed
across every example in help.interfaceware.com). No token/OAuth. Stored as
BYOK pair (username+password) per connection, same JSON-array-of-connections
shape as GitLab CI/CD/PagerDuty/MuleSoft. `base_url` includes host+port
(default port 6543, confirmed in every doc example).

**License API (my.interfaceware.com):** separate surface, separate
credentials (my.interfaceware.com account username/password, NOT the
instance's admin credentials) → `session.login` returns a session token
used on subsequent `license.*` calls. Stored as a SEPARATE optional secret
(`iguana_license_credentials`), same pattern as PagerDuty's separate
Integration Keys store — a user may manage Iguana instances without ever
touching the License API, so it must not be forced into the same connect
flow.

## 5. Решение об объёме релиза

Ярус 1 + Ярус 2 + Ярус 3 — полный охват документированной Iguana 6 HTTP/
Web/License API поверхности плюс value-add агрегаты, как явно указано в
задаче #2251 ("полный максимум"). IguanaX-специфичное "живое" REST-
управление сознательно исключено по причине §2 (объективное отсутствие
публичного контракта у вендора) — не пропуск функциональности, а честная
граница того, что сервис в принципе предоставляет извне сегодня.
