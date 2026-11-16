#!/usr/bin/env bash
# Сторож CI (4-15-49 → 4-17-35): упавший workflow на main → задача в Bitrix24; повтор → сообщение
# в ту же задачу; зелёный запуск → сообщение «восстановлено» (задачу закрывает человек).
#
# Данные события читаются из $GITHUB_EVENT_PATH через jq — НЕ через ${{ }} в run:
# (сообщение коммита — свободный текст, подстановка в shell = инъекция).
# URL вебхука никуда не печатается: ни в лог, ни в DRY_RUN.
#
# Окружение:
#   BITRIX24_CI_WEBHOOK         секрет, входящий вебхук вида https://<portal>/rest/<uid>/<token>/
#   BITRIX24_CI_GROUP_ID        группа задач CI
#   BITRIX24_CI_RESPONSIBLE_ID  ответственный
#   GH_TOKEN                    для `gh run view` (список упавших jobs)
#   TEST_CONCLUSION             workflow_dispatch-смоук: failure | success
#   DRY_RUN=1                   печатать метод и тело вместо вызова
#   DRY_RUN_OPEN_TASK_ID        только DRY_RUN: имитировать найденную открытую задачу
#
# Комментарии пишутся в ЧАТ задачи (REST v3 tasks.task.chat.message.send, путь /rest/api/):
# форумный task.comment.add в интерфейсе задачи не виден (bitrix24-mcp, 4-23-13).
set -euo pipefail

die() { echo "::error::$*" >&2; exit 1; }

for v in BITRIX24_CI_WEBHOOK BITRIX24_CI_GROUP_ID BITRIX24_CI_RESPONSIBLE_ID; do
  [ -n "${!v:-}" ] || die "не задан ${v} (Settings → Secrets and variables → Actions)"
done
[ -n "${GITHUB_EVENT_PATH:-}" ] && [ -f "$GITHUB_EVENT_PATH" ] || die "нет файла события GITHUB_EVENT_PATH"

webhook="${BITRIX24_CI_WEBHOOK%/}/"
case "$webhook" in
  */rest/*) ;;
  *) die "BITRIX24_CI_WEBHOOK не похож на входящий вебхук Bitrix24 (нет /rest/)" ;;
esac
# v3: /rest/<uid>/<token>/ → /rest/api/<uid>/<token>/. Производная строка — уже не подстрока
# секрета, GitHub её сам не замаскирует; маскируем явно (и токен отдельно).
webhook_v3="${webhook%%/rest/*}/rest/api/${webhook#*/rest/}"
token="${webhook#*/rest/}"; token="${token#*/}"; token="${token%/}"
if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
  echo "::add-mask::${webhook_v3}"
  [ -n "$token" ] && echo "::add-mask::${token}"
fi

repo_full="${GITHUB_REPOSITORY:?}"
repo="${repo_full#*/}"

# --- данные запуска ---------------------------------------------------------------------
if [ -n "${TEST_CONCLUSION:-}" ]; then
  # Ручной смоук: тестовые данные, отдельный заголовок, рабочие workflow не роняем.
  smoke=1
  wf_name="CI"
  conclusion="$TEST_CONCLUSION"
  run_url="${GITHUB_SERVER_URL:-https://github.com}/${repo_full}/actions/runs/${GITHUB_RUN_ID:-0}"
  head_sha="${GITHUB_SHA:-0000000}"
  commit_msg="smoke test (workflow_dispatch)"
  event="workflow_dispatch"
  actor="${GITHUB_ACTOR:-unknown}"
  attempt="${GITHUB_RUN_ATTEMPT:-1}"
  run_id=""
else
  smoke=0
  ev() { jq -r "$1 // \"\"" "$GITHUB_EVENT_PATH"; }
  wf_name="$(ev '.workflow_run.name')"
  conclusion="$(ev '.workflow_run.conclusion')"
  run_url="$(ev '.workflow_run.html_url')"
  head_sha="$(ev '.workflow_run.head_sha')"
  commit_msg="$(jq -r '(.workflow_run.head_commit.message // "") | split("\n")[0]' "$GITHUB_EVENT_PATH")"
  event="$(ev '.workflow_run.event')"
  actor="$(ev '.workflow_run.actor.login')"
  attempt="$(ev '.workflow_run.run_attempt')"
  run_id="$(ev '.workflow_run.id')"
fi

case "$conclusion" in
  failure|timed_out|startup_failure) mode=fail ;;
  success) mode=ok ;;
  *) echo "conclusion=${conclusion}: игнор"; exit 0 ;;
esac

if [ "$smoke" = 1 ]; then
  title="[CI-SMOKE] ${repo}: ${wf_name} упал на main"
else
  title="[CI] ${repo}: ${wf_name} упал на main"
fi

failed_jobs="smoke-job (${conclusion})"
if [ -n "$run_id" ] && [ "$mode" = fail ]; then
  failed_jobs="$(gh run view "$run_id" --repo "$repo_full" --json jobs \
    -q '.jobs[] | select(.conclusion != "success" and .conclusion != "skipped" and .conclusion != "neutral") | "\(.name) (\(.conclusion))"' \
    2>/dev/null)" || failed_jobs=""
  [ -n "$failed_jobs" ] || failed_jobs="(не удалось получить список jobs — см. ссылку на run)"
