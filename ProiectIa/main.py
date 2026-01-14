import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import math

class NodBayesian:
    def __init__(self, data):
        self.nume = data['nume']
        self.parinti = data['parinti']
        self.valori = data['valori']
        self.cpt = data['cpt']

class ReteaBayesiana:
    def __init__(self):
        self.noduri = {}
        self.lista_noduri = []
        self.straturi = {} 

    def check_stability(self):
        epsilon = 0.0001
        for nod in self.lista_noduri:
            for caz, distributie in nod.cpt.items():
                suma_prob = sum(distributie.values())
                if abs(suma_prob - 1.0) > epsilon:
                    raise ValueError(f"Eroare stabilitate la nodul '{nod.nume}'! Suma probabilitatilor este {suma_prob:.4f}")

    def load_from_file(self, file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                self.noduri = {}
                self.lista_noduri = []
                self.straturi = data.get('straturi', {})
                
                for strat_nume, lista_noduri_json in self.straturi.items():
                    for nod_data in lista_noduri_json:
                        new_nod = NodBayesian(nod_data)
                        self.noduri[new_nod.nume] = new_nod
                        self.lista_noduri.append(new_nod)
            
            self.check_stability()
            return True, f"Reteaua '{data.get('nume_retea', 'Necunoscuta')}' a fost incarcata!"
        except Exception as e:
            return False, str(e)

    def get_probability(self, nod_nume, valoare_curenta, evidenta_completa):
        nod = self.noduri[nod_nume]
        if not nod.parinti:
            key = "root"
        else:
            parent_vals = [str(evidenta_completa[p]) for p in nod.parinti]
            key = ",".join(parent_vals)
        try:
            return nod.cpt[key][valoare_curenta]
        except KeyError:
            return 0

def enumerate_all(vars_list, evidence, retea):
    if not vars_list:
        return 1.0
    Y = vars_list[0]
    rest_vars = vars_list[1:]
    if Y in evidence:
        val_y = evidence[Y]
        prob = retea.get_probability(Y, val_y, evidence)
        return prob * enumerate_all(rest_vars, evidence, retea)
    else:
        suma = 0
        for val in retea.noduri[Y].valori:
            evidence_temp = evidence.copy()
            evidence_temp[Y] = val
            prob = retea.get_probability(Y, val, evidence_temp)
            suma += prob * enumerate_all(rest_vars, evidence_temp, retea)
        return suma

def run_inference(query_var, evidence, retea):
    vars_list = [n.nume for n in retea.lista_noduri]
    possible_values = retea.noduri[query_var].valori
    distribution = {}
    
    for val in possible_values:
        ev_ext = evidence.copy()
        ev_ext[query_var] = val
        prob = enumerate_all(vars_list, ev_ext, retea)
        distribution[val] = prob

    total = sum(distribution.values())
    if total == 0: return distribution
    return {k: v / total for k, v in distribution.items()}

class BayesianApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistem Expert Bayesian - Proiect IA")
        self.root.geometry("1280x720")
        
        self.retea = ReteaBayesiana()
        self.node_positions = {}
        self.selected_query_node = None
        self.evidence_vars = {}
        
        self.setup_ui()

    def setup_ui(self):
        toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        btn_load = tk.Button(toolbar, text="Incarca JSON", command=self.load_json)
        btn_load.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.lbl_status = tk.Label(toolbar, text="Asteptare fisier...", fg="gray")
        self.lbl_status.pack(side=tk.LEFT, padx=10)

        paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        frame_left = tk.LabelFrame(paned, text="Evidente (Observatii)", width=300)
        paned.add(frame_left)
        
        self.canvas_ev = tk.Canvas(frame_left)
        scroll_y = tk.Scrollbar(frame_left, orient="vertical", command=self.canvas_ev.yview)
        self.frame_evidence_inner = tk.Frame(self.canvas_ev)

        self.frame_evidence_inner.bind(
            "<Configure>",
            lambda e: self.canvas_ev.configure(scrollregion=self.canvas_ev.bbox("all"))
        )
        self.canvas_ev.create_window((0, 0), window=self.frame_evidence_inner, anchor="nw")
        self.canvas_ev.configure(yscrollcommand=scroll_y.set)

        self.canvas_ev.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        frame_right = tk.LabelFrame(paned, text="Vizualizare Retea (Click pe nod pentru interogare)")
        paned.add(frame_right)

        self.canvas_graph = tk.Canvas(frame_right, bg="white")
        self.canvas_graph.pack(fill=tk.BOTH, expand=True)
        self.canvas_graph.bind("<Button-1>", self.on_canvas_click)
        self.canvas_graph.bind("<Configure>", lambda e: self.draw_network())

        bottom_bar = tk.Frame(self.root, bd=1, relief=tk.SUNKEN, bg="#f0f0f0")
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)

        btn_calc = tk.Button(bottom_bar, text="Calculeaza Probabilitatea", 
                             font=("Arial", 12, "bold"), bg="#4CAF50", fg="white",
                             command=self.calculate)
        btn_calc.pack(pady=10)

    def load_json(self):
        filename = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not filename: return
        
        success, msg = self.retea.load_from_file(filename)
        if success:
            self.lbl_status.config(text=f"Incarcat: {filename}", fg="green")
            self.generate_evidence_panel()
            self.draw_network()
        else:
            messagebox.showerror("Eroare", msg)

    def generate_evidence_panel(self):
        for widget in self.frame_evidence_inner.winfo_children():
            widget.destroy()
        self.evidence_vars = {}

        for i, nod in enumerate(self.retea.lista_noduri):
            row_frame = tk.Frame(self.frame_evidence_inner, pady=5)
            row_frame.pack(fill=tk.X, padx=5)

            var_checked = tk.BooleanVar()
            chk = tk.Checkbutton(row_frame, text=nod.nume, variable=var_checked, font=("Arial", 10, "bold"))
            chk.pack(side=tk.LEFT)

            var_value = tk.StringVar()
            combo = ttk.Combobox(row_frame, values=nod.valori, textvariable=var_value, state="readonly", width=10)
            combo.pack(side=tk.RIGHT)
            if nod.valori: combo.current(0)

            def toggle_state(c=combo, v=var_checked, name=nod.nume):
                if v.get():
                    c.config(state="readonly")
                    self.update_node_color(name, "evidence")
                else:
                    c.config(state="disabled")
                    self.update_node_color(name, "normal")

            chk.config(command=toggle_state)
            combo.config(state="disabled")

            self.evidence_vars[nod.nume] = (var_checked, var_value)

    def draw_network(self):
        self.canvas_graph.delete("all")
        self.node_positions = {}
        if not self.retea.straturi: return

        width = self.canvas_graph.winfo_width()
        height = self.canvas_graph.winfo_height()
        
        layers_keys = list(self.retea.straturi.keys())
        num_cols = len(layers_keys)
        col_width = width / (num_cols + 1)

        for col_idx, layer_name in enumerate(layers_keys):
            nodes_in_layer = self.retea.straturi[layer_name]
            num_rows = len(nodes_in_layer)
            row_height = height / (num_rows + 1)
            
            x = (col_idx + 1) * col_width
            
            for row_idx, nod_data in enumerate(nodes_in_layer):
                y = (row_idx + 1) * row_height
                self.node_positions[nod_data['nume']] = (x, y)

        r = 25

        for nod in self.retea.lista_noduri:
            if nod.nume not in self.node_positions: continue
            x_end_center, y_end_center = self.node_positions[nod.nume]
            
            for parinte in nod.parinti:
                if parinte in self.node_positions:
                    x_start_center, y_start_center = self.node_positions[parinte]
                    
                    angle = math.atan2(y_end_center - y_start_center, x_end_center - x_start_center)
                    
                    x_start = x_start_center + r * math.cos(angle)
                    y_start = y_start_center + r * math.sin(angle)
                    x_end = x_end_center - r * math.cos(angle)
                    y_end = y_end_center - r * math.sin(angle)

                    self.canvas_graph.create_line(
                        x_start, y_start, x_end, y_end, 
                        arrow=tk.LAST, 
                        arrowshape=(16, 20, 6),
                        width=2, 
                        fill="#555555"
                    )

        self.canvas_ids = {}
        for name, (x, y) in self.node_positions.items():
            uid = self.canvas_graph.create_oval(x-r, y-r, x+r, y+r, fill="#ADD8E6", outline="black", width=2, tags="node")
            self.canvas_graph.create_text(x, y, text=name, font=("Arial", 8, "bold"))
            self.canvas_ids[name] = uid
            
            if name in self.evidence_vars and self.evidence_vars[name][0].get():
                self.update_node_color(name, "evidence")
            elif name == self.selected_query_node:
                self.update_node_color(name, "query")

    def on_canvas_click(self, event):
        x_click, y_click = event.x, event.y
        r = 25
        
        clicked_node = None
        for name, (x, y) in self.node_positions.items():
            if (x - x_click)**2 + (y - y_click)**2 <= r**2:
                clicked_node = name
                break
        
        if clicked_node:
            self.select_query_node(clicked_node)

    def select_query_node(self, node_name):
        for name in self.node_positions:
            is_evidence = False
            if name in self.evidence_vars:
                is_evidence = self.evidence_vars[name][0].get()
            self.update_node_color(name, "evidence" if is_evidence else "normal")

        self.selected_query_node = node_name
        self.update_node_color(node_name, "query")

    def update_node_color(self, name, state):
        if name not in self.canvas_ids: return
        uid = self.canvas_ids[name]
        
        color = "#ADD8E6"
        if state == "evidence": color = "#90EE90"
        if state == "query": color = "#FF6347"
        
        self.canvas_graph.itemconfig(uid, fill=color)

    def calculate(self):
        if not self.selected_query_node:
            messagebox.showwarning("Atentie", "Selecteaza un nod pentru interogare dand click pe grafic!")
            return

        evidence = {}
        for name, (var_chk, var_val) in self.evidence_vars.items():
            if var_chk.get():
                if name == self.selected_query_node:
                    messagebox.showerror("Eroare Logica", f"Nu poti interoga nodul '{name}' daca l-ai setat deja ca evidenta!")
                    return
                evidence[name] = var_val.get()

        try:
            result = run_inference(self.selected_query_node, evidence, self.retea)
            
            result_str = f"Rezultat pentru: {self.selected_query_node}\n"
            result_str += "-"*30 + "\n"
            for val, prob in result.items():
                result_str += f"{val}: {prob*100:.2f}%\n"
            
            messagebox.showinfo("Rezultat Inferenta", result_str)
        except Exception as e:
            messagebox.showerror("Eroare Calcul", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = BayesianApp(root)
    root.mainloop()