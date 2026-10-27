import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "humanize-text", "scripts"))
import humanize_check as hc  # noqa: E402


def fx(name):
    with open(os.path.join(HERE, "fixtures", name), encoding="utf-8") as f:
        return f.read()


def cats(r):
    return {s["category"] for s in r["signals"]}


class CheckTests(unittest.TestCase):
    def test_human_text_is_clean(self):
        r = hc.check(fx("human_ru.txt"))
        self.assertLess(r["score"], 15)
        self.assertEqual(r["signals"], [])

    def test_ai_ru_is_flagged(self):
        r = hc.check(fx("ai_ru.txt"))
        self.assertGreater(r["score"], 60)
        for c in ("negative-parallelism", "chat-closer", "cliche-intro", "summary-closer",
                  "rhetorical-question-answer", "significance-tail", "bold-first-bullets"):
            self.assertIn(c, cats(r))
        self.assertNotIn("data-gap-hedge", cats(r))  # «Как ИИ» в заголовке не маркер

    def test_ai_en_is_flagged(self):
        r = hc.check(fx("ai_en.txt"))
        self.assertGreater(r["score"], 60)
        for c in ("chat-opener", "negative-parallelism", "ai-vocabulary", "inflated-significance"):
            self.assertIn(c, cats(r))

    def test_isnt_just_form(self):
        r = hc.check("AI isn't just a tool, it's a shift in how we work every day.")
        self.assertIn("negative-parallelism", cats(r))

    def test_dialogue_dash_not_counted(self):
        text = "— Привет, как дела?\n— Нормально, работаю.\n— Ну и отлично."
        self.assertNotIn("long-dash", cats(hc.check(text)))

    def test_inline_dash_counted(self):
        self.assertIn("long-dash", cats(hc.check("Проблема — в том, что никто не проверил.")))

    def test_single_marker_stays_low(self):
        r = hc.check("Сегодня я проверил поставку. Стоит отметить, что один контейнер пришёл с задержкой. "
                     "Остальное в порядке, документы в папке.")
        self.assertLess(r["score"], 35)


class CompareTests(unittest.TestCase):
    def test_same_facts(self):
        r = hc.compare("Цена 14 800 $ до 15.11.2026, см. https://a.kz/x", "До 15.11.2026 цена 14 800 $: https://a.kz/x")
        self.assertTrue(r["ok"], r)

    def test_lost_and_added(self):
        r = hc.compare("Рост 12% за 2025 год, версия 2.4.1", "Рост 15% за 2025 год")
        self.assertFalse(r["ok"])
        self.assertIn("percent", r["lost"])
        self.assertIn("version", r["lost"])
        self.assertIn("percent", r["added"])


if __name__ == "__main__":
    unittest.main()
