import sys
import numpy as np
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDoubleSpinBox,
    QSpinBox,
    QPushButton,
    QComboBox,
    QProgressBar,
    QGroupBox,
    QFormLayout,
    QFileDialog,
    QSizePolicy,
    QRubberBand,
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QRect, QSize
from PyQt5.QtGui import QCursor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


DEFAULTS = {
    "cx": -0.5,
    "cy": 0.0,
    "scale": 3.5,
    "max_iter": 128,
    "resolution": 600,
}

ZOOM_FACTOR = 0.85


class MandelbrotWorker(QThread):
    # Signal sends the computed 2D array back to the main thread.
    finished = pyqtSignal(np.ndarray)

    def __init__(self, cx, cy, scale, max_iter, resolution):
        super().__init__()
        self.cx = cx
        self.cy = cy
        self.scale = scale
        self.max_iter = max_iter
        self.resolution = resolution

    def run(self):
        # Build a square region of the complex plane.
        res = self.resolution
        half = self.scale / 2
        x = np.linspace(self.cx - half, self.cx + half, res)
        y = np.linspace(self.cy - half, self.cy + half, res)
        c = x[np.newaxis, :] + 1j * y[:, np.newaxis]

        # z starts from zero for every point c.
        z = np.zeros_like(c)

        # Result matrix stores smooth escape values.
        result = np.zeros(c.shape, dtype=np.float64)
        active_mask = np.ones(c.shape, dtype=bool)

        # Iterate z = z^2 + c for all pixels.
        for i in range(self.max_iter):
            z[active_mask] = z[active_mask] ** 2 + c[active_mask]
            escaped = active_mask & (np.abs(z) > 2)

            # Smooth coloring makes gradients softer.
            result[escaped] = i + 1 - np.log2(np.log2(np.abs(z[escaped]) + 1e-10))
            active_mask[escaped] = False

        self.finished.emit(result)


