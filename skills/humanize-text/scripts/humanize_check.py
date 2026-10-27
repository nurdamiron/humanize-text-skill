#!/usr/bin/env python3
"""humanize_check: детерминированная проверка текста на маркеры ИИ-письма (RU + EN).

Без зависимостей, только стандартная библиотека Python 3.8+.

  humanize_check.py check FILE|-            найти маркеры, показать вхождения и оценку
  humanize_check.py check FILE --json       то же в JSON
  humanize_check.py check FILE --fail-above 40
  humanize_check.py compare ORIG REWRITE    проверить, что правка не потеряла и не добавила факты

Оценка 0-100 это эвристика плотности маркеров, а не вердикт об авторстве.
Скопление маркеров значимо, одиночный маркер нет.
"""
import argparse
import json
import math
import re
import statistics
import sys

# ---------------------------------------------------------------- словари

# (категория, вес, список regex). Регистр игнорируется.
PHRASES = [
    ("chat-opener", 3, [
        r"\b(отличный|хороший|интересный|замечательный|прекрасный) вопрос\b",
        r"\bвы (абсолютно|совершенно|полностью) правы\b",
        r"^\s*(конечно|разумеется|безусловно|certainly|absolutely|sure)[!,]",
        r"\bрад(а)? помочь\b",
        r"\bgreat question\b", r"\byou'?re absolutely right\b", r"\bexcellent (point|question)\b",
        r"\bi'?d be happy to\b", r"\bhere'?s (a|the|what)\b[^.\n]{0,40}:\s*$",
    ]),
    ("chat-closer", 3, [
        r"\bнадеюсь, (это|эта информация|мой ответ) (поможет|была? полезн)",
        r"\bдайте знать, если\b", r"\bне стесняйтесь\b", r"\bобращайтесь, если\b",
        r"\bi hope this helps\b", r"\blet me know if\b", r"\bfeel free to\b",
        r"\bis there anything else\b",
    ]),
    ("announce-summary", 2, [
        r"\bтаким образом\b", r"\bподводя итог", r"\bв заключение\b", r"\bрезюмируя\b",
        r"\bиз вышесказанного (следует|видно)", r"\bв итоге мы видим\b",
        r"\bin conclusion\b", r"\bin summary\b", r"\bto sum up\b", r"\boverall,",
        r"\bдавайте (разберёмся|разберемся|погрузимся|углубимся|рассмотрим|разберем|разберём)",
        r"\blet'?s (dive|delve|break|unpack|explore)\b",
        r"\bсегодня (поговорим|разберём|разберем)\b",
    ]),
    ("filler-framing", 2, [
        r"\bстоит (отметить|подчеркнуть|упомянуть)\b", r"\bследует (отметить|подчеркнуть|учитывать)\b",
        r"\bважно (понимать|помнить|отметить|подчеркнуть|учитывать)\b",
        r"\bнельзя не (отметить|упомянуть|сказать)\b", r"\bне стоит забывать\b",
        r"\bit'?s (important|worth|crucial) (to note|noting|to remember)\b",
        r"\bit bears mentioning\b", r"\b(importantly|notably|interestingly),",
    ]),
    ("cliche-intro", 3, [
        r"\bв современном мире\b", r"\bв эпоху\b", r"\bв наше время\b", r"\bна сегодняшний день\b",
        r"\bс развитием (технологий|цифровизации)\b", r"\bв условиях\b[^.]{0,30}\b(цифровизаци|глобализаци)",
        r"\bin today'?s (fast-paced|digital|modern|ever-changing)\b", r"\bin the (ever-evolving|rapidly evolving) (world|landscape)\b",
    ]),
    ("inflated-significance", 2, [
        r"\bиграет (ключевую|важную|решающую|значительную) роль\b",
        r"\bнеотъемлемая часть\b", r"\bключевой (момент|фактор|элемент)\b",
        r"\b(служит|выступает|является) (напоминанием|свидетельством|символом|ярким примером)\b",
        r"\b(знаменует|представляет собой) (собой )?(сдвиг|переломный|важный шаг)",
        r"\bоставил(а|о|и)? неизгладимый след\b", r"\bбеспрецедентн", r"\bкардинально (изменит|меняет)",
        r"\b(stands|serves) as (a|an|the)\b", r"\ba testament to\b", r"\bpivotal\b", r"\bunderscores?\b",
        r"\bevolving landscape\b", r"\bsetting the stage\b", r"\bgame-?changer\b", r"\bgroundbreaking\b",
        r"\bindelible mark\b", r"\bplays? a (crucial|vital|key|pivotal) role\b",
    ]),
    ("promo-adjective", 1, [
        r"\bзахватывающ", r"\bуникальн(ый|ая|ое|ые)\b", r"\bбогат(ый|ая|ое|ые) (наследие|история|культура|опыт)",
        r"\bславится\b", r"\bширокий спектр\b", r"\bкомплексный подход\b", r"\bвысококачественн",
        r"\bvibrant\b", r"\brich tapestry\b", r"\bboasts?\b", r"\bnestled\b", r"\brenowned\b",
        r"\bseamless(ly)?\b", r"\brobust\b", r"\bdiverse array\b", r"\bcutting-edge\b",
    ]),
    ("ai-vocabulary", 2, [
        r"\bdelve[sd]?\b", r"\btapestry\b", r"\bintricate\b", r"\binterplay\b", r"\bmeticulous(ly)?\b",
        r"\bleverag(e|es|ed|ing)\b", r"\bfoster(s|ed|ing)?\b", r"\bmultifaceted\b", r"\butiliz(e|es|ed|ing)\b",
        r"\bharness(es|ed|ing)?\b", r"\bstreamlin(e|es|ed|ing)\b", r"\bnavigat(e|es|ing) the (complexit|landscape)",
        r"\bлеверидж", r"\bландшафт\b", r"\bэкосистем[аыеу]\b", r"\bсинерги", r"\bпарадигм",
        r"\bмногогранн", r"\bбесшовн", r"\bосуществлять\b", r"\bобеспечивать\b",
    ]),
    ("magic-adverb", 1, [
        r"\bпо-настоящему\b", r"\bдействительно\b", r"\bглубоко\b", r"\bфундаментально\b",
        r"\bquietly\b", r"\btruly\b", r"\bfundamentally\b", r"\bremarkably\b", r"\barguably\b",
    ]),
    ("vague-attribution", 2, [
        r"\bэксперты (считают|отмечают|утверждают|предупреждают)\b",
        r"\b(исследования|аналитики|наблюдатели|специалисты) (показывают|отмечают|считают|утверждают)\b",
        r"\bпо мнению (экспертов|аналитиков|наблюдателей)\b", r"\bкак известно\b",
        r"\b(experts|observers|critics|researchers) (argue|say|note|suggest)\b",
        r"\bstudies (show|suggest|indicate)\b", r"\bindustry reports\b",
    ]),
    ("data-gap-hedge", 2, [
        r"\bв (доступных|предоставленных) (источниках|данных)\b", r"\bна основании (имеющейся|доступной) информации\b",
        r"\bподробности (ограничены|не раскрываются)\b", r"\bне (является )?общедоступн",
        r"\bbased on (the )?available (information|sources)\b", r"\bnot (widely|publicly) (available|documented)\b",
        r"\bas of my last (knowledge )?update\b", r"\bas an ai\b", r"\bкак (языковая модель|ии-?ассистент)\b",
    ]),
    ("copula-dodge", 1, [
        r"\bвыступает (в роли|как)\b", r"\bпредставляет собой\b", r"\bserves as\b", r"\bfunctions as\b", r"\bstands as\b",
    ]),
    ("despite-challenges", 2, [
        r"\bнесмотря на (эти |все )?(трудности|вызовы|сложности)[^.]{0,60}(продолжает|остаётся|остается)",
        r"\bdespite (these|its|the) (challenges|obstacles)[^.]{0,80}(continues|remains|thrives)",
    ]),
    ("rhetorical-hook", 2, [
        r"\bвот в чём (подвох|дело|фишка|секрет)\b", r"\bвот что (интересно|важно)\b",
        r"\bпредставьте (себе )?(мир|ситуацию)\b", r"\bhere'?s the (kicker|thing|catch|truth)\b",
        r"\bimagine a world\b", r"\bthink of it as\b", r"\bчто\?\s",
    ]),
]

