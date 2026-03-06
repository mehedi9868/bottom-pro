import tkinter as tk
from tkinter import ttk
from datetime import datetime

top30=[]
top_candidates=[]
pair_stats={"total":0,"scanned":0,"last_scan":""}

class BotGUI:

    def __init__(self,root):

        self.root=root
        root.title("AI Futures Scanner")
        root.geometry("1200x720")

        topbar=tk.Frame(root)
        topbar.pack(fill=tk.X)

        self.time_label=tk.Label(topbar,text="")
        self.time_label.pack(side=tk.LEFT,padx=10)

        self.scan_label=tk.Label(topbar,text="")
        self.scan_label.pack(side=tk.LEFT,padx=20)

        self.progress=ttk.Progressbar(topbar,length=300)
        self.progress.pack(side=tk.RIGHT,padx=20)

        frame1=tk.LabelFrame(root,text="Selected 30 Coins")
        frame1.pack(fill=tk.BOTH,expand=True,padx=10,pady=5)

        self.list30=tk.Listbox(frame1)
        self.list30.pack(fill=tk.BOTH,expand=True)

        frame2=tk.LabelFrame(root,text="Top 10 Signals")
        frame2.pack(fill=tk.BOTH,expand=True,padx=10,pady=5)

        cols=("Rank","Coin","Signal","Score","Profit%","Entry","SL","TP")

        self.tree=ttk.Treeview(frame2,columns=cols,show="headings")

        for c in cols:
            self.tree.heading(c,text=c)
            self.tree.column(c,width=110)

        self.tree.pack(fill=tk.BOTH,expand=True)

        self.tree.tag_configure("buy",foreground="green")
        self.tree.tag_configure("sell",foreground="red")

        self.update_gui()

    def update_gui(self):

        self.time_label.config(
            text="Time: "+datetime.now().strftime("%H:%M:%S")
        )

        total=pair_stats["total"]
        scanned=pair_stats["scanned"]

        percent=0
        if total>0:
            percent=(scanned/total)*100

        self.progress["value"]=percent

        self.scan_label.config(
            text=f"Pairs {scanned}/{total} | Last Scan {pair_stats['last_scan']}"
        )

        self.list30.delete(0,tk.END)

        for c in top30:
            self.list30.insert(tk.END,c)

        for r in self.tree.get_children():
            self.tree.delete(r)

        rank=1

        for c in top_candidates:

            row=self.tree.insert(
                "",
                tk.END,
                values=(
                    rank,
                    c["symbol"],
                    c["signal"],
                    c["score"],
                    c["profit"],
                    c["entry"],
                    c["sl"],
                    c["tp"]
                )
            )

            if c["signal"]=="BUY":
                self.tree.item(row,tags=("buy",))

            if c["signal"]=="SELL":
                self.tree.item(row,tags=("sell",))

            rank+=1

        self.root.after(1500,self.update_gui)