class InteractiveCanvas(FigureCanvas):
    # Signal informs the window that the viewport has changed.
    view_changed = pyqtSignal(float, float, float)

    def __init__(self, figure, cx, cy, scale):
        super().__init__(figure)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFocusPolicy(Qt.StrongFocus)

        # Current viewport of the complex plane.
        self._cx = cx
        self._cy = cy
        self._scale = scale

        # Left mouse drag state.
        self._pan_active = False
        self._pan_start_px = None
        self._pan_start_cx = None
        self._pan_start_cy = None

        # Right mouse drag state.
        self._rubber_band = QRubberBand(QRubberBand.Rectangle, self)
        self._rb_origin = None

        self.setMouseTracking(True)

    def set_view(self, cx, cy, scale):
        self._cx = cx
        self._cy = cy
        self._scale = scale

    def _pixel_to_fractal(self, px, py):
        # Convert widget pixel coordinates to Mandelbrot coordinates.
        width = self.width()
        height = self.height()
        fx = self._cx + (px / width - 0.5) * self._scale
        fy = self._cy + (0.5 - py / height) * self._scale
        return fx, fy

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Start panning.
            self._pan_active = True
            self._pan_start_px = event.pos()
            self._pan_start_cx = self._cx
            self._pan_start_cy = self._cy
            self.setCursor(QCursor(Qt.ClosedHandCursor))

        elif event.button() == Qt.RightButton:
            # Start area selection for zoom.
            self._rb_origin = event.pos()
            self._rubber_band.setGeometry(QRect(self._rb_origin, QSize()))
            self._rubber_band.show()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan_active and self._pan_start_px is not None:
            # Convert mouse shift from pixels to fractal coordinates.
            dx_px = event.pos().x() - self._pan_start_px.x()
            dy_px = event.pos().y() - self._pan_start_px.y()
            width = self.width()
            height = self.height()
            self._cx = self._pan_start_cx - dx_px / width * self._scale
            self._cy = self._pan_start_cy + dy_px / height * self._scale

        elif self._rb_origin is not None:
            # Update selection rectangle.
            rect = QRect(self._rb_origin, event.pos()).normalized()
            self._rubber_band.setGeometry(rect)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._pan_active:
            # Finish panning and notify the main window.
            self._pan_active = False
            self.setCursor(QCursor(Qt.ArrowCursor))
            self.view_changed.emit(self._cx, self._cy, self._scale)

        elif event.button() == Qt.RightButton and self._rb_origin is not None:
            # Finish selection and zoom into the selected region.
            self._rubber_band.hide()
            rect = QRect(self._rb_origin, event.pos()).normalized()
            self._rb_origin = None

            if rect.width() > 5 and rect.height() > 5:
                fx0, fy0 = self._pixel_to_fractal(rect.left(), rect.bottom())
                fx1, fy1 = self._pixel_to_fractal(rect.right(), rect.top())
                self._cx = (fx0 + fx1) / 2
                self._cy = (fy0 + fy1) / 2
                self._scale = max(abs(fx1 - fx0), abs(fy1 - fy0))
                self.view_changed.emit(self._cx, self._cy, self._scale)

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        # Mouse wheel changes zoom relative to cursor position.
        delta = event.angleDelta().y()
        if delta == 0:
            return

        px = event.pos().x()
        py = event.pos().y()
        fx, fy = self._pixel_to_fractal(px, py)

        factor = ZOOM_FACTOR if delta > 0 else (1.0 / ZOOM_FACTOR)
        self._scale *= factor

        # Keep the point under the cursor visually fixed.
        self._cx = fx + (self._cx - fx) * factor
        self._cy = fy + (self._cy - fy) * factor

        self.view_changed.emit(self._cx, self._cy, self._scale)
        super().wheelEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Множество Мандельброта")
        self.resize(1100, 720)
        self._worker = None
        self._last_array = None
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # Left panel contains all controls.
        panel = QWidget()
        panel.setFixedWidth(230)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(8)

        params_box = QGroupBox("Параметры")
        form = QFormLayout(params_box)
        form.setSpacing(6)

        self.spin_cx = QDoubleSpinBox()
        self.spin_cx.setRange(-4.0, 4.0)
        self.spin_cx.setDecimals(8)
        self.spin_cx.setSingleStep(0.1)
        self.spin_cx.setValue(DEFAULTS["cx"])
        form.addRow("Центр X:", self.spin_cx)

        self.spin_cy = QDoubleSpinBox()
        self.spin_cy.setRange(-4.0, 4.0)
        self.spin_cy.setDecimals(8)
        self.spin_cy.setSingleStep(0.1)
        self.spin_cy.setValue(DEFAULTS["cy"])
        form.addRow("Центр Y:", self.spin_cy)

        self.spin_scale = QDoubleSpinBox()
        self.spin_scale.setRange(1e-10, 10.0)
        self.spin_scale.setDecimals(10)
        self.spin_scale.setSingleStep(0.1)
        self.spin_scale.setValue(DEFAULTS["scale"])
        form.addRow("Масштаб:", self.spin_scale)

        self.spin_iter = QSpinBox()
        self.spin_iter.setRange(8, 2048)
        self.spin_iter.setSingleStep(32)
        self.spin_iter.setValue(DEFAULTS["max_iter"])
        form.addRow("Итерации:", self.spin_iter)

        self.spin_res = QSpinBox()
        self.spin_res.setRange(100, 2000)
        self.spin_res.setSingleStep(100)
        self.spin_res.setValue(DEFAULTS["resolution"])
        form.addRow("Разрешение:", self.spin_res)

        panel_layout.addWidget(params_box)

        view_box = QGroupBox("Отображение")
        view_layout = QVBoxLayout(view_box)
        view_layout.setSpacing(6)

        self.combo_cmap = QComboBox()
        self.combo_cmap.addItems(["hot", "inferno", "RdBu"])
        view_layout.addWidget(QLabel("Цветовая схема:"))
        view_layout.addWidget(self.combo_cmap)

        panel_layout.addWidget(view_box)

        help_box = QGroupBox("Управление мышью")
        help_layout = QVBoxLayout(help_box)
        help_layout.setSpacing(3)

        for text in [
            "ЛКМ + перетащить - сдвиг",
            "ПКМ + выделить - зум в область",
            "Колесо - изменить масштаб",
        ]:
            label = QLabel(text)
            label.setWordWrap(True)
            label.setStyleSheet("color: gray; font-size: 11px;")
            help_layout.addWidget(label)

        panel_layout.addWidget(help_box)

        self.btn_build = QPushButton("Построить")
        self.btn_build.setDefault(True)
        self.btn_build.clicked.connect(self._on_build)
        panel_layout.addWidget(self.btn_build)

        self.btn_reset = QPushButton("Сбросить")
        self.btn_reset.clicked.connect(self._on_reset)
        panel_layout.addWidget(self.btn_reset)

        self.btn_save = QPushButton("Сохранить PNG")
        self.btn_save.clicked.connect(self._on_save)
        panel_layout.addWidget(self.btn_save)

        panel_layout.addStretch()
        root.addWidget(panel)

        # Right side contains the Matplotlib canvas.
        self.figure = Figure(tight_layout=True)
        self.canvas = InteractiveCanvas(
            self.figure,
            DEFAULTS["cx"],
            DEFAULTS["cy"],
            DEFAULTS["scale"],
        )
        self.canvas.view_changed.connect(self._on_view_changed)
        root.addWidget(self.canvas, stretch=1)

        # Status bar shows current state of calculations.
        self.statusBar().showMessage("Готово - нажмите \"Построить\"")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedWidth(120)
        self.progress.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress)

    def _block_spin_updates(self, block):
        # Prevent extra signals while values are updated from code.
        for widget in (self.spin_cx, self.spin_cy, self.spin_scale):
            widget.blockSignals(block)

    def _on_view_changed(self, cx, cy, scale):
        # Mouse interaction changed viewport -> update widgets -> rebuild image.
        self._block_spin_updates(True)
        self.spin_cx.setValue(cx)
        self.spin_cy.setValue(cy)
        self.spin_scale.setValue(scale)
        self._block_spin_updates(False)
        self._on_build()

    def _on_build(self):
        # Avoid launching a second worker while the first one is active.
        if self._worker and self._worker.isRunning():
            return

        self.btn_build.setEnabled(False)
        self.statusBar().showMessage("Вычисляем...")
        self.progress.setVisible(True)

        cx = self.spin_cx.value()
        cy = self.spin_cy.value()
        scale = self.spin_scale.value()
        self.canvas.set_view(cx, cy, scale)

        self._worker = MandelbrotWorker(
            cx=cx,
            cy=cy,
            scale=scale,
            max_iter=self.spin_iter.value(),
            resolution=self.spin_res.value(),
        )
        self._worker.finished.connect(self._on_result)
        self._worker.start()

    def _on_result(self, arr):
        # Store image data and redraw the canvas in the main thread.
        self._last_array = arr
        self._render(arr)
        self.btn_build.setEnabled(True)
        self.progress.setVisible(False)
        self.statusBar().showMessage("Готово")

    def _render(self, arr):
        # Draw the Mandelbrot image using current viewport parameters.
        cmap = self.combo_cmap.currentText()
        self.figure.clear()
        ax = self.figure.add_subplot(1, 1, 1)

        cx = self.spin_cx.value()
        cy = self.spin_cy.value()
        scale = self.spin_scale.value()
        half = scale / 2
        extent = [cx - half, cx + half, cy - half, cy + half]

        ax.imshow(
            arr,
            cmap=cmap,
            origin="lower",
            interpolation="bilinear",
            extent=extent,
        )
        ax.set_title("Множество Мандельброта", fontsize=10)
        ax.tick_params(labelsize=7)
        self.canvas.draw()

    def _on_reset(self):
        self._block_spin_updates(True)
        self.spin_cx.setValue(DEFAULTS["cx"])
        self.spin_cy.setValue(DEFAULTS["cy"])
        self.spin_scale.setValue(DEFAULTS["scale"])
        self.spin_iter.setValue(DEFAULTS["max_iter"])
        self.spin_res.setValue(DEFAULTS["resolution"])
        self._block_spin_updates(False)
        self.canvas.set_view(DEFAULTS["cx"], DEFAULTS["cy"], DEFAULTS["scale"])

    def _on_save(self):
        if self._last_array is None:
            self.statusBar().showMessage("Нечего сохранять - сначала постройте фрактал")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить PNG",
            "mandelbrot.png",
            "PNG (*.png)",
        )
        if path:
            self.figure.savefig(path, dpi=150, bbox_inches="tight")
            self.statusBar().showMessage(f"Сохранено: {path}")


def main():
    # Standard PyQt application bootstrap.
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
