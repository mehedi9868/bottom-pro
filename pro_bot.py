import json
import time
import threading
import math

from binance.client import Client
import tkinter as tk

from gui_monitor import open_trades,signal_log,scan_log,top_candidates,pair_stats,BotGUI

with open("config.json") as f:
    config=json.load(f)

API_KEY=config["api_key"]
API_SECRET=config["api_secret"]

TRADE_SIZE=config["TRADE_SIZE"]
MAX_TRADES=config["MAX_TRADES"]
PRICE_INTERVAL=config["PRICE_INTERVAL"]
ATR_PERIOD=config["ATR_PERIOD"]

client=Client(API_KEY,API_SECRET)

print("Bot Started")

def get_futures_balance():

    acc=client.futures_account_balance()

    for a in acc:
        if a["asset"]=="USDT":
            return float(a["balance"])

    return 0


info=client.futures_exchange_info()

ACTIVE_SYMBOLS=[]
SYMBOL_INFO={}

for s in info["symbols"]:

    if s["status"]!="TRADING":
        continue

    if s["contractType"]!="PERPETUAL":
        continue

    symbol=s["symbol"]

    if not symbol.endswith("USDT"):
        continue

    filters={f["filterType"]:f for f in s["filters"]}

    ACTIVE_SYMBOLS.append(symbol)

    SYMBOL_INFO[symbol]={
        "min_qty":float(filters["LOT_SIZE"]["minQty"]),
        "step":float(filters["LOT_SIZE"]["stepSize"])
    }

pair_stats["total"]=len(ACTIVE_SYMBOLS)


def format_quantity(qty,step):

    precision=int(round(-math.log(step,10),0))

    return round(qty,precision)


def get_price(symbol):

    return float(
        client.futures_symbol_ticker(symbol=symbol)["price"]
    )


def calculate_ATR(symbol):

    candles=client.futures_klines(
        symbol=symbol,
        interval=PRICE_INTERVAL,
        limit=ATR_PERIOD+1
    )

    trs=[]

    for c in candles[1:]:

        high=float(c[2])
        low=float(c[3])
        close=float(c[4])

        tr=max(high-low,abs(high-close),abs(low-close))

        trs.append(tr)

    return sum(trs)/len(trs)


def create_trade(symbol,price,atr):

    for t in open_trades:
        if t["symbol"]==symbol:
            return

    stop=price-atr*1.5
    tp=price+atr*2

    try:

        info=SYMBOL_INFO[symbol]

        min_qty=info["min_qty"]
        step=info["step"]

        qty=TRADE_SIZE/price

        if qty<min_qty:
            qty=min_qty

        quantity=math.floor(qty/step)*step
        quantity=format_quantity(quantity,step)

        notional=quantity*price

        if notional<5:
            signal_log.append("Order skipped (<5 USDT)")
            return

        order=client.futures_create_order(
            symbol=symbol,
            side="BUY",
            type="MARKET",
            quantity=quantity
        )

        entry=float(order["avgPrice"])

        signal_log.append(f"BUY {symbol}")

        open_trades.append({
            "symbol":symbol,
            "entry":entry,
            "atr_stop":stop,
            "tp":tp,
            "current":entry,
            "pnl":0,
            "status":"OPEN"
        })

    except Exception as e:

        signal_log.append(str(e))


def manual_buy(symbol):

    price=get_price(symbol)
    atr=calculate_ATR(symbol)

    create_trade(symbol,price,atr)


def close_position(symbol):

    try:

        pos=client.futures_position_information(symbol=symbol)

        amt=float(pos[0]["positionAmt"])

        if amt==0:
            return

        side="SELL"

        if amt<0:
            side="BUY"

        client.futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=abs(amt),
            reduceOnly=True
        )

        signal_log.append(f"CLOSE {symbol}")

    except Exception as e:

        signal_log.append(str(e))


def sync_positions():

    positions=client.futures_position_information()

    active={}

    for p in positions:

        amt=float(p["positionAmt"])

        if amt!=0:

            symbol=p["symbol"]
            entry=float(p["entryPrice"])

            active[symbol]=entry

    for t in open_trades[:]:

        if t["symbol"] not in active:
            open_trades.remove(t)


def update_trades():

    sync_positions()

    for t in open_trades:

        try:

            price=get_price(t["symbol"])

            t["current"]=price

            pnl=(price-t["entry"])/t["entry"]*100

            t["pnl"]=pnl

        except:
            pass


def get_top_movers():

    tickers=client.futures_ticker()

    coins=[]

    for t in tickers:

        symbol=t["symbol"]

        if symbol not in ACTIVE_SYMBOLS:
            continue

        change=float(t["priceChangePercent"])

        coins.append({
            "symbol":symbol,
            "percent":change
        })

    coins.sort(key=lambda x:x["percent"],reverse=True)

    return coins[:10]


def bot_loop():

    while True:

        try:

            pair_stats["scanned"]=0

            start=time.time()

            coins=get_top_movers()

            top_candidates.clear()

            for c in coins:

                top_candidates.append({
                    "symbol":c["symbol"],
                    "score":round(c["percent"],2)
                })

            for symbol in ACTIVE_SYMBOLS:

                pair_stats["scanned"]+=1

                scan_log.append(symbol)

                price=get_price(symbol)

                atr=calculate_ATR(symbol)

                score=50

                if score>=50 and len(open_trades)<MAX_TRADES:

                    create_trade(symbol,price,atr)

            pair_stats["round_time"]=round(time.time()-start,2)

            update_trades()

            time.sleep(30)

        except Exception as e:

            signal_log.append(str(e))
            time.sleep(5)


threading.Thread(target=bot_loop,daemon=True).start()

if __name__=="__main__":

    root=tk.Tk()
    BotGUI(root)
    root.mainloop()