"""Debounced recovery of editable work; never mutate a scientific execution."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone

from PySide6.QtCore import QObject, QTimer, QStandardPaths
from PySide6.QtWidgets import QLabel, QInputDialog

from data.drafts import DraftStore


class DraftController(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        directory = (window.repository.base_dir / ".workspace" if window.repository else
                     Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / "recovery")
        self.store = DraftStore(directory)
        self.state = self.store.load()
        self.annotations = self.state.get("annotations", {})
        self.protocols = self.state.get("protocols", {})
        self.history = self.state.get("editor_history", [])
        saved_form = self.state.get("simulation",{})
        self.identity_baseline = (saved_form.get("committed_name",""),saved_form.get("committed_description",""))
        self.source = None
        self.restoring = True
        self.error = ""
        self.indicator = QLabel("Rascunhos protegidos")
        self.indicator.setToolTip("Circuito, formulário e anotações em edição são recuperados automaticamente. Salvar revisão e salvar anotações continuam ações explícitas.")
        window.statusBar().addPermanentWidget(self.indicator)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.flush)
        self.restore()
        page = window.page_simulation
        page.experiment_name.textChanged.connect(self.schedule)
        page.experiment_description.textChanged.connect(self.schedule)
        page.config_panel.parametros_alterados.connect(self.schedule)
        page.config_panel.mode_changed.connect(self.schedule)
        window.page_circuit.editor.draft_changed.connect(self.schedule)
        window.page_circuit.editor.document_replacing.connect(self.remember_editor)
        window.page_circuit.editor.recovery_requested.connect(self.choose_editor_recovery)
        window.page_circuit.editor.recover_draft.setEnabled(bool(self.history))
        window.page_library.draft_changed.connect(self.annotation_edited)
        window.page_library.name.textChanged.connect(self.schedule)
        window.page_library.loaded.connect(self.annotation_loaded)
        for field in window.page_analysis.protocol.fields.values():
            field.textChanged.connect(self.protocol_edited)
        self.restoring = False
        if self.store.warning:
            window.statusBar().showMessage(self.store.warning)
        elif self.state:
            window.statusBar().showMessage("Rascunhos recuperados. Revisões e resultados salvos permanecem preservados.")

    def restore(self):
        try:
            if self.state.get("editor"):
                self.window.page_circuit.editor.restore_draft(self.state["editor"])
            saved = self.state.get("simulation", {})
            page = self.window.page_simulation
            self.window._loading_draft = True
            controls = saved.get("controls", {})
            panel = page.config_panel
            for key, attr in (("qubits","spin_qubits"),("J","spin_J"),("h","spin_h"),
                              ("tempo","spin_tempo"),("passos","spin_passos"),("p1","spin_p1"),
                              ("p2","spin_p2"),("t1","spin_t1"),("t2","spin_t2"),("shots","spin_shots"),
                              ("gate1","spin_gate1"),("gate2","spin_gate2")):
                if key in controls:
                    getattr(panel, attr).setValue(controls[key])
            for key, attr in (("ruido_ativo","check_ruido"),("periodic","check_periodic"),("salvar_snaps","check_snaps")):
                if key in controls:
                    getattr(panel,attr).setChecked(controls[key])
            for key, attr in (("hamiltoniano","combo_ham"),("modelo_ruido","combo_modelo")):
                if key in controls:
                    getattr(panel,attr).setCurrentText(controls[key])
            for key, attr in (("initial","combo_initial"),("order","combo_order")):
                if key in saved:
                    combo = getattr(panel,attr)
                    combo.setCurrentIndex(max(0,combo.findData(saved[key])))
            if "seed" in controls:
                panel.input_seed.setText(controls["seed"])
            if "mode" in saved:
                panel.set_mode(saved["mode"])
            page.experiment_name.setText(saved.get("name", ""))
            page.experiment_description.setText(saved.get("description", ""))
            self.window.page_library.name.setText(self.state.get("template_name",""))
            protocol = self.protocols.get("draft",{})
            self.window.page_analysis.protocol.loaded = protocol.get("loaded")
            for key,field in self.window.page_analysis.protocol.fields.items():
                field.setText(protocol.get("fields",{}).get(key,""))
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            self.error = "Parte do rascunho não pôde ser recuperada; arquivo preservado: " + str(exc)
            self.indicator.setText("Revisar recuperação de rascunho")
            self.window.statusBar().showMessage(self.error)
        finally:
            self.window._loading_draft = False
        self.window._draft_changed()

    def schedule(self, *_):
        if not self.restoring:
            self.indicator.setText("Salvando rascunhos…")
            self.timer.start()

    def annotation_edited(self):
        if self.restoring:
            return
        page = self.window.page_library
        if page.identifier:
            self.annotations[page.identifier] = page.draft_payload()
            self.schedule()

    def annotation_loaded(self, identifier):
        if identifier in self.annotations:
            self.window.page_library.restore_draft(self.annotations[identifier])

    def annotation_committed(self, identifier):
        self.annotations.pop(identifier, None)
        self.schedule()

    def protocol_edited(self, *_):
        if self.restoring:
            return
        panel = self.window.page_analysis.protocol
        self.protocols[self.source or "draft"] = {
            "fields": {key: field.text() for key, field in panel.fields.items()},
            "loaded": panel.loaded,
        }
        self.schedule()

    def set_source(self, identifier):
        if identifier == self.source:
            return
        panel = self.window.page_analysis.protocol
        saved = self.protocols.get(identifier, self.protocols.get("draft", {}) if self.source is None else {})
        if self.source is None and identifier not in self.protocols and "draft" in self.protocols:
            self.protocols[identifier] = self.protocols.pop("draft")
        self.source = identifier
        self.restoring = True
        try:
            panel.loaded = saved.get("loaded")
            for key, field in panel.fields.items():
                field.setText(saved.get("fields", {}).get(key, ""))
        finally:
            self.restoring = False

    def flush(self):
        if self.restoring:
            return True
        self.timer.stop()
        page = self.window.page_simulation
        panel = page.config_panel
        state = dict(editor=self.window.page_circuit.editor.draft_state(),
                     simulation=dict(name=page.experiment_name.text(), description=page.experiment_description.text(),
                                     controls=panel.coletar_tudo(), mode=panel.current_mode,
                                     initial=panel.combo_initial.currentData(), order=panel.combo_order.currentData(),
                                     committed_name=self.identity_baseline[0],committed_description=self.identity_baseline[1]),
                     annotations=self.annotations, protocols=self.protocols,template_name=self.window.page_library.name.text(),
                     editor_history=self.history[-10:])
        try:
            self.store.save(state)
        except (OSError, ValueError, TypeError) as exc:
            self.error = "Não foi possível proteger os rascunhos: " + str(exc)
            self.indicator.setText("Rascunhos ainda não protegidos")
            self.window.statusBar().showMessage(self.error)
            return False
        self.state = state
        self.error = ""
        self.indicator.setText("Rascunhos protegidos")
        return True

    @property
    def identity_dirty(self):
        page = self.window.page_simulation
        return (page.experiment_name.text(),page.experiment_description.text()) != self.identity_baseline

    def mark_identity_baseline(self):
        page = self.window.page_simulation
        self.identity_baseline = (page.experiment_name.text(),page.experiment_description.text())
        self.schedule()

    def remember_editor(self, snapshot):
        if self.restoring or (self.history and self.history[-1]["editor"] == snapshot):
            return
        self.history.append(dict(editor=deepcopy(snapshot),saved_at=datetime.now(timezone.utc).isoformat()))
        self.history = self.history[-10:]
        self.window.page_circuit.editor.recover_draft.setEnabled(True)
        self.schedule()

    def choose_editor_recovery(self):
        labels = []
        indexes = list(reversed(range(len(self.history))))
        for order,index in enumerate(indexes,1):
            item = self.history[index]
            name = item["editor"].get("name") or "Circuito sem nome"
            count = len(item["editor"]["document"].get("gates",[]))
            try:
                stamp = datetime.fromisoformat(item.get("saved_at","")).astimezone().strftime("%d/%m %H:%M")
            except ValueError:
                stamp = "data indisponível"
            labels.append(f"{order}. {name} · {count} portas · {stamp}")
        label, accepted = QInputDialog.getItem(self.window,"Recuperar rascunho","Escolha o estado anterior do editor:",labels,0,False)
        if accepted and label in labels:
            self.restore_editor_checkpoint(indexes[labels.index(label)])

    def restore_editor_checkpoint(self,index):
        snapshot = deepcopy(self.history[index]["editor"])
        self.remember_editor(self.window.page_circuit.editor.draft_state())
        self.restoring = True
        try:
            self.window.page_circuit.editor.restore_draft(snapshot)
        finally:
            self.restoring = False
        self.schedule()
