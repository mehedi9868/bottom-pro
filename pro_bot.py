import json
import time
import threading
import statistics
import math
from datetime import datetime,timedelta

from binance.client import Client
from binance.enums import *

import tkinter as tk
from gui_monitor import top30,top_candidates,pair_stats,BotGUI


# ---------------- CONFIG ----------------

with open("config.json") as f:
    config=json.load(f)

API_KEY=config["api_key"]
API_SECRET=config["api_secret"]

LEVERAGE=config["LEVERAGE"]
TRADE_SIZE=config["TRADE_SIZE"]
MAX_TRADES=config["MAX_TRADES"]
MARGIN_TYPE=config["MARGIN_TYPE"]

STOP_LOSS_PERCENT=.01
TAKE_PROFIT_PERCENT=10

TRAIL_START=3
TRAIL_STEP=1


client=Client(API_KEY,API_SECRET)

symbol_filters={}
active_trades={}
active_30=[]
next_scan=datetime.now()


# ---------------- LOAD SYMBOL INFO ----------------

def load_symbols():

    info=client.futures_exchange_info()

    for s in info["symbols"]:

        symbol=s["symbol"]

        if not symbol.endswith("USDT"):
            continue

        step=None
        min_qty=None

        for f in s["filters"]:

            if f["filterType"]=="LOT_SIZE":

                step=float(f["stepSize"])
                min_qty=float(f["minQty"])

        symbol_filters[symbol]={
            "step":step,
            "min_qty":min_qty
        }


load_symbols()

ACTIVE_SYMBOLS=list(symbol_filters.keys())

pair_stats["total"]=len(ACTIVE_SYMBOLS)


# ---------------- SAFE QUANTITY ----------------

def format_quantity(symbol,qty):

    step=symbol_filters[symbol]["step"]

    precision=int(round(-math.log(step,10),0))

    qty=math.floor(qty*(10**precision))/(10**precision)

    return qty


def safe_quantity(symbol,price):

    qty=TRADE_SIZE/price

    min_notional=5.5

    if qty*price<min_notional:
        qty=min_notional/price

    qty=format_quantity(symbol,qty)

    if qty<symbol_filters[symbol]["min_qty"]:
        qty=symbol_filters[symbol]["min_qty"]

    return qty


# ---------------- MARGIN ----------------

def set_margin(symbol):

    try:
        client.futures_change_margin_type(
            symbol=symbol,
            marginType=MARGIN_TYPE
        )
    except:
        pass


# ---------------- PNL ----------------

def calculate_pnl(symbol):

    trade=active_trades.get(symbol)

    if not trade:
        return 0

    price=float(client.futures_mark_price(symbol=symbol)["markPrice"])

    entry=trade["entry"]

    pnl=((price-entry)/entry)*100

    if trade["side"]=="SELL":
        pnl=-pnl

    return round(pnl,2)


# ---------------- FAST SCAN ----------------

def fast_scan():

    tickers=client.futures_ticker()

    results=[]

    for t in tickers:

        symbol=t["symbol"]

        if symbol not in ACTIVE_SYMBOLS:
            continue

        volume=float(t["quoteVolume"])
        change=float(t["priceChangePercent"])
        high=float(t["highPrice"])
        low=float(t["lowPrice"])
        price=float(t["lastPrice"])

        if price<=0:
            continue

        volatility=((high-low)/price)*100

        score=0

        if volume>30000000:
            score+=30

        if volatility>5:
            score+=30

        if abs(change)>3:
            score+=20

        results.append((symbol,score))

    results.sort(key=lambda x:x[1],reverse=True)

    return [r[0] for r in results[:30]]


# ---------------- SIGNAL ----------------

def indicator_score(symbol):

    klines=client.futures_klines(symbol=symbol,interval="5m",limit=120)

    closes=[float(k[4]) for k in klines]
    highs=[float(k[2]) for k in klines]
    volumes=[float(k[5]) for k in klines]

    price=closes[-1]

    score=50

    ema20=sum(closes[-20:])/20
    ema50=sum(closes[-50:])/50

    if ema20>ema50:
        score+=15
    else:
        score-=15

    avg_vol=statistics.mean(volumes[:-1])

    if volumes[-1]>avg_vol*1.8:
        score+=10

    breakout=max(highs[-20:-1])

    if price>breakout:
        score+=10

    entry=price
    sl=entry*(1-STOP_LOSS_PERCENT/100)
    tp=entry*(1+TAKE_PROFIT_PERCENT/100)

    signal="HOLD"

    if score>=70:
        signal="BUY"

    if score<=30:
        signal="SELL"

    pnl=calculate_pnl(symbol)

    return {
        "symbol":symbol,
        "score":score,
        "signal":signal,
        "entry":entry,
        "sl":sl,
        "tp":tp,
        "pnl":pnl
    }


