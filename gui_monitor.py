import tkinter as tk
from tkinter import ttk
from datetime import datetime

scan_log=[]
top_candidates=[]
pair_stats={"total":0,"scanned":0,"round_time":0}

class BotGUI:

    def __init__(self,root):

        self.root=root
        root.title("AI Crypto Scanner")
        root.geometry("1200x700")

        bar=tk.Frame(root)
        bar.pack(fill=tk.X)

        self.update_label=tk.Label(bar,text="")
        self.update_label.pack(side=tk.LEFT,padx=10)

        self.pairs=tk.Label(bar,text="Pairs 0/0")
        self.pairs.pack(side=tk.LEFT,padx=20)

        self.timer=tk.Label(bar,text="Round:0s")
        self.timer.pack(side=tk.LEFT,padx=20)

        scan_frame=tk.LabelFrame(root,text="Scanning")
        scan_frame.pack(fill=tk.BOTH,expand=True,padx=10,pady=5)

        self.progress=ttk.Progressbar(scan_frame,length=400)
        self.progress.pack(pady=5)

        self.scan=tk.Listbox(scan_frame)
        self.scan.pack(fill=tk.BOTH,expand=True)

        top_frame=tk.LabelFrame(root,text="Top Signals")
        top_frame.pack(fill=tk.BOTH,expand=True,padx=10,pady=5)

        cols=("Rank","Coin","Signal","Score","Profit")

        self.tree=ttk.Treeview(top_frame,columns=cols,show="headings")

        for c in cols:
            self.tree.heading(c,text=c)
            self.tree.column(c,width=120)

        self.tree.pack(fill=tk.BOTH,expand=True)

        self.tree.tag_configure("buy",foreground="green")
        self.tree.tag_configure("sell",foreground="red")

        self.update_gui()

    def update_gui(self):

        self.update_label.config(
            text="Update "+datetime.now().strftime("%H:%M:%S")
        )

        total=pair_stats["total"]
        scanned=pair_stats["scanned"]

        if total>0:
            percent=(scanned/total)*100
        else:
            percent=0

        self.progress["value"]=percent

        self.pairs.config(
            text=f"Pairs {scanned}/{total}"
        )

        self.timer.config(
            text=f"Round {pair_stats.get('round_time',0)}s"
        )

        self.scan.delete(0,tk.END)

        for s in scan_log[-30:]:
            self.scan.insert(tk.END,s)

        for r in self.tree.get_children():
            self.tree.delete(r)

        rank=1

        for c in top_candidates[:10]:

            row=self.tree.insert(
                "",
                tk.END,
                values=(
                    rank,
                    c["symbol"],
                    c["signal"],
                    c["score"],
                    c["profit"]
                )
            )

            if c["signal"]=="BUY":
                self.tree.item(row,tags=("buy",))

            if c["signal"]=="SELL":
                self.tree.item(row,tags=("sell",))

            rank+=1

        self.root.after(1500,self.update_gui)