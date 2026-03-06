import time
import threading
import statistics

from binance.client import Client
import tkinter as tk

from gui_monitor import scan_log,top_candidates,pair_stats,BotGUI

API_KEY=""
API_SECRET=""

client=Client(API_KEY,API_SECRET)

print("Scanner started")

info=client.futures_exchange_info()

ACTIVE_SYMBOLS=[]

for s in info["symbols"]:

    if s["status"]!="TRADING":
        continue

    if s["contractType"]!="PERPETUAL":
        continue

    symbol=s["symbol"]

    if not symbol.endswith("USDT"):
        continue

    ACTIVE_SYMBOLS.append(symbol)

pair_stats["total"]=len(ACTIVE_SYMBOLS)


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

        vol_score=0

        if volume>50000000:
            vol_score=25
        elif volume>20000000:
            vol_score=15
        else:
            vol_score=5

        volatility=((high-low)/price)*100

        volat_score=0

        if volatility>6:
            volat_score=25
        elif volatility>4:
            volat_score=15
        elif volatility>2:
            volat_score=8

        trend_score=0

        if abs(change)>5:
            trend_score=20
        elif abs(change)>3:
            trend_score=15
        elif abs(change)>1:
            trend_score=10

        score=vol_score+volat_score+trend_score

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

    score=50

    ema20=sum(closes[-20:])/20
    ema50=sum(closes[-50:])/50

    if ema20>ema50:
        score+=10
    else:
        score-=10

    avg=statistics.mean(volumes[:-1])

    if volumes[-1]>avg*1.8:
        score+=10

    high=max(highs[-20:-1])

    if closes[-1]>high:
        score+=10

    atr=statistics.mean([highs[i]-lows[i] for i in range(-14,0)])

    if atr/closes[-1]>0.01:
        score+=8

    support=min(lows[-20:])
    resistance=max(highs[-20:])

    up=(resistance-closes[-1])/closes[-1]*100
    down=(closes[-1]-support)/closes[-1]*100

    profit=max(up,down)

    if score>100:
        score=100

    if score<0:
        score=0

    signal="HOLD"

    if score>=60:
        signal="BUY"

    if score<=40:
        signal="SELL"

    return {
        "symbol":symbol,
        "score":round(score,2),
        "signal":signal,
        "profit":round(profit,2)
    }


def bot_loop():

    while True:

        try:

            start=time.time()

            pair_stats["scanned"]=0

            candidates=fast_scan()

            results=[]

            for s in candidates:

                pair_stats["scanned"]+=1

                scan_log.append(s)

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

            pair_stats["round_time"]=round(time.time()-start,2)

            time.sleep(20)

        except Exception as e:

            print(e)

            time.sleep(5)


threading.Thread(target=bot_loop,daemon=True).start()

root=tk.Tk()
BotGUI(root)
root.mainloop()