import tkinter as tk
from tkinter import ttk
from datetime import datetime

open_trades=[]
signal_log=[]
scan_log=[]
top_candidates=[]

stats_data={
    "wins":0,
    "losses":0,
    "profit":0
}

class BotGUI:

    def __init__(self,root):

        self.root=root
        root.title("Crypto Trading Terminal")
        root.geometry("1300x750")

        bar=tk.Frame(root)
        bar.pack(fill=tk.X)

        self.balance=tk.Label(bar,text="Futures Balance: 0 USDT")
        self.balance.pack(side=tk.LEFT,padx=10)

        self.update_label=tk.Label(bar,text="")
        self.update_label.pack(side=tk.LEFT,padx=10)

        self.winrate=tk.Label(bar,text="WinRate: 0%")
        self.winrate.pack(side=tk.RIGHT,padx=10)

        self.profit=tk.Label(bar,text="Profit: 0%")
        self.profit.pack(side=tk.RIGHT,padx=10)

        log_frame=tk.LabelFrame(root,text="Signals")
        log_frame.pack(fill=tk.X,padx=10,pady=5)

        self.log=tk.Text(log_frame,height=10)
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

        control=tk.Frame(root)
        control.pack(fill=tk.X)

        self.margin_type=tk.StringVar(value="ISOLATED")

        tk.Radiobutton(control,text="Isolated",
                       variable=self.margin_type,
                       value="ISOLATED").pack(side=tk.LEFT,padx=5)

        tk.Radiobutton(control,text="Cross",
                       variable=self.margin_type,
                       value="CROSSED").pack(side=tk.LEFT,padx=5)

        close_btn=tk.Button(control,text="Close Trade",
                            command=self.close_trade)

        close_btn.pack(side=tk.RIGHT,padx=10)

        bottom=tk.Frame(root)
        bottom.pack(fill=tk.BOTH,expand=True)

        scan_frame=tk.LabelFrame(bottom,text="Scanning")
        scan_frame.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)

        self.scan=tk.Listbox(scan_frame)
        self.scan.pack(fill=tk.BOTH,expand=True)

        top_frame=tk.LabelFrame(bottom,text="Top Signals")
        top_frame.pack(side=tk.RIGHT,fill=tk.BOTH,expand=True)

        self.top=ttk.Treeview(top_frame,columns=("Coin","Score"),show="headings")

        self.top.heading("Coin",text="Coin")
        self.top.heading("Score",text="Score")

        self.top.pack(fill=tk.BOTH,expand=True)

        self.update_gui()

    def close_trade(self):

        selected=self.tree.selection()

        if not selected:
            return

        item=self.tree.item(selected[0])

        symbol=item["values"][0]

        try:
            from pro_bot import close_position
            close_position(symbol,self.margin_type.get())
        except:
            pass

    def update_gui(self):

        self.update_label.config(
            text="Last Update: "+datetime.now().strftime("%H:%M:%S")
        )

        try:
            from pro_bot import get_futures_balance
            bal=get_futures_balance()
            self.balance.config(text=f"Futures Balance: {round(bal,2)} USDT")
        except:
            pass

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

        for c in top_candidates[:5]:
            self.top.insert("",tk.END,values=(c["symbol"],c["score"]))

        wins=stats_data["wins"]
        losses=stats_data["losses"]

        total=wins+losses

        if total>0:
            winrate=round((wins/total)*100,2)
        else:
            winrate=0

        self.winrate.config(text=f"WinRate: {winrate}%")
        self.profit.config(text=f"Profit: {round(stats_data['profit'],2)}%")

        self.root.after(1500,self.update_gui)