# Негативный параллелизм и родственные формулы.
NEG_PARALLEL = [
    r"\bне только\b[^.!?\n]{2,90}?,?\s*но\s+(и|также)\b",
    r"\bне просто\b[^.!?\n]{2,70}?,?\s*а\b",
    r"\bэто не\b[^.!?\n]{2,70}?[,;:—–-]\s*(это|а)\b",
    r"\bне\s+[^.!?\n,]{2,30}\.\s*не\s+[^.!?\n,]{2,30}\.\s*(а\s+)?[А-ЯЁA-Z]",
    r"\bnot (just|only|merely|simply)\b[^.!?\n]{2,80}?,?\s*(but|it'?s|—)",
    r"\bit'?s not\b[^.!?\n]{2,70}?[,;:—–-]\s*it'?s\b",
    r"\b(isn'?t|aren'?t|wasn'?t|is not|are not)\s+(just|only|merely|simply)\b[^.!?\n]{2,70}?[,;:—–-]\s*(it'?s|but|they'?re)\b",
    r"\bnot\s+[^.!?\n,]{2,25}\.\s*not\s+[^.!?\n,]{2,25}\.\s*(just\s+)?[A-Z]",
]

PARTICIPLE_TAIL = [
    r",\s*(обеспечивая|подчёркивая|подчеркивая|отражая|способствуя|выделяя|демонстрируя|формируя|создавая|укрепляя)\b",
    r",\s*(highlighting|underscoring|emphasizing|showcasing|fostering|ensuring|reflecting|contributing to|enhancing|cultivating)\b",
]

