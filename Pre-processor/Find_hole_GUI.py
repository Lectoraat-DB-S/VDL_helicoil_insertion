import sys
import gmsh
import csv
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QTreeWidget, 
                             QTreeWidgetItem, QHeaderView, QLabel, QMessageBox)
from PyQt5.QtCore import Qt

class HoleAnalyzerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAD Hole Analyzer: Pro Data Export")
        self.resize(1600, 900)
        
        self.hole_data = [] # Stores processed hole info for export
        self.hole_plot_map = {} 
        self.nodes = None
        self.tris = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)

        # --- Left Panel ---
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.main_layout.addWidget(self.left_panel, 1)

        self.btn_open = QPushButton("1. Load STEP File")
        self.btn_open.setFixedHeight(40)
        self.btn_open.clicked.connect(self.open_file)
        self.left_layout.addWidget(self.btn_open)

        self.btn_export = QPushButton("2. Export Hole Data to CSV")
        self.btn_export.setFixedHeight(40)
        self.btn_export.setEnabled(False) # Disabled until file is loaded
        self.btn_export.clicked.connect(self.export_to_csv)
        self.left_layout.addWidget(self.btn_export)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(["Feature", "Radii", "Lengths", "Position", "Direction"])
        self.tree.header().setSectionResizeMode(QHeaderView.Stretch)
        self.tree.itemSelectionChanged.connect(self.handle_selection)
        self.left_layout.addWidget(self.tree)

        self.lbl_summary = QLabel("Holes Found: 0")
        self.left_layout.addWidget(self.lbl_summary)

        # --- Right Panel ---
        self.canvas = FigureCanvas(plt.Figure(tight_layout=True))
        self.main_layout.addWidget(self.canvas, 2)
        self.ax = self.canvas.figure.add_subplot(111, projection='3d')

    def analyze_and_mesh(self, file_path):
        gmsh.initialize()
        gmsh.option.setNumber("General.Terminal", 0) 
        all_holes = []
        try:
            gmsh.model.occ.importShapes(file_path)
            gmsh.model.occ.synchronize()
            gmsh.model.mesh.generate(2)
            
            node_tags, coords, _ = gmsh.model.mesh.getNodes()
            self.nodes = coords.reshape((-1, 3)) if len(node_tags) > 0 else None
            elem_types, _, node_indices = gmsh.model.mesh.getElements(2)
            for i, e_type in enumerate(elem_types):
                if e_type == 2:
                    node_map = {tag: i for i, tag in enumerate(node_tags)}
                    self.tris = np.array([node_map[t] for t in node_indices[i]]).reshape((-1, 3))

            raw_cylinders = []
            for dim, tag in gmsh.model.getEntities(2):
                if "Cylind" in gmsh.model.getType(dim, tag):
                    b = gmsh.model.getParametrizationBounds(dim, tag)
                    v_m, v_x = b[0][1], b[1][1]
                    u_m, u_x = b[0][0], b[1][0]
                    def get_c(v_val):
                        p = [gmsh.model.getValue(dim, tag, [u_m + (u_x-u_m)*(k/2.0), v_val]) for k in range(2)]
                        c = np.mean(p, axis=0)
                        return c, np.linalg.norm(p[0]-c)
                    
                    c1, r1 = get_c(v_m)
                    c2, _ = get_c(v_x)
                    vec = c2 - c1
                    length = np.linalg.norm(vec)
                    unit_v = vec / length if length > 1e-6 else np.array([0,0,0])
                    raw_cylinders.append({"tag": tag, "c1": c1, "c2": c2, "radius": r1, "length": length, "dir": unit_v})

            used = set()
            for i, cy1 in enumerate(raw_cylinders):
                if cy1["tag"] in used: continue
                current = [cy1]; used.add(cy1["tag"])
                for j, cy2 in enumerate(raw_cylinders):
                    if i == j or cy2["tag"] in used: continue
                    d = [np.linalg.norm(cy1["c1"]-cy2["c1"]), np.linalg.norm(cy1["c1"]-cy2["c2"]),
                         np.linalg.norm(cy1["c2"]-cy2["c1"]), np.linalg.norm(cy1["c2"]-cy2["c2"])]
                    if min(d) < 1e-3:
                        current.append(cy2); used.add(cy2["tag"])
                
                all_holes.append({
                    "radii": tuple(round(float(c["radius"]), 3) for c in current), 
                    "lengths": tuple(round(float(c["length"]), 3) for c in current), 
                    "pos": [float(x) for x in current[0]["c1"]],
                    "dir": [float(x) for x in current[0]["dir"]],
                    "segments": current
                })
        finally:
            gmsh.finalize()
        return all_holes

    def populate_tree_and_plot(self, holes):
        self.hole_data = holes
        self.ax.clear()
        self.tree.clear()
        self.hole_plot_map = {}
        self.lbl_summary.setText(f"Holes Found: {len(holes)}")
        self.btn_export.setEnabled(len(holes) > 0)

        if self.nodes is not None:
            self.ax.plot_trisurf(self.nodes[:,0], self.nodes[:,1], self.nodes[:,2], triangles=self.tris, alpha=0.03, color='gray')
            ranges = [self.nodes[:,i].max() - self.nodes[:,i].min() for i in range(3)]; pr = 0.5 * max(ranges)
            mids = [np.mean([self.nodes[:,i].max(), self.nodes[:,i].min()]) for i in range(3)]
            self.ax.set_xlim3d([mids[0]-pr, mids[0]+pr]); self.ax.set_ylim3d([mids[1]-pr, mids[1]+pr]); self.ax.set_zlim3d([mids[2]-pr, mids[2]+pr])

        groups = {}
        for h in holes:
            key = (h["radii"], h["lengths"])
            if key not in groups: groups[key] = []
            groups[key].append(h)

        for i, (key, instances) in enumerate(groups.items()):
            parent = QTreeWidgetItem(self.tree, [f"Type {i+1}", str(list(key[0])), str(list(key[1])), "", ""])
            parent_elements = []
            for j, inst in enumerate(instances):
                p, d = inst['pos'], inst['dir']
                pos_str = f"({p[0]:.1f}, {p[1]:.1f}, {p[2]:.1f})"
                dir_str = f"[{d[0]:.2f}, {d[1]:.2f}, {d[2]:.2f}]"
                child = QTreeWidgetItem(parent, [f"Inst {j+1}", "", "", pos_str, dir_str])
                
                child_elements = []
                for seg in inst['segments']:
                    pts = np.array([seg['c1'], seg['c2']])
                    ln, = self.ax.plot(pts[:,0], pts[:,1], pts[:,2], color='blue', linewidth=1, alpha=0.3)
                    child_elements.append(ln)
                
                arrow_len = key[0][0] * 2 if key[0] else 5
                q = self.ax.quiver(p[0], p[1], p[2], d[0], d[1], d[2], length=arrow_len, color='red', alpha=0.4)
                child_elements.append(q)
                
                self.hole_plot_map[id(child)] = child_elements
                parent_elements.append(child_elements)
            self.hole_plot_map[id(parent)] = parent_elements

        self.ax.set_box_aspect((1,1,1))
        self.canvas.draw()

    def handle_selection(self):
        selected = self.tree.selectedItems()
        if not selected: return
        item = selected[0]
        for val in self.hole_plot_map.values():
            nested = val if isinstance(val[0], list) else [val]
            for sub in nested:
                for obj in sub:
                    if hasattr(obj, 'set_color'):
                        obj.set_color('blue' if not hasattr(obj, 'segments') else 'red')
                        obj.set_alpha(0.2)
        target = self.hole_plot_map.get(id(item))
        if target:
            nested = target if isinstance(target[0], list) else [target]
            for sub in nested:
                for obj in sub:
                    obj.set_color('orange'); obj.set_alpha(1.0)
        self.canvas.draw()

    def export_to_csv(self):
        if not self.hole_data: return
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "hole_analysis.csv", "CSV Files (*.csv)")
        if not path: return
        
        try:
            with open(path, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Type", "Instance", "Radii", "Lengths", "PosX", "PosY", "PosZ", "DirX", "DirY", "DirZ"])
                
                # Regrouping for clear naming in CSV
                groups = {}
                for h in self.hole_data:
                    key = (h["radii"], h["lengths"])
                    if key not in groups: groups[key] = []
                    groups[key].append(h)
                
                for i, (key, instances) in enumerate(groups.items()):
                    for j, inst in enumerate(instances):
                        writer.writerow([
                            f"Type {i+1}", f"Instance {j+1}",
                            str(list(key[0])), str(list(key[1])),
                            inst['pos'][0], inst['pos'][1], inst['pos'][2],
                            inst['dir'][0], inst['dir'][1], inst['dir'][2]
                        ])
            QMessageBox.information(self, "Success", f"Data exported successfully to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export CSV: {e}")

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open STEP", "", "STEP (*.step *.stp)")
        if path:
            holes = self.analyze_and_mesh(path)
            self.populate_tree_and_plot(holes)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HoleAnalyzerGUI()
    window.show()
    sys.exit(app.exec_())