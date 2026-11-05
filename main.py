import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from core.settings import Settings
from core.timer import Phase, PomodoroTimer
from core.vocab import VocabDeck
from ui.break_overlay import BreakScreen
from ui.main_window import MainWindow
from ui.settings_dialog import SettingsDialog
from ui.speech import Speaker
from ui.tray import Tray
from ui.util import format_time


def make_deck(settings: Settings) -> VocabDeck:
    deck = VocabDeck(settings.vocab_path or None)
    if deck.warning:
        print(f"[vocab] {deck.warning}")
    return deck


def main():
    app = QApplication(sys.argv)
    # The app lives in the tray: hiding the timer or closing the break screen
    # must not end the program. Only "Quit" does.
    app.setQuitOnLastWindowClosed(False)

    # --fast        10 s focus / 15 s break, ignores saved timing (testing)
    # --no-grab     cover the screen but never grab keyboard and mouse
    # --background  start hidden in the tray
    fast = "--fast" in sys.argv
    allow_grab = "--no-grab" not in sys.argv

    settings = Settings.load()
    print(f"[settings] stored in {Settings.location()}")
    state = {"settings": settings, "deck": make_deck(settings),
             "dialog_open": False}

    def durations(s: Settings):
        return (10, 15) if fast else (s.focus_minutes * 60, s.break_seconds)

    focus_s, break_s = durations(settings)
    pomo = PomodoroTimer(focus_seconds=focus_s, break_seconds=break_s)
    pomo.auto_continue = settings.auto_start_focus

    speaker = Speaker(settings.piper_model, settings.speech_speed)
    print(f"[speech] using {speaker.engine}" if speaker.available
          else f"[speech] disabled: {speaker.problem}")

    def toggle_break_pause():
        if pomo.phase is not Phase.BREAK:
            return
        pomo.toggle_pause()
        overlay.set_paused(pomo.paused)

    overlay = BreakScreen(speaker, on_emergency=pomo.stop, settings=settings,
                          on_toggle_pause=toggle_break_pause)
    overlay.configure(settings, allow_grab)

    tray_ok = QSystemTrayIcon.isSystemTrayAvailable()
    if not tray_ok:
        print("[tray] no system tray found; 'hide' will minimize to the taskbar")

    # ---------- actions ----------

    def minimize():
        if tray_ok:
            window.hide()
        else:
            window.showMinimized()

    def open_settings():
        if state["dialog_open"]:
            return
        state["dialog_open"] = True
        try:
            current = state["settings"]
            dialog = SettingsDialog(
                current, Settings(),
                parent=window if window.is_shown() else None)
            if not dialog.exec():  # 0 = cancelled
                return
            new = dialog.result_settings()
            try:
                new.save()
                print(f"[settings] saved to {Settings.location()}")
            except OSError as e:
                print(f"[settings] SAVE FAILED: {e}")
                QMessageBox.warning(
                    None, "Foklumi",
                    f"Your settings could not be saved:\n{e}\n\n"
                    "They will apply until you quit the app.")
            state["settings"] = new
            window.apply_settings(new)
            overlay.configure(new, allow_grab)
            speaker.reconfigure(new.piper_model, new.speech_speed)
            pomo.auto_continue = new.auto_start_focus
            f, b = durations(new)
            pomo.set_durations(f, b)
            if new.vocab_path != current.vocab_path:
                state["deck"] = make_deck(new)
            if tray:
                tray.update_state(tray_color(pomo.phase),
                                  tip(pomo.phase, pomo.remaining))
        finally:
            state["dialog_open"] = False

    # ---------- window and tray ----------

    window = MainWindow(
        settings, on_start=pomo.start, on_stop=pomo.stop, on_skip=pomo.skip,
        on_settings=open_settings, on_minimize=minimize, on_quit=app.quit)

    def tray_color(phase: Phase) -> str:
        s = state["settings"]
        return {Phase.FOCUS: s.focus_color, Phase.BREAK: s.break_color,
                Phase.IDLE: s.idle_color}[phase]

    def tip(phase: Phase, remaining: int) -> str:
        if phase is Phase.IDLE:
            return "Foklumi – ready"
        name = "Focus" if phase is Phase.FOCUS else "Break"
        return f"{name} {format_time(remaining)}"

    tray = None
    if tray_ok:
        tray = Tray(window, on_start=pomo.start, on_stop=pomo.stop,
                    on_skip=pomo.skip, on_settings=open_settings,
                    on_quit=app.quit)
        tray.update_state(tray_color(Phase.IDLE), tip(Phase.IDLE, 0))
        tray.show()
        app.aboutToQuit.connect(tray.hide)  # no stale icon after quitting

    # ---------- timer callbacks ----------

    def on_phase(phase: Phase):
        window.set_phase(phase)
        if tray:
            tray.update_state(tray_color(phase), tip(phase, pomo.remaining))
        if phase is Phase.BREAK:
            overlay.show(state["deck"].next_word(), pomo.break_seconds,
                         state["settings"].auto_speak)
        else:
            overlay.hide()
            speaker.stop()

    def on_tick(phase: Phase, remaining: int):
        window.set_remaining(remaining)
        if tray:
            tray.set_tip(tip(phase, remaining))
        if phase is Phase.BREAK:
            overlay.update(remaining)

    pomo.on_phase_changed = on_phase
    pomo.on_tick = on_tick

    ticker = QTimer()
    ticker.timeout.connect(pomo.tick)
    ticker.start(500)

    background = settings.start_in_background or "--background" in sys.argv
    if background and tray_ok:
        print("[tray] started in the background")
    else:
        window.show()

    app.aboutToQuit.connect(speaker.stop)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
