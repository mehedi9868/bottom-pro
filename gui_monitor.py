import tkinter as tk
from tkinter import ttk
from datetime import datetime

open_trades=[]
signal_log=[]
scan_log=[]
top_candidates=[]

pair_stats={
    "total":0,
    "scanned":0,
    "round_time":0
}

class BotGUI:

    def __init__(self,root):

        self.root=root
        root.title("Crypto Trading Terminal")
        root.geometry("1300x780")

        bar=tk.Frame(root)
        bar.pack(fill=tk.X)

        self.balance=tk.Label(bar,text="Balance: 0 USDT")
        self.balance.pack(side=tk.LEFT,padx=10)

        self.update_label=tk.Label(bar,text="")
        self.update_label.pack(side=tk.LEFT,padx=10)

        self.pairs=tk.Label(bar,text="Pairs: 0/0")
        self.pairs.pack(side=tk.LEFT,padx=20)

        log_frame=tk.LabelFrame(root,text="Signals")
        log_frame.pack(fill=tk.X,padx=10,pady=5)

        self.log=tk.Text(log_frame,height=8)
        self.log.pack(fill=tk.X)

        trade_frame=tk.LabelFrame(root,text="Open Trades")
        trade_frame.pack(fill=tk.BOTH,expand=True,padx=10,pady=5)

        cols=("Symbol","Entry","Current","TP","SL","PnL","Status")

        self.tree=ttk.Treeview(trade_frame,columns=cols,show="headings")

        for c in cols:
            self.tree.heading(c,text=c)
            self.tree.column(c,width=120)

        self.tree.pack(fill=tk.BOTH,expand=True)

        self.tree.tag_configure("profit",foreground="green")
        self.tree.tag_configure("loss",foreground="red")

        btn_frame=tk.Frame(root)
        btn_frame.pack(fill=tk.X)

        close_btn=tk.Button(btn_frame,text="Close Selected Trade",
                            command=self.close_trade)

        close_btn.pack(side=tk.RIGHT,padx=10)

        bottom=tk.Frame(root)
        bottom.pack(fill=tk.BOTH,expand=True)

        scan_frame=tk.LabelFrame(bottom,text="Scanning")
        scan_frame.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)

        self.scan_timer=tk.Label(scan_frame,text="Round Time: 0s")
        self.scan_timer.pack()

        self.progress=ttk.Progressbar(
            scan_frame,
            orient="horizontal",
            length=350,
            mode="determinate"
        )

        self.progress.pack(pady=5)

        self.scan=tk.Listbox(scan_frame)
        self.scan.pack(fill=tk.BOTH,expand=True)

        top_frame=tk.LabelFrame(bottom,text="Top Movers")
        top_frame.pack(side=tk.RIGHT,fill=tk.BOTH,expand=True)

        self.top=ttk.Treeview(
            top_frame,
            columns=("Coin","Percent"),
            show="headings"
        )

        self.top.heading("Coin",text="Coin")
        self.top.heading("Percent",text="% Change")

        self.top.pack(fill=tk.BOTH,expand=True)

        buy_btn=tk.Button(
            top_frame,
            text="Manual BUY",
            command=self.manual_buy
        )

        buy_btn.pack(pady=5)

        self.update_gui()

    def manual_buy(self):

        selected=self.top.selection()

        if not selected:
            return

        item=self.top.item(selected[0])

        symbol=item["values"][0]

        try:
            from pro_bot import manual_buy
            manual_buy(symbol)
        except:
            pass

    def close_trade(self):

        selected=self.tree.selection()

        if not selected:
            return

        item=self.tree.item(selected[0])

        symbol=item["values"][0]

        try:
            from pro_bot import close_position
            close_position(symbol)
        except:
            pass

    def update_gui(self):

        self.update_label.config(
            text="Last Update: "+datetime.now().strftime("%H:%M:%S")
        )

        try:
            from pro_bot import get_futures_balance
            bal=get_futures_balance()
            self.balance.config(text=f"Balance: {round(bal,2)} USDT")
        except:
            pass

        self.pairs.config(
            text=f"Pairs: {pair_stats['scanned']} / {pair_stats['total']}"
        )

        total=pair_stats["total"]
        scanned=pair_stats["scanned"]

        if total>0:
            percent=(scanned/total)*100
        else:
            percent=0

        self.progress["value"]=percent

        self.scan_timer.config(
            text=f"Round Time: {pair_stats.get('round_time',0)}s"
        )

        while signal_log:
            msg=signal_log.pop(0)
            t=datetime.now().strftime("%H:%M:%S")
            self.log.insert(tk.END,f"[{t}] {msg}\n")
            self.log.see(tk.END)

        for r in self.tree.get_children():
            self.tree.delete(r)

        for t in open_trades:

            row=self.tree.insert(
                "",
                tk.END,
                values=(
                    t["symbol"],
                    round(t["entry"],4),
                    round(t["current"],4),
                    round(t["tp"],4),
                    round(t["atr_stop"],4),
                    round(t["pnl"],2),
                    t["status"]
                )
            )

            if t["pnl"]>=0:
                self.tree.item(row,tags=("profit",))
            else:
                self.tree.item(row,tags=("loss",))

        self.scan.delete(0,tk.END)

        for s in scan_log[-20:]:
            self.scan.insert(tk.END,s)

        for r in self.top.get_children():
            self.top.delete(r)

        for c in top_candidates[:10]:
            self.top.insert("",tk.END,values=(c["symbol"],c["score"]))

        self.root.after(1500,self.update_gui)