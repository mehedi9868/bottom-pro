import json
import time
import threading
import statistics
from datetime import datetime,timedelta

from binance.client import Client
from binance.enums import *

import tkinter as tk
from gui_monitor import top30,top_candidates,pair_stats,BotGUI

with open("config.json") as f:
    config=json.load(f)

API_KEY=config["api_key"]
API_SECRET=config["api_secret"]

LEVERAGE=config["LEVERAGE"]
TRADE_SIZE=config["TRADE_SIZE"]
MAX_TRADES=config["MAX_TRADES"]
MARGIN_TYPE=config["MARGIN_TYPE"]

STOP_LOSS_PERCENT=2
TAKE_PROFIT_PERCENT=10

TRAIL_START=3
TRAIL_STEP=1

client=Client(API_KEY,API_SECRET)

symbol_precision={}
active_trades={}
active_30=[]
next_scan=datetime.now()

def load_symbols():

    info=client.futures_exchange_info()

    for s in info["symbols"]:

        symbol=s["symbol"]

        if not symbol.endswith("USDT"):
            continue

        for f in s["filters"]:

            if f["filterType"]=="LOT_SIZE":

                step=float(f["stepSize"])
                precision=str(step)[::-1].find('.')

                symbol_precision[symbol]=precision

load_symbols()

ACTIVE_SYMBOLS=list(symbol_precision.keys())

pair_stats["total"]=len(ACTIVE_SYMBOLS)

def format_qty(symbol,qty):

    precision=symbol_precision.get(symbol,3)
    return round(qty,precision)

def adjust_min_notional(symbol,price,qty):

    if price*qty<5:
        qty=5/price

    return qty

def set_margin(symbol):

    try:

        client.futures_change_margin_type(
            symbol=symbol,
            marginType=MARGIN_TYPE
        )

    except:
        pass

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

def indicator_score(symbol):

    klines=client.futures_klines(symbol=symbol,interval="5m",limit=120)

    closes=[float(k[4]) for k in klines]
    highs=[float(k[2]) for k in klines]
    lows=[float(k[3]) for k in klines]
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

    if score>=80:
        signal="BUY"

    if score<=20:
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

def open_trade(symbol,side):

    if symbol in active_trades:
        return

    if len(active_trades)>=MAX_TRADES:
        return

    price=float(client.futures_mark_price(symbol=symbol)["markPrice"])

    qty=TRADE_SIZE/price

    qty=adjust_min_notional(symbol,price,qty)
    qty=format_qty(symbol,qty)

    try:

        set_margin(symbol)

        client.futures_change_leverage(symbol=symbol,leverage=LEVERAGE)

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

    except Exception as e:
        print(e)

def close_trade(symbol):

    if symbol not in active_trades:
        return

    trade=active_trades[symbol]

    side=SIDE_SELL if trade["side"]=="BUY" else SIDE_BUY

    price=float(client.futures_mark_price(symbol=symbol)["markPrice"])

    qty=TRADE_SIZE/price

    qty=format_qty(symbol,qty)

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

def update_trailing(symbol,price):

    trade=active_trades[symbol]

    entry=trade["entry"]

    profit=((price-entry)/entry)*100

    if profit>TRAIL_START:

        if price>trade["highest"]:

            trade["highest"]=price

            new_sl=price*(1-TRAIL_STEP/100)

            if new_sl>trade["sl"]:
                trade["sl"]=new_sl

def monitor_trades():

    while True:

        positions=client.futures_position_information()

        exchange_symbols=set()

        for p in positions:

            qty=float(p["positionAmt"])

            if qty!=0:
                exchange_symbols.add(p["symbol"])

        for symbol in list(active_trades.keys()):

            if symbol not in exchange_symbols:
                del active_trades[symbol]
                continue

            price=float(client.futures_mark_price(symbol=symbol)["markPrice"])

            update_trailing(symbol,price)

            trade=active_trades[symbol]

            if price>=trade["tp"] or price<=trade["sl"]:
                close_trade(symbol)

        time.sleep(3)

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

                if r["score"]>=80:
                    open_trade(s,"BUY")

            except:
                pass

        results.sort(key=lambda x:x["score"],reverse=True)

        top_candidates.clear()

        for r in results[:10]:
            top_candidates.append(r)

        time.sleep(20)

threading.Thread(target=bot_loop,daemon=True).start()
threading.Thread(target=monitor_trades,daemon=True).start()

root=tk.Tk()
BotGUI(root,close_trade)
root.mainloop()