# humanize-text

Скилл для Claude Code (и других агентов), который заставляет писать текст как живой человек, а не как модель. Русский и английский.

*English: a writing skill that removes AI-writing tells (RU + EN), with a zero-dependency checker script and a fact-preservation diff. Install notes below.*

## Что внутри

| Файл | Зачем |
|---|---|
| `skills/humanize-text/SKILL.md` | Метод: содержание до формы, образец голоса, чек-лист, режим «очеловечь этот текст», когда не вмешиваться |
| `skills/humanize-text/references/patterns.md` | Каталог паттернов с примерами, цифрами (Pangram), эпохами лексики, исследованиями и источниками |
| `skills/humanize-text/scripts/humanize_check.py` | Проверка черновика: маркеры RU+EN, оценка 0–100, сверка фактов до/после правки. Python 3, без зависимостей |
| `adapters/` | Версии под Cursor, Codex/AGENTS.md и инструкции для обычных чатов |

## Чем отличается от других humanizer-скиллов

- **Русский как первый язык.** Штампы, канцелярит, причастные хвосты, кальки, заголовки-двоеточия.
- **Содержание до формы.** Замена слов не лечит пустую фразу, поэтому первым шагом идёт «что именно я хочу сказать» и конкретика вместо оценок.
- **Образец автора главнее правил.** Если человек сам любит тире и тройки, скилл не ломает его голос.
- **Скрипт и сверка фактов.** `compare` ловит потерянные и выдуманные числа, даты, ссылки, версии. Пример в `examples/`: на первой версии правки он поймал две выдуманные цифры.
- **Защита от ложных срабатываний.** Одиночный маркер ничего не значит, детекторы ошибаются, чужую подпись скилл не подделывает.

## Установка

**Claude Code, как плагин**
```
/plugin marketplace add nurdamiron/humanize-text-skill
/plugin install humanize-text@humanize-text
```

**Claude Code, вручную**
```bash
git clone https://github.com/nurdamiron/humanize-text-skill.git
cp -R humanize-text-skill/skills/humanize-text ~/.claude/skills/
```
Чтобы применялось ко всем текстам без вызова, добавь в `~/.claude/CLAUDE.md`:
```
Любой связный текст для человека пишется по скиллу `humanize-text`.
```

**claude.ai (Skills)**: `scripts/build_zip.sh` собирает `dist/humanize-text.zip`. Загрузи его в Settings → Capabilities → Skills (нужен включённый раздел Skills в твоём плане).

**Обычные чаты (claude.ai, ChatGPT, Gemini и т.д.)**: вставь `adapters/chat/instructions-ru.md` в пользовательские инструкции или в инструкции проекта.

**Cursor**: скопируй `adapters/cursor/humanize-text.mdc` в `.cursor/rules/`.

**Codex и агенты с AGENTS.md**: добавь `adapters/codex/AGENTS.snippet.md` в `AGENTS.md` и положи папку `skills/humanize-text` в репозиторий.

## Скрипт

```bash
python3 skills/humanize-text/scripts/humanize_check.py check draft.txt
python3 skills/humanize-text/scripts/humanize_check.py check draft.txt --fail-above 40
python3 skills/humanize-text/scripts/humanize_check.py compare before.txt after.txt
python3 -I -m unittest discover -s tests -v
```

Пример: `examples/before.txt` получает 100/100, `examples/after.txt` 0/100, `compare` подтверждает, что факты не потеряны.

## Ограничения

- Оценка скрипта это эвристика плотности маркеров. Это не детектор авторства и не вердикт.
- Словари маркеров устаревают с каждым поколением моделей. Список эпох в `references/patterns.md` нужно обновлять.
- Часть источников это блоги и сайты, продающие детекторы. Количественные данные только у Pangram и у академической работы Reinhart и др. (2024, GPT-4o и Llama 3).
- Не предназначен для подделки авторства там, где человек обязан писать сам.

## Источники

Wikipedia «Signs of AI writing», Pangram «9 Signs of AI Writing», tropes.fyi, Reinhart и др. arXiv 2410.16107, The Register «Semantic ablation», разборы на iphones.ru, sostav.ru и Habr. Полный список в `references/patterns.md`.

## Лицензия

MIT
