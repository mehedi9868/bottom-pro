import tkinter as tk
from tkinter import ttk
from datetime import datetime

top30=[]
top_candidates=[]
pair_stats={"total":0,"scanned":0,"last_scan":""}

close_callback=None
buy_callback=None
sell_callback=None


class BotGUI:

    def __init__(self,root,close_fn,buy_fn,sell_fn):

        global close_callback,buy_callback,sell_callback

        close_callback=close_fn
        buy_callback=buy_fn
        sell_callback=sell_fn

        self.root=root
        root.title("AI Futures Bot PRO")
        root.geometry("1250x720")
        root.configure(bg="#111")

        style=ttk.Style()
        style.theme_use("default")

        # ---------- TOP BAR ----------

        topbar=tk.Frame(root,bg="#111")
        topbar.pack(fill=tk.X,pady=5)

        self.time_label=tk.Label(topbar,text="",fg="white",bg="#111",font=("Arial",11))
        self.time_label.pack(side=tk.LEFT,padx=10)

        self.scan_label=tk.Label(topbar,text="",fg="white",bg="#111",font=("Arial",11))
        self.scan_label.pack(side=tk.LEFT,padx=20)

        self.progress=ttk.Progressbar(topbar,length=300)
        self.progress.pack(side=tk.RIGHT,padx=20)

        # ---------- COIN LIST ----------

        frame1=tk.LabelFrame(root,text="Top 30 Coins",fg="white",bg="#111")
        frame1.pack(fill=tk.BOTH,expand=True,padx=10,pady=5)

        self.list30=tk.Listbox(frame1,font=("Arial",10))
        self.list30.pack(fill=tk.BOTH,expand=True,padx=5,pady=5)

        # ---------- SIGNAL TABLE ----------

        frame2=tk.LabelFrame(root,text="Top Signals",fg="white",bg="#111")
        frame2.pack(fill=tk.BOTH,expand=True,padx=10,pady=5)

        cols=("Rank","Coin","Signal","Score","Entry","SL","TP","PNL","BUY","SELL","CLOSE")

        self.tree=ttk.Treeview(frame2,columns=cols,show="headings",height=15)

        widths=[50,90,80,70,100,100,100,70,70,70,80]

        for i,c in enumerate(cols):
            self.tree.heading(c,text=c)
            self.tree.column(c,width=widths[i],anchor="center")

        self.tree.pack(fill=tk.BOTH,expand=True)

        self.tree.tag_configure("buy",foreground="#00ff7f")
        self.tree.tag_configure("sell",foreground="#ff5c5c")
        self.tree.tag_configure("profit",foreground="#00ff7f")
        self.tree.tag_configure("loss",foreground="#ff5c5c")

        self.tree.bind("<Button-1>",self.on_click)

        self.update_gui()

    def on_click(self,event):

        item=self.tree.identify_row(event.y)
        col=self.tree.identify_column(event.x)

        if not item:
            return

        symbol=self.tree.item(item,"values")[1]

        # BUY button
        if col=="#9":
            if buy_callback:
                buy_callback(symbol,"BUY")

        # SELL button
        elif col=="#10":
            if sell_callback:
                sell_callback(symbol,"SELL")

        # CLOSE button
        elif col=="#11":
            if close_callback:
                close_callback(symbol)

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
                    round(c["entry"],4),
                    round(c["sl"],4),
                    round(c["tp"],4),
                    c["pnl"],
                    "BUY",
                    "SELL",
                    "CLOSE"
                )
            )

            if c["pnl"]>0:
                self.tree.item(row,tags=("profit",))

            elif c["pnl"]<0:
                self.tree.item(row,tags=("loss",))

            rank+=1

        self.root.after(1500,self.update_gui)