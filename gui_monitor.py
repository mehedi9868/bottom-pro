"""
GUI Monitor
========================
এই ফাইলটি শুধু Bot এর GUI দেখানোর জন্য।

এখানে দেখায়:
- Top 30 scanned coins
- Best signal coins
- Trade buttons (BUY / SELL / CLOSE)
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime


# ===============================
# GLOBAL SHARED DATA
# ===============================

# Top 30 scanned coins
top30=[]

# Best signal candidates
top_candidates=[]

# Scan statistics
pair_stats={
    "total":0,
    "scanned":0,
    "last_scan":""
}

# Bot callbacks (bot থেকে control)
close_callback=None
buy_callback=None
sell_callback=None


# ===============================
# MAIN GUI CLASS
# ===============================

class BotGUI:

    def __init__(self,root,close_fn,buy_fn,sell_fn):

        """
        root = tkinter root
        close_fn = close trade callback
        buy_fn = manual buy callback
        sell_fn = manual sell callback
        """

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

        # ===============================
        # TOP STATUS BAR
        # ===============================

        topbar=tk.Frame(root,bg="#111")
        topbar.pack(fill=tk.X,pady=5)

        # Time label
        self.time_label=tk.Label(
            topbar,
            text="",
            fg="white",
            bg="#111",
            font=("Arial",11)
        )
        self.time_label.pack(side=tk.LEFT,padx=10)

        # Scan status
        self.scan_label=tk.Label(
            topbar,
            text="",
            fg="white",
            bg="#111",
            font=("Arial",11)
        )
        self.scan_label.pack(side=tk.LEFT,padx=20)

        # Scan progress bar
        self.progress=ttk.Progressbar(topbar,length=300)
        self.progress.pack(side=tk.RIGHT,padx=20)


        # ===============================
        # TOP 30 COIN LIST
        # ===============================

        frame1=tk.LabelFrame(
            root,
            text="Top 30 Coins",
            fg="white",
            bg="#111"
        )
        frame1.pack(fill=tk.BOTH,expand=True,padx=10,pady=5)

        self.list30=tk.Listbox(frame1,font=("Arial",10))
        self.list30.pack(fill=tk.BOTH,expand=True,padx=5,pady=5)


        # ===============================
        # SIGNAL TABLE
        # ===============================

        frame2=tk.LabelFrame(
            root,
            text="Top Signals",
            fg="white",
            bg="#111"
        )
        frame2.pack(fill=tk.BOTH,expand=True,padx=10,pady=5)

        cols=(
            "Rank","Coin","Signal","Score",
            "Entry","SL","TP","PNL",
            "BUY","SELL","CLOSE"
        )

        self.tree=ttk.Treeview(
            frame2,
            columns=cols,
            show="headings",
            height=15
        )

        widths=[50,90,80,70,100,100,100,70,70,70,80]

        for i,c in enumerate(cols):
            self.tree.heading(c,text=c)
            self.tree.column(c,width=widths[i],anchor="center")

        self.tree.pack(fill=tk.BOTH,expand=True)

        # Color tags
        self.tree.tag_configure("profit",foreground="#00ff7f")
        self.tree.tag_configure("loss",foreground="#ff5c5c")

        # Click handler
        self.tree.bind("<Button-1>",self.on_click)

        # Start GUI refresh loop
        self.update_gui()


    # ===============================
    # BUTTON CLICK HANDLER
    # ===============================

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


    # ===============================
    # GUI UPDATE LOOP
    # ===============================

    def update_gui(self):

        # Time update
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


        # -------- Top30 coins --------

        self.list30.delete(0,tk.END)

        for c in top30:
            self.list30.insert(tk.END,c)


        # -------- Signal table --------

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

            # Color PNL
            if c["pnl"]>0:
                self.tree.item(row,tags=("profit",))
            elif c["pnl"]<0:
                self.tree.item(row,tags=("loss",))

            rank+=1

        # GUI refresh interval
        self.root.after(1500,self.update_gui)