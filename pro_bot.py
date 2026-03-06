import json
import time
import threading
import math

from binance.client import Client
import tkinter as tk

from gui_monitor import open_trades,signal_log,scan_log,top_candidates,stats_data,BotGUI


with open("config.json") as f:
    config=json.load(f)

API_KEY=config["api_key"]
API_SECRET=config["api_secret"]

TRADE_SIZE=config["TRADE_SIZE"]
MAX_TRADES=config["MAX_TRADES"]

PRICE_INTERVAL=config["PRICE_INTERVAL"]
CHART_INTERVAL=config["CHART_INTERVAL"]

SCAN_COINS=config["SCAN_COINS"]

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

        order=client.futures_create_order(
            symbol=symbol,
            side="BUY",
            type="MARKET",
            quantity=quantity
        )

        entry=float(order["avgPrice"])

        signal_log.append(f"BUY {symbol} {entry}")

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


def close_position(symbol,margin_type):

    try:

        client.futures_change_margin_type(
            symbol=symbol,
            marginType=margin_type
        )
    except:
        pass

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


def update_trades():

    for t in open_trades:

        try:

            price=get_price(t["symbol"])

            t["current"]=price

            pnl=(price-t["entry"])/t["entry"]*100

            t["pnl"]=pnl

            if price>=t["tp"]:

                t["status"]="TP"
                stats_data["wins"]+=1
                stats_data["profit"]+=pnl

            if price<=t["atr_stop"]:

                t["status"]="SL"
                stats_data["losses"]+=1
                stats_data["profit"]+=pnl

        except:
            pass


def get_top_coins():

    tickers=client.futures_ticker()

    coins=[]

    for t in tickers:

        symbol=t["symbol"]

        if symbol not in ACTIVE_SYMBOLS:
            continue

        volume=float(t["quoteVolume"])

        coins.append({
            "symbol":symbol,
            "volume":volume
        })

    coins.sort(key=lambda x:x["volume"],reverse=True)

    return coins[:SCAN_COINS]


def bot_loop():

    while True:

        try:

            coins=get_top_coins()

            top_candidates.clear()

            for c in coins:

                symbol=c["symbol"]

                scan_log.append(symbol)

                price=get_price(symbol)

                atr=calculate_ATR(symbol)

                score=50

                top_candidates.append({
                    "symbol":symbol,
                    "score":score
                })

                if score>=50 and len(open_trades)<MAX_TRADES:

                    create_trade(symbol,price,atr)

            update_trades()

            time.sleep(30)

        except Exception as e:

            signal_log.append(str(e))

            time.sleep(5)


threading.Thread(target=bot_loop,daemon=True).start()

root=tk.Tk()
BotGUI(root)
root.mainloop()