# ---------------- OPEN TRADE ----------------
def open_trade(symbol,side):

    if symbol in active_trades:
        return

    if len(active_trades)>=MAX_TRADES:
        return

    price=float(client.futures_mark_price(symbol=symbol)["markPrice"])

    qty=safe_quantity(symbol,price)

    try:

        set_margin(symbol)

        client.futures_change_leverage(
            symbol=symbol,
            leverage=LEVERAGE
        )

        # MARKET ENTRY
        client.futures_create_order(
            symbol=symbol,
            side=SIDE_BUY if side=="BUY" else SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=qty
        )

        entry=price

        # TP SL CALCULATION
        if side=="BUY":
            sl=entry*(1-STOP_LOSS_PERCENT/100)
            tp=entry*(1+TAKE_PROFIT_PERCENT/100)
            close_side=SIDE_SELL
        else:
            sl=entry*(1+STOP_LOSS_PERCENT/100)
            tp=entry*(1-TAKE_PROFIT_PERCENT/100)
            close_side=SIDE_BUY

        active_trades[symbol]={
            "side":side,
            "entry":entry,
            "sl":sl,
            "tp":tp,
            "highest":entry
        }

        # STOP LOSS ORDER
        client.futures_create_order(
            symbol=symbol,
            side=close_side,
            type="STOP_MARKET",
            stopPrice=round(sl,6),
            workingType="MARK_PRICE",
            closePosition=True
        )

        # TAKE PROFIT ORDER
        client.futures_create_order(
            symbol=symbol,
            side=close_side,
            type="TAKE_PROFIT_MARKET",
            stopPrice=round(tp,6),
            workingType="MARK_PRICE",
            closePosition=True
        )

        print(f"TRADE OPENED {symbol} {side} | Entry:{entry} TP:{tp} SL:{sl}")

    except Exception as e:
        print("TRADE ERROR:",e)

    if symbol in active_trades:
        return

    if len(active_trades)>=MAX_TRADES:
        return

    price=float(client.futures_mark_price(symbol=symbol)["markPrice"])

    qty=safe_quantity(symbol,price)

    try:

        set_margin(symbol)

        client.futures_change_leverage(
            symbol=symbol,
            leverage=LEVERAGE
        )

        # MARKET ENTRY
        client.futures_create_order(
            symbol=symbol,
            side=SIDE_BUY if side=="BUY" else SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=qty
        )

        entry=price

        # TP SL CALCULATION
        if side=="BUY":
            sl=entry*(1-STOP_LOSS_PERCENT/100)
            tp=entry*(1+TAKE_PROFIT_PERCENT/100)
            close_side=SIDE_SELL
        else:
            sl=entry*(1+STOP_LOSS_PERCENT/100)
            tp=entry*(1-TAKE_PROFIT_PERCENT/100)
            close_side=SIDE_BUY

        active_trades[symbol]={
            "side":side,
            "entry":entry,
            "sl":sl,
            "tp":tp,
            "highest":entry
        }

        # STOP LOSS ORDER
        client.futures_create_order(
            symbol=symbol,
            side=close_side,
            type="STOP_MARKET",
            stopPrice=round(sl,6),
            workingType="MARK_PRICE",
            closePosition=True
        )

        # TAKE PROFIT ORDER
        client.futures_create_order(
            symbol=symbol,
            side=close_side,
            type="TAKE_PROFIT_MARKET",
            stopPrice=round(tp,6),
            workingType="MARK_PRICE",
            closePosition=True
        )

        print(f"TRADE OPENED {symbol} {side} | Entry:{entry} TP:{tp} SL:{sl}")

    except Exception as e:
        print("TRADE ERROR:",e)

    if symbol in active_trades:
        return

    if len(active_trades)>=MAX_TRADES:
        return

    price=float(client.futures_mark_price(symbol=symbol)["markPrice"])

    qty=safe_quantity(symbol,price)

    try:

        set_margin(symbol)

        client.futures_change_leverage(
            symbol=symbol,
            leverage=LEVERAGE
        )

        # OPEN MARKET ORDER
        client.futures_create_order(
            symbol=symbol,
            side=SIDE_BUY if side=="BUY" else SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=qty
        )

        entry=price

        # TP SL CALCULATION
        if side=="BUY":
            sl=entry*(1-STOP_LOSS_PERCENT/100)
            tp=entry*(1+TAKE_PROFIT_PERCENT/100)
            close_side=SIDE_SELL
        else:
            sl=entry*(1+STOP_LOSS_PERCENT/100)
            tp=entry*(1-TAKE_PROFIT_PERCENT/100)
            close_side=SIDE_BUY

        active_trades[symbol]={
            "side":side,
            "entry":entry,
            "sl":sl,
            "tp":tp,
            "highest":entry
        }

        # STOP LOSS ORDER
        # client.futures_create_order(
        #     symbol=symbol,
        #     side=close_side,
        #     type="STOP_MARKET",
        #     stopPrice=round(sl,4),
        #     closePosition=True
        # )

        # TAKE PROFIT ORDER
        client.futures_create_order(
            symbol=symbol,
            side=close_side,
            type="TAKE_PROFIT_MARKET",
            stopPrice=round(tp,4),
            closePosition=True
        )

    except Exception as e:
        print(e)

    if symbol in active_trades:
        return

    if len(active_trades)>=MAX_TRADES:
        return

    price=float(client.futures_mark_price(symbol=symbol)["markPrice"])

    qty=safe_quantity(symbol,price)

    try:

        set_margin(symbol)

        client.futures_change_leverage(
            symbol=symbol,
            leverage=LEVERAGE
        )

        client.futures_create_order(
            symbol=symbol,
            side=SIDE_BUY if side=="BUY" else SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=qty
        )

        entry=price

        active_trades[symbol]={
            "side":side,
            "entry":entry,
            "sl":entry*(1-STOP_LOSS_PERCENT/100),
            "tp":entry*(1+TAKE_PROFIT_PERCENT/100),
            "highest":entry
        }

        # TAKE PROFIT ORDER
        client.futures_create_order(
            symbol=symbol,
            side=close_side,
            type="TAKE_PROFIT_MARKET",
            stopPrice=round(tp,4),
            closePosition=True
        )

    except Exception as e:
        print(e)


