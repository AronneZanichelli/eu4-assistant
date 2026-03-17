"""Tema scuro per l'UI EU4 Assistant."""

DARK_STYLESHEET = """
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #181825;
}

/* Pannelli */
QFrame#panel {
    background-color: #24273a;
    border: 1px solid #313244;
    border-radius: 6px;
}

QLabel#section_title {
    color: #89b4fa;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}

/* Barre progresso (economy) */
QProgressBar {
    background-color: #313244;
    border: none;
    border-radius: 3px;
    height: 8px;
    text-align: right;
}
QProgressBar::chunk { border-radius: 3px; }
QProgressBar#treasury::chunk  { background-color: #a6e3a1; }
QProgressBar#income::chunk    { background-color: #89b4fa; }
QProgressBar#expenses::chunk  { background-color: #f38ba8; }
QProgressBar#debt::chunk      { background-color: #fab387; }
QProgressBar#manpower::chunk  { background-color: #cba6f7; }

/* Card raccomandazione */
QFrame#rec_card {
    background-color: #2a2a3e;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 8px;
}
QFrame#rec_card:hover {
    border-color: #89b4fa;
}

/* Pulsante Esegui */
QPushButton#execute_btn {
    background-color: #313244;
    color: #a6e3a1;
    border: 1px solid #a6e3a1;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 12px;
}
QPushButton#execute_btn:hover {
    background-color: #a6e3a1;
    color: #1e1e2e;
}
QPushButton#execute_btn:disabled {
    border-color: #45475a;
    color: #6c7086;
}

/* Switch modalità */
QPushButton#mode_btn {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 5px 14px;
}
QPushButton#mode_btn:checked {
    background-color: #89b4fa;
    color: #1e1e2e;
    border-color: #89b4fa;
}

/* Badge alert */
QLabel#alert_badge {
    background-color: #f38ba8;
    color: #1e1e2e;
    border-radius: 3px;
    padding: 2px 6px;
    font-size: 11px;
    font-weight: bold;
}
QLabel#alert_badge_warn {
    background-color: #fab387;
    color: #1e1e2e;
    border-radius: 3px;
    padding: 2px 6px;
    font-size: 11px;
    font-weight: bold;
}

/* Log feed */
QPlainTextEdit#log_feed {
    background-color: #181825;
    color: #a6adc8;
    border: none;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
}

/* Separatori */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: #313244;
}

/* Scrollbar */
QScrollBar:vertical {
    background-color: #181825;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
