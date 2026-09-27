"""Card states and theme rules, run offscreen (no window appears).

Skipped when PyQt6 isn't installed; CI installs it via requirements.txt.
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt6.QtWidgets import QApplication
except ImportError:  # pragma: no cover
    QApplication = None

from vaultsoft_hub.models import AppEntry


def _app(**kw):
    fields = dict(id="wavescout", name="WaveScout", repo="VaultSoft/WaveScout",
                  category="Network", description="Wi-Fi analyser.", icon="wavescout.svg")
    fields.update(kw)
    return AppEntry(**fields)


@unittest.skipIf(QApplication is None, "PyQt6 not installed")
class CardStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from vaultsoft_hub.ui.styles import STYLESHEET

        cls.qapp = QApplication.instance() or QApplication([])
        cls.qapp.setStyleSheet(STYLESHEET)

    def _card(self, **kw):
        from vaultsoft_hub.ui.app_card import AppCard

        card = AppCard(_app(**kw))
        self.addCleanup(card.deleteLater)
        return card

    def _pills(self, card):
        return [(w.property("kind"), w.text()) for w in card.findChildren(type(card.status_label), "Pill")
                if not w.isHidden() and w.parent() is card]

    def _status_colour(self, card):
        return card.status_label.palette().color(card.status_label.foregroundRole()).name().lower()

    def test_error_after_installed_is_not_green(self):
        from vaultsoft_hub.ui.styles import ACCENT

        card = self._card()
        card.set_up_to_date("1.0.0")
        card.set_error("Couldn't reach GitHub. Check your internet connection.", offline=True)
        card.ensurePolished()
        card.status_label.ensurePolished()
        self.assertEqual(card.status_label.property("tone"), "error")
        self.assertNotEqual(self._status_colour(card), ACCENT.lower())
        self.assertNotIn("#2ecc71", self._status_colour(card))
        self.assertEqual(card.action_button.objectName(), "Subtle")
        self.assertEqual(card.action_button.text(), "Retry")
        self.assertTrue(card.offline)
        self.assertEqual(self._pills(card), [])  # the window shows the one Offline pill

    def test_button_tiers(self):
        card = self._card()
        card.set_not_installed("1.0.0")
        self.assertEqual((card.action_button.text(), card.action_button.objectName()), ("Install", "Secondary"))
        card.set_up_to_date("1.0.0")
        self.assertEqual((card.action_button.text(), card.action_button.objectName()), ("Launch", "Primary"))
        card.set_update_available("1.0.0", "1.1.0")
        self.assertEqual(card.status_label.property("tone"), "warn")
        link = self._card(id="scribevault", name="ScribeVault", mode="link", badge="Free trial")
        link.set_link()
        self.assertEqual((link.action_button.text(), link.action_button.objectName()), ("Open page", "Outline"))

    def test_mode_drives_the_click(self):
        card = self._card()
        fired = []
        card.retry_requested.connect(lambda i: fired.append(("retry", i)))
        card.launch_requested.connect(lambda i: fired.append(("launch", i)))
        card.set_error("x")
        card.action_button.click()
        card.set_up_to_date("1.0.0")
        card.action_button.click()
        self.assertEqual(fired, [("retry", "wavescout"), ("launch", "wavescout")])

    def test_narrow_card_moves_the_button_under_the_text(self):
        card = self._card()
        card.resize(600, 120)
        card.show()
        self.qapp.processEvents()
        self.assertFalse(card._compact)
        card.resize(320, 200)
        self.qapp.processEvents()
        self.assertTrue(card._compact)
        card.resize(600, 120)
        self.qapp.processEvents()
        self.assertFalse(card._compact)
        card.hide()


@unittest.skipIf(QApplication is None, "PyQt6 not installed")
class IconTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qapp = QApplication.instance() or QApplication([])

    def test_every_bundled_app_has_an_icon_file(self):
        from vaultsoft_hub.app_list import BUNDLED_PATH, parse_app_list
        from vaultsoft_hub.ui.icons import ICON_DIR

        for app in parse_app_list(json.loads(BUNDLED_PATH.read_text(encoding="utf-8"))).apps:
            self.assertTrue((ICON_DIR / app.icon).is_file(), f"{app.id}: {app.icon} missing")

    def test_unknown_app_gets_a_drawn_fallback(self):
        from vaultsoft_hub.ui.icons import app_icon

        pm = app_icon(_app(id="newthing", name="NewThing", icon="nope.svg"), 24)
        self.assertFalse(pm.isNull())
        self.assertFalse(pm.toImage().allGray() and pm.toImage().pixelColor(12, 12).alpha() == 0)


class ThemeRuleTests(unittest.TestCase):
    def test_no_blanket_widget_background(self):
        # A background on plain QWidget paints a dark box behind every label in a card.
        src = (Path(__file__).resolve().parent.parent / "vaultsoft_hub" / "ui" / "styles.py").read_text(encoding="utf-8")
        blanket = re.search(r"(^|\n)QWidget\s*\{\{[^}]*background", src)
        self.assertIsNone(blanket)
        self.assertIn("QLabel {{ background: transparent; }}", src)


if __name__ == "__main__":
    unittest.main()