# ---------------- CLOSE TRADE ----------------

def close_trade(symbol):

    if symbol not in active_trades:
        return

    trade=active_trades[symbol]

    side=SIDE_SELL if trade["side"]=="BUY" else SIDE_BUY

    price=float(client.futures_mark_price(symbol=symbol)["markPrice"])

    qty=safe_quantity(symbol,price)

    try:

        client.futures_create_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=qty
        )

    except Exception as e:
        print(e)

    del active_trades[symbol]


# ---------------- TRADE MONITOR ----------------

def monitor_trades():

    while True:

        for symbol in list(active_trades.keys()):

            price=float(client.futures_mark_price(symbol=symbol)["markPrice"])

            trade=active_trades[symbol]

            if price>=trade["tp"] or price<=trade["sl"]:
                close_trade(symbol)

        time.sleep(3)


# ---------------- BOT LOOP ----------------

def bot_loop():

    global next_scan,active_30

    while True:

        now=datetime.now()

        if now>=next_scan:

            active_30=fast_scan()

            top30.clear()

            t=datetime.now().strftime("%H:%M")

            for s in active_30:
                top30.append(f"{t} {s}")

            pair_stats["last_scan"]=t

            next_scan=now+timedelta(hours=1)

        results=[]

        pair_stats["scanned"]=0

        for s in active_30:

            pair_stats["scanned"]+=1

            try:

                r=indicator_score(s)

                results.append(r)

                if r["score"] >= 60:
                 open_trade(s,"BUY")

                elif r["score"] <= 40:
                    open_trade(s,"SELL")

            except:
                pass

        results.sort(key=lambda x:x["score"],reverse=True)

        top_candidates.clear()

        for r in results[:10]:
            top_candidates.append(r)

        time.sleep(20)


# ---------------- THREADS ----------------

threading.Thread(target=bot_loop,daemon=True).start()
threading.Thread(target=monitor_trades,daemon=True).start()


# ---------------- GUI ----------------

root=tk.Tk()

BotGUI(root,close_trade,open_trade,open_trade)

root.mainloop()