fi
short_sha="${head_sha:0:7}"
now_utc="$(jq -rn 'now | strftime("%Y-%m-%d %H:%M UTC")')"

# --- вызов Bitrix24 ---------------------------------------------------------------------
# bx <v2|v3> <method> <json-body> → печатает JSON ответа. URL передаётся curl через stdin
# (-K -), чтобы не светиться в списке процессов; при ошибке — код ошибки, без URL.
bx() {
  local ver="$1" method="$2" body="$3" base resp code
  if [ "${DRY_RUN:-}" = 1 ]; then
    echo "DRY_RUN ${ver} ${method}" >&2
    jq . <<<"$body" >&2
    case "$method" in
      tasks.task.list)
        if [ -n "${DRY_RUN_OPEN_TASK_ID:-}" ]; then
          jq -n --arg id "$DRY_RUN_OPEN_TASK_ID" --arg t "$title" '{result:{tasks:[{id:$id,title:$t}]}}'
        else
          echo '{"result":{"tasks":[]}}'
        fi ;;
      tasks.task.add) echo '{"result":{"task":{"id":"0"}}}' ;;
      *) echo '{"result":{"result":true}}' ;;
    esac
    return 0
  fi
  if [ "$ver" = v3 ]; then base="$webhook_v3"; else base="$webhook"; fi
  resp="$(printf 'url = "%s%s"\n' "$base" "$method" | curl -sS --max-time 30 -K - \
    -X POST -H 'Content-Type: application/json' --data "$body" -w '\n%{http_code}')" \
    || die "Bitrix24 ${method}: сетевая ошибка curl"
  code="${resp##*$'\n'}"
  resp="${resp%$'\n'*}"
  local err
  err="$(jq -r 'if type == "object" and has("error") then (if (.error|type) == "object" then (.error.code // "unknown") else .error end) else "" end' <<<"$resp" 2>/dev/null || echo "invalid_json")"
  if [ "$code" != 200 ] || [ -n "$err" ]; then
    die "Bitrix24 ${method}: HTTP ${code}, error=${err:-none}"
  fi
  printf '%s\n' "$resp"
}

# BBCode: в описании задачи — HTML-сущности, в чате — ZWSP после «[» (сущности чат декодирует).
esc_desc() { sed -e 's/\[/\&#91;/g' -e 's/\]/\&#93;/g'; }
zwsp="$(printf '\342\200\213')"
esc_chat() { sed -e "s/\\[/[${zwsp}/g"; }

# --- дедуп: открытая задача с тем же заголовком -----------------------------------------
list_body="$(jq -n --arg t "$title" --argjson g "$BITRIX24_CI_GROUP_ID" \
  '{filter:{GROUP_ID:$g, TITLE:$t, "!STATUS":5}, select:["ID","TITLE"]}')"
# Фильтр TITLE может работать как LIKE — точное совпадение проверяем сами.
open_id="$(bx v2 tasks.task.list "$list_body" | jq -r --arg t "$title" \
  '[.result.tasks[]? | select((.title // .TITLE) == $t) | (.id // .ID)] | first // ""')"

chat_send() {
  local body
  body="$(jq -n --argjson id "$1" --arg text "$(esc_chat <<<"$2")" '{fields:{taskId:$id, text:$text}}')"
  bx v3 tasks.task.chat.message.send "$body" \
    | jq -e '.result.result == true' >/dev/null || die "Bitrix24 chat.message.send: result != true"
}

if [ "$mode" = ok ]; then
  if [ -n "$open_id" ]; then
    chat_send "$open_id" "✅ Зелёный запуск: ${run_url}"
    echo "Задача ${open_id}: отмечено восстановление"
  else
    echo "Открытой задачи нет — нечего отмечать"
  fi
  exit 0
fi

details="Run: ${run_url}
Коммит: ${short_sha} — ${commit_msg}
Событие: ${event}, запустил: ${actor}, попытка: ${attempt}
Упавшие jobs:
${failed_jobs}"

if [ -n "$open_id" ]; then
  chat_send "$open_id" "❌ Повторное падение ${now_utc}
${details}"
  echo "Задача ${open_id}: добавлено сообщение о повторном падении"
  exit 0
fi

description="Репозиторий: ${repo_full}
Workflow: ${wf_name} (${conclusion})
${details}

Классифицировать по СМК-40-07 п.7: critical — 24 ч, high — 14 дн., medium — 30 дн."

tags='["ci"]'
[ "$wf_name" = security ] && tags='["ci","security"]'

add_body="$(jq -n \
  --arg t "$title" \
  --arg d "$(esc_desc <<<"$description")" \
  --argjson g "$BITRIX24_CI_GROUP_ID" \
  --argjson r "$BITRIX24_CI_RESPONSIBLE_ID" \
  --argjson tags "$tags" \
  '{fields:{TITLE:$t, DESCRIPTION:$d, GROUP_ID:$g, RESPONSIBLE_ID:$r,
            DEADLINE:(now + 86400 | strftime("%Y-%m-%dT%H:%M:%S+00:00")), TAGS:$tags}}')"
new_id="$(bx v2 tasks.task.add "$add_body" | jq -r '.result.task.id // empty')"
[ -n "$new_id" ] || die "Bitrix24 tasks.task.add: в ответе нет id задачи"
echo "Создана задача ${new_id}"
