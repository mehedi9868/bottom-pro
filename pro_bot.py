import time
import threading
import statistics
from datetime import datetime,timedelta

from binance.client import Client
import tkinter as tk

from gui_monitor import top30,top_candidates,pair_stats,BotGUI

API_KEY=""
API_SECRET=""

client=Client(API_KEY,API_SECRET)

print("AI Scanner Started")

STOP_LOSS_PERCENT=2
TAKE_PROFIT_PERCENT=10

info=client.futures_exchange_info()

ACTIVE_SYMBOLS=[]

for s in info["symbols"]:

    if s["status"]!="TRADING":
        continue

    if not s["symbol"].endswith("USDT"):
        continue

    ACTIVE_SYMBOLS.append(s["symbol"])

pair_stats["total"]=len(ACTIVE_SYMBOLS)

next_scan=datetime.now()

active_30=[]

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

    klines=client.futures_klines(
        symbol=symbol,
        interval="5m",
        limit=120
    )

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

    support=min(lows[-20:])
    resistance=max(highs[-20:])

    up=(resistance-price)/price*100
    down=(price-support)/price*100

    profit=max(up,down)

    entry=price

    sl=round(entry*(1-STOP_LOSS_PERCENT/100),6)

    tp=round(entry*(1+TAKE_PROFIT_PERCENT/100),6)

    if score>100:
        score=100

    signal="HOLD"

    if score>=80:
        signal="BUY"

    if score<=20:
        signal="SELL"

    return {
        "symbol":symbol,
        "score":round(score,2),
        "signal":signal,
        "profit":round(profit,2),
        "entry":round(entry,6),
        "sl":sl,
        "tp":tp
    }

def bot_loop():

    global next_scan,active_30

    while True:

        try:

            now=datetime.now()

            if now>=next_scan:

                print("FULL MARKET SCAN")

                active_30=fast_scan()

                top30.clear()

                t=datetime.now().strftime("%H:%M")

                for s in active_30:
                    top30.append(f"{t}  {s}")

                pair_stats["last_scan"]=t

                next_scan=now+timedelta(hours=1)

            results=[]

            pair_stats["scanned"]=0

            for s in active_30:

                pair_stats["scanned"]+=1

                try:

                    r=indicator_score(s)

                    results.append(r)

                except:
                    pass

            results.sort(
                key=lambda x:(x["score"],x["profit"]),
                reverse=True
            )

            top_candidates.clear()

            for r in results[:10]:
                top_candidates.append(r)

            time.sleep(20)

        except Exception as e:

            print("ERROR:",e)

            time.sleep(5)

threading.Thread(target=bot_loop,daemon=True).start()

root=tk.Tk()
BotGUI(root)
root.mainloop()