RHETORICAL_QA = r"(?<![А-Яа-яЁёA-Za-z])[А-ЯЁA-Z][а-яёa-z]{2,20}\?\s+[А-ЯЁA-Z][а-яёa-z]{2,25}\.(?=\s|$)"

EMOJI_MARKS = "✅❌🚀💡🔑📌⚡🎯✨🔥📈⚠️👉"
UNICODE_DECOR = "→≈≥≤⇒─━"

SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+(?=[\"«“(\[]?[A-ZА-ЯЁ0-9])")
WORD = re.compile(r"[\w'’-]+", re.UNICODE)


# ---------------------------------------------------------------- разбор

def words(text):
    return WORD.findall(text)


def sentences(text):
    plain = re.sub(r"^[#>\-*•\s\d.]+(?=\S)", "", text, flags=re.M)
    out = []
    for para in re.split(r"\n\s*\n", plain):
        para = para.strip().replace("\n", " ")
        if para:
            out.extend(s.strip() for s in SENT_SPLIT.split(para) if s.strip())
    return out


def paragraphs(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def line_no(text, pos):
    return text.count("\n", 0, pos) + 1


def find_all(pattern, text, flags=re.I | re.M):
    return [(m.start(), m.group(0).strip()) for m in re.finditer(pattern, text, flags)]


def em_dashes(text):
    """Длинное тире не в начале строки (диалог в русской прозе не считаем)."""
    hits = []
    for m in re.finditer(r"—|\s--\s|\s–\s", text):
        start = m.start()
        line_start = text.rfind("\n", 0, start) + 1
        if text[line_start:start].strip() == "":
            continue  # тире открывает строку: реплика диалога
        hits.append((start, m.group(0).strip() or "—"))
    return hits


# ---------------------------------------------------------------- проверка

def check(text):
    wc = max(len(words(text)), 1)
    signals = []  # (category, weight, [(line, snippet)])

    def add(cat, weight, hits):
        if hits:
            signals.append({
                "category": cat,
                "weight": weight,
                "count": len(hits),
                "examples": [{"line": line_no(text, p), "text": s[:90]} for p, s in hits[:6]],
            })

    for cat, weight, patterns in PHRASES:
        hits = []
        for pat in patterns:
            hits.extend(find_all(pat, text))
        add(cat, weight, sorted(set(hits)))

    hits = []
    for pat in NEG_PARALLEL:
        hits.extend(find_all(pat, text))
    add("negative-parallelism", 3, sorted(set(hits)))

    hits = []
    for pat in PARTICIPLE_TAIL:
        hits.extend(find_all(pat, text))
    add("significance-tail", 2, sorted(set(hits)))

    add("rhetorical-question-answer", 2, find_all(RHETORICAL_QA, text, 0))
    add("long-dash", 1, em_dashes(text))

    # Markdown и декор
    add("markdown-bold", 2, find_all(r"\*\*[^*\n]{1,80}\*\*", text, 0))
    add("markdown-heading", 2, find_all(r"^#{1,6}\s+\S.*$", text))
    add("markdown-rule", 1, find_all(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$", text))
    bullets = find_all(r"^\s*([-*•]|\d+[.)])\s+\S.*$", text)
    if len(bullets) >= 3:
        add("bullet-list", 1, bullets)
    emoji = [(i, ch) for i, ch in enumerate(text) if ch in EMOJI_MARKS]
    add("emoji-marks", 2, emoji)
    add("unicode-decor", 1, [(i, ch) for i, ch in enumerate(text) if ch in UNICODE_DECOR])
    add("title-case-heading", 1, find_all(r"^#{1,6}\s+(?:[A-Z][a-z]+\s+){3,}[A-Z][a-z]+\s*$", text, re.M))
    add("bold-first-bullets", 2, find_all(r"^\s*([-*•]|\d+[.)])\s+\*\*[^*]+\*\*", text))

    sents = sentences(text)
    lens = [len(words(s)) for s in sents]

    # Ритм: короткие фрагменты подряд
    frag_runs, run = [], 0
    for i, n in enumerate(lens):
        run = run + 1 if n <= 4 else 0
        if run == 3:
            frag_runs.append((text.find(sents[i]), sents[i]))
    add("fragment-run", 2, frag_runs)

    # Анафора: одинаковое первое слово у 3+ подряд идущих предложений
    ana, streak = [], 1
    for i in range(1, len(sents)):
        a = (words(sents[i]) or [""])[0].lower()
        b = (words(sents[i - 1]) or [""])[0].lower()
        streak = streak + 1 if a and a == b else 1
        if streak == 3:
            ana.append((text.find(sents[i]), sents[i]))
    add("anaphora", 2, ana)

    # Заключение-пересказ в последнем абзаце
    paras = paragraphs(text)
    if len(paras) >= 3 and re.match(
        r"(таким образом|в заключение|подводя итог|итак|в итоге|резюмируя|in conclusion|in summary|overall|to sum up)",
        paras[-1], re.I,
    ):
        add("summary-closer", 3, [(text.rfind(paras[-1]), paras[-1][:60])])

    # Тройки: «A, B и C» с короткими однотипными элементами
    triads = find_all(
        r"\b[\w-]{3,18},\s[\w-]{3,18}(,)?\s(и|and|или|or)\s[\w-]{3,18}\b", text, re.I)
    if len(triads) >= 3:
        add("triad-density", 1, triads)

    metrics = {}
    if len(sents) >= 8:
        cv = statistics.pstdev(lens) / (statistics.mean(lens) or 1)
        metrics["sentence_length_cv"] = round(cv, 2)
        if cv < 0.35:
            signals.append({"category": "uniform-rhythm", "weight": 2, "count": 1,
                            "examples": [{"line": 0, "text": f"коэффициент вариации длины предложений {cv:.2f} (<0.35)"}]})
    if len(paras) >= 4:
        plens = [len(words(p)) for p in paras]
        pcv = statistics.pstdev(plens) / (statistics.mean(plens) or 1)
        metrics["paragraph_length_cv"] = round(pcv, 2)
        if pcv < 0.2:
            signals.append({"category": "uniform-paragraphs", "weight": 1, "count": 1,
                            "examples": [{"line": 0, "text": f"абзацы почти одной длины (cv {pcv:.2f})"}]})
    if wc >= 120:
        lw = [w.lower() for w in words(text)]
        ttr = len(set(lw)) / len(lw)
        metrics["type_token_ratio"] = round(ttr, 2)

    metrics["words"] = wc
    metrics["sentences"] = len(sents)

    points = sum(s["weight"] * min(s["count"], 5) for s in signals)
    per_500 = points * 500 / max(wc, 250)
    score = round(100 * (1 - math.exp(-per_500 / 14)))
    return {"score": score, "metrics": metrics, "signals": sorted(signals, key=lambda s: -s["weight"] * s["count"])}


def verdict(score):
    if score < 15:
        return "чисто"
    if score < 35:
        return "есть отдельные маркеры"
    if score < 60:
        return "заметный ИИ-почерк"
    return "сильный ИИ-почерк"


def print_report(r):
    m = r["metrics"]
    print(f"Оценка: {r['score']}/100 ({verdict(r['score'])}). Слов: {m['words']}, предложений: {m['sentences']}")
    extra = [f"{k}={v}" for k, v in m.items() if k not in ("words", "sentences")]
    if extra:
        print("Метрики: " + ", ".join(extra))
    if not r["signals"]:
        print("Маркеров не найдено.")
        return
    print("Маркеры (по значимости):")
    for s in r["signals"]:
        print(f"  - {s['category']} x{s['count']} (вес {s['weight']})")
        for ex in s["examples"][:3]:
            where = f"стр.{ex['line']}: " if ex["line"] else ""
            print(f"      {where}{ex['text']}")
    print("Оценка это эвристика плотности маркеров, не вердикт об авторстве.")


# ---------------------------------------------------------------- сравнение фактов

FACT_PATTERNS = {
    "url": r"https?://[^\s)>\]\"']+",
    "email": r"[\w.+-]+@[\w-]+\.[\w.-]+",
    "date": r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b",
    "version": r"\bv?\d+\.\d+(?:\.\d+)+\b",
    "percent": r"\d+(?:[.,]\d+)?\s?%",
    "number": r"(?<![\w.])\d[\d\s ]*(?:[.,]\d+)?(?![\w])",
}


def extract_facts(text):
    facts, work = {}, text
    for kind, pat in FACT_PATTERNS.items():
        found = re.findall(pat, work)
        facts[kind] = sorted({re.sub(r"[\s ]+", "", f) for f in found})
        work = re.sub(pat, " ", work)
    return facts


def compare(orig, rewrite):
    a, b = extract_facts(orig), extract_facts(rewrite)
    lost = {k: sorted(set(a[k]) - set(b[k])) for k in a}
    added = {k: sorted(set(b[k]) - set(a[k])) for k in a}
    lost = {k: v for k, v in lost.items() if v}
    added = {k: v for k, v in added.items() if v}
    wa, wb = len(words(orig)), len(words(rewrite))
    return {"lost": lost, "added": added, "words_before": wa, "words_after": wb,
            "ok": not lost and not added}


# ---------------------------------------------------------------- CLI

def read(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as f:
        return f.read()


def main(argv=None):
    p = argparse.ArgumentParser(description="Проверка текста на маркеры ИИ-письма (RU+EN)")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="найти маркеры")
    c.add_argument("file")
    c.add_argument("--json", action="store_true")
    c.add_argument("--fail-above", type=int, default=None, help="код 1, если оценка выше порога")
    d = sub.add_parser("compare", help="сверить факты до и после правки")
    d.add_argument("original")
    d.add_argument("rewrite")
    d.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    if args.cmd == "check":
        r = check(read(args.file))
        if args.json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        else:
            print_report(r)
        return 1 if args.fail_above is not None and r["score"] > args.fail_above else 0

    r = compare(read(args.original), read(args.rewrite))
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"Слов: {r['words_before']} -> {r['words_after']}")
        if r["ok"]:
            print("Факты (числа, даты, ссылки, версии) совпадают.")
        for k, v in r["lost"].items():
            print(f"ПОТЕРЯНО {k}: {', '.join(v)}")
        for k, v in r["added"].items():
            print(f"ДОБАВЛЕНО {k}: {', '.join(v)}")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
