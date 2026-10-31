from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFrame
from PySide6.QtCore import QPropertyAnimation, QEasingCurve

class CollapsibleBox(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.toggle_btn = QPushButton(title)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 12px;
                background: #12171f;
                border: 1px solid #1a1f2b;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 600;
                color: #7ec8e3;
            }
            QPushButton:hover {
                background: #1a2a3a;
                border-color: #7ec8e3;
            }
        """)
        self.toggle_btn.clicked.connect(self._animate)

        self.content_area = QFrame()
        self.content_area.setStyleSheet("QFrame { background: transparent; border: none; }")
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(8, 8, 8, 8)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)
        main_layout.addWidget(self.toggle_btn)
        main_layout.addWidget(self.content_area)

        self._animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self._animation.setDuration(250)
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)
        self._expanded_height = 0

    def _animate(self):
        # Para qualquer animação em andamento e desconecta sinais antigos
        self._animation.stop()
        try:
            self._animation.finished.disconnect()
        except (RuntimeError, TypeError):
            pass

        if self.toggle_btn.isChecked():
            # ----- EXPANDIR -----
            # 1. Torna o conteúdo visível e define altura máxima grande para obter o tamanho real
            self.content_area.setVisible(True)
            self.content_area.setMaximumHeight(16777215)  # valor grande o suficiente
            # Força o layout a recalcular e obter a altura ideal
            self.content_area.updateGeometry()
            self._expanded_height = self.content_area.sizeHint().height()
            # 2. Define altura máxima como 0 para iniciar a animação de expansão
            self.content_area.setMaximumHeight(0)
            # 3. Configura a animação
            self._animation.setStartValue(0)
            self._animation.setEndValue(self._expanded_height)
            # 4. Após a animação, libera a altura máxima para permitir crescimento futuro
            self._animation.finished.connect(lambda: self.content_area.setMaximumHeight(16777215))
        else:
            # ----- RECOLHER -----
            # Armazena a altura atual
            self._expanded_height = self.content_area.height()
            # Configura animação de recolhimento
            self._animation.setStartValue(self._expanded_height)
            self._animation.setEndValue(0)
            # Ao terminar, esconde o conteúdo
            self._animation.finished.connect(lambda: self.content_area.setVisible(False))

        self._animation.start()

    def addWidget(self, widget):
        self.content_layout.addWidget(widget)
        # Invalida altura guardada para que seja recalculada na próxima expansão
        self._expanded_height = 0
