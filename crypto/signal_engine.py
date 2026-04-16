"""
Crypto Signal Engine — CoinGecko + DeFiLlama + Alternative.me
Layer 1: Market health | Layer 2: Per-coin technicals | Layer 3: Profile thresholds
"""
import json, logging, os, time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import numpy as np, pandas as pd, requests
import yfinance as yf

logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORTFOLIO_FILE = os.path.join(BASE_DIR, "portfolio.json")
PROFILES_FILE = os.path.join(BASE_DIR, "crypto_profiles.json")
STATE_FILE = os.path.join(BASE_DIR, "data", "crypto_state.json")
HISTORY_FILE = os.path.join(BASE_DIR, "data", "crypto_history.json")
SUGGESTIONS_FILE = os.path.join(BASE_DIR, "data", "crypto_suggestions.json")
CG = "https://api.coingecko.com/api/v3"

def load_json(p):
    try:
        with open(p) as f: return json.load(f)
    except: return {}

def save_json(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p,"w") as f: json.dump(d,f,indent=2,default=str)

def _get(url, params=None):
    for i in range(3):
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 429: time.sleep(30); continue
            r.raise_for_status(); return r.json()
        except Exception as e:
            if i == 2: logger.warning(f"GET {url}: {e}")
            time.sleep(2)
    return None

class CryptoSignalEngine:
    def __init__(self):
        self.portfolio = {}; self.profiles = {}; self.market_data = {}
        self.price_history = {}; self.global_data = {}

    def load_config(self):
        self.portfolio = load_json(PORTFOLIO_FILE)
        self.profiles = load_json(PROFILES_FILE)

    def get_coin_ids(self): return [h["coin_id"] for h in self.portfolio.get("holdings",[]) if h.get("coin_id")]

    def fetch_market_data(self):
        ids = ",".join(self.get_coin_ids())
        if not ids: return
        data = _get(f"{CG}/coins/markets", {"vs_currency":"usd","ids":ids,"sparkline":"false","price_change_percentage":"1h,24h,7d,30d"})
        if data: self.market_data = {c["id"]:c for c in data}
        time.sleep(1)

    def fetch_price_history(self):
        for cid in self.get_coin_ids():
            data = _get(f"{CG}/coins/{cid}/market_chart", {"vs_currency":"usd","days":"365","interval":"daily"})
            if data and "prices" in data:
                prices = [p[1] for p in data["prices"]]
                dates = [datetime.fromtimestamp(p[0]/1000) for p in data["prices"]]
                self.price_history[cid] = pd.Series(prices, index=dates)
            time.sleep(1.5)

    def fetch_global_data(self):
        data = _get(f"{CG}/global")
        self.global_data = data.get("data",{}) if data else {}
        time.sleep(1)

    def fetch_fear_greed(self):
        data = _get("https://api.alternative.me/fng/", {"limit":"30"})
        return data.get("data") if data else None

    def fetch_stablecoin_supply(self):
        data = _get("https://api.llama.fi/stablecoins")
        if data and "peggedAssets" in data:
            return sum(s.get("circulating",{}).get("peggedUSD",0) for s in data["peggedAssets"] if s.get("symbol") in ("USDT","USDC","DAI","FDUSD"))
        return None

    def fetch_macro(self):
        macro = {}
        for k, t in [("dxy","DX-Y.NYB"),("treasury_10y","^TNX"),("gold","GC=F")]:
            try:
                h = yf.Ticker(t).history(period="5d")
                if not h.empty: macro[k] = float(h["Close"].iloc[-1])
            except: pass
        return macro

    def _rsi(self, s, p=14):
        if s is None or len(s)<p+1: return None
        d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=(-d).where(d<0,0).rolling(p).mean()
        rs=g/l; r=100-(100/(1+rs)); v=r.iloc[-1]; return round(float(v),1) if not pd.isna(v) else None

    def _sma(self, s, w):
        if s is None or len(s)<w: return None
        return round(float(s.rolling(w).mean().iloc[-1]),2)

    def _macd(self, s):
        if s is None or len(s)<35: return None
        e12=s.ewm(span=12).mean(); e26=s.ewm(span=26).mean(); m=e12-e26; sig=m.ewm(span=9).mean()
        return {"macd":round(float(m.iloc[-1]),4),"signal":round(float(sig.iloc[-1]),4),"histogram":round(float((m-sig).iloc[-1]),4)}

    def _vol(self, s, w=30):
        if s is None or len(s)<w: return None
        r = s.pct_change().dropna()
        return round(float(r.iloc[-w:].std()*np.sqrt(365)*100),1) if len(r)>=w else None

    # ── Layer 1 ──────────────────────────────────
    def compute_market_signals(self):
        signals = []
        fg = self.fetch_fear_greed()
        if fg and len(fg)>0:
            v=int(fg[0].get("value",50)); lbl=fg[0].get("value_classification","")
            sc = 1.0 if v<=20 else (0.5 if v<=40 else (-1.0 if v>=80 else (-0.5 if v>=60 else 0.0)))
            st = "bullish" if v<=40 else ("bearish" if v>=60 else "neutral")
            signals.append({"name":"Fear & Greed Index","layer":1,"value":v,"score":sc,"status":st,
                "detail":f"F&G {v} ({lbl})","source":"Alternative.me","frequency":"Daily"})

        bd = self.global_data.get("market_cap_percentage",{}).get("btc")
        if bd:
            sc = -0.5 if bd>60 else (0.5 if bd<45 else 0.0)
            signals.append({"name":"BTC Dominance","layer":1,"value":round(bd,1),"score":sc,
                "status":"bearish" if bd>60 else ("bullish" if bd<45 else "neutral"),
                "detail":f"BTC dom {bd:.1f}% — {'BTC season' if bd>55 else 'alt rotation' if bd<45 else 'balanced'}",
                "source":"CoinGecko","frequency":"Real-time"})

        tm = self.global_data.get("total_market_cap",{}).get("usd")
        if tm:
            signals.append({"name":"Total Market Cap","layer":1,"value":round(tm/1e9),"score":0.0,"status":"neutral",
                "detail":f"${tm/1e9:,.0f}B total crypto","source":"CoinGecko","frequency":"Real-time"})

        ss = self.fetch_stablecoin_supply()
        if ss:
            sb=ss/1e9
            signals.append({"name":"Stablecoin Supply","layer":1,"value":round(sb,1),
                "score":0.5 if sb>150 else 0.0,"status":"bullish" if sb>150 else "neutral",
                "detail":f"${sb:.0f}B stablecoins — {'significant dry powder' if sb>150 else 'moderate'}",
                "source":"DeFiLlama","frequency":"Daily"})

        macro = self.fetch_macro()
        dxy = macro.get("dxy")
        if dxy:
            sc = 0.5 if dxy<100 else (0.0 if dxy<105 else -0.5)
            signals.append({"name":"DXY (Dollar)","layer":1,"value":round(dxy,1),"score":sc,
                "status":"bullish" if dxy<100 else ("bearish" if dxy>105 else "neutral"),
                "detail":f"DXY {dxy:.1f}","source":"Yahoo Finance","frequency":"15 min"})

        t10 = macro.get("treasury_10y")
        if t10:
            sc = 0.5 if t10<3.5 else (0.0 if t10<4.5 else -0.5)
            signals.append({"name":"10Y Treasury","layer":1,"value":round(t10,2),"score":sc,
                "status":"bullish" if t10<3.5 else ("bearish" if t10>4.5 else "neutral"),
                "detail":f"10Y {t10:.2f}%","source":"Yahoo Finance","frequency":"15 min"})

        # Halving cycle
        days = (datetime.now()-datetime(2024,4,20)).days; months = days/30.44
        sc = 0.5 if months<18 else (0.0 if months<24 else -0.25)
        signals.append({"name":"Halving Cycle","layer":1,"value":round(months,1),"score":sc,
            "status":"bullish" if months<18 else "neutral",
            "detail":f"{months:.0f} months post-halving (Apr 2024). Next: ~Apr 2028.",
            "source":"Calculated","frequency":"Static"})

        return signals

    # ── Layer 2: Per-Coin ────────────────────────
    def compute_coin_signals(self, coin_id):
        mkt = self.market_data.get(coin_id,{}); series = self.price_history.get(coin_id)
        profile = self.profiles.get("profiles",{}).get(coin_id, self.profiles.get("default_profile",{}))
        price = mkt.get("current_price",0); sym = mkt.get("symbol",coin_id).upper()
        result = {"coin_id":coin_id,"symbol":sym,"name":mkt.get("name",coin_id),"price":price,
            "signals":[],"technicals":{},"changes":{},"market":{},"category":profile.get("category","unclassified"),
            "risk_tier":profile.get("risk_tier","unclassified"),"role":profile.get("role",""),
            "sell_triggers":profile.get("sell_triggers",[]),"buy_signals":profile.get("buy_signals",[]),
            "cycle_notes":profile.get("cycle_notes","")}

        result["market"] = {k:mkt.get(k) for k in ["market_cap","market_cap_rank","total_volume","ath","ath_change_percentage","ath_date","circulating_supply","total_supply"]}

        for k,f in [("1h","price_change_percentage_1h_in_currency"),("24h","price_change_percentage_24h_in_currency"),
                     ("7d","price_change_percentage_7d_in_currency"),("30d","price_change_percentage_30d_in_currency")]:
            v = mkt.get(f)
            if v is not None: result["changes"][k]=round(v,2)

        ath_pct = mkt.get("ath_change_percentage")
        if ath_pct is not None:
            result["technicals"]["pct_from_ath"]=round(ath_pct,1)
            if ath_pct<-60: result["signals"].append({"name":"% from ATH","layer":2,"value":round(ath_pct,1),"score":0.5,"status":"bullish","detail":f"{ath_pct:.0f}% from ATH — deeply discounted"})
            elif ath_pct>-10: result["signals"].append({"name":"% from ATH","layer":2,"value":round(ath_pct,1),"score":-0.5,"status":"bearish","detail":f"{ath_pct:.0f}% from ATH — near highs"})

        if series is not None and len(series)>0:
            rsi=self._rsi(series)
            if rsi: result["technicals"]["rsi"]=rsi; st="bearish" if rsi>75 else ("bullish" if rsi<30 else "neutral"); result["signals"].append({"name":"RSI","layer":2,"value":rsi,"score":-0.5 if rsi>75 else (0.5 if rsi<30 else 0.0),"status":st,"detail":f"RSI {rsi:.0f}"})

            s50=self._sma(series,50); s200=self._sma(series,200)
            if s50 and s200:
                result["technicals"]["sma50"]=s50; result["technicals"]["sma200"]=s200
                gc=s50>s200; result["technicals"]["golden_cross"]=gc
                result["signals"].append({"name":"Trend (50/200)","layer":2,"value":round(s50-s200,2),"score":0.5 if gc else -0.5,"status":"bullish" if gc else "bearish","detail":f"{'Golden' if gc else 'Death'} cross"})
                if price and s200:
                    pv=round((price-s200)/s200*100,1); result["technicals"]["pct_vs_200sma"]=pv
                    result["signals"].append({"name":"vs 200-SMA","layer":2,"value":pv,"score":0.5 if pv>0 else -1.0,"status":"bullish" if pv>0 else "bearish","detail":f"{'Above' if pv>0 else 'BELOW'} 200-SMA by {abs(pv):.1f}%"})

            macd=self._macd(series)
            if macd: result["technicals"]["macd"]=macd; result["signals"].append({"name":"MACD","layer":2,"value":macd["histogram"],"score":0.25 if macd["histogram"]>0 else -0.25,"status":"bullish" if macd["histogram"]>0 else "bearish","detail":f"MACD hist {'positive' if macd['histogram']>0 else 'negative'}"})

            vol=self._vol(series)
            if vol: result["technicals"]["volatility_ann"]=vol

        scores=[s.get("score",0) for s in result["signals"]]
        result["composite_score"]=round(sum(scores),2)
        nb=sum(1 for s in result["signals"] if s.get("status")=="bullish")
        nbe=sum(1 for s in result["signals"] if s.get("status")=="bearish")
        result["signal_summary"]={"bullish":nb,"bearish":nbe,"total":len(scores)}
        cs=result["composite_score"]
        if cs>=1.5: result["status"],result["status_color"]="ACCUMULATE","green"
        elif cs>=0: result["status"],result["status_color"]="HOLD","yellow"
        elif cs>=-1.5: result["status"],result["status_color"]="CAUTION","orange"
        else: result["status"],result["status_color"]="REDUCE","red"
        return result

    # ── Full Build ───────────────────────────────
    def build_dashboard(self):
        self.load_config(); self.fetch_global_data(); self.fetch_market_data(); self.fetch_price_history()
        holdings = self.portfolio.get("holdings",[])
        total = sum(h.get("dollars",0) for h in holdings)
        market_signals = self.compute_market_signals()
        coin_cards = {}
        for h in holdings:
            cid=h.get("coin_id","")
            if not cid: continue
            card=self.compute_coin_signals(cid)
            card["dollars"]=h.get("dollars",0); card["quantity"]=h.get("quantity"); card["notes"]=h.get("notes","")
            card["is_watchlist"]=h.get("dollars",0)==0
            if card["dollars"]>0 and card["price"]>0 and not card["quantity"]:
                card["estimated_quantity"]=round(card["dollars"]/card["price"],4)
            coin_cards[cid]=card

        ms = sum(s.get("score",0) for s in market_signals)
        if ms>=2: mst={"label":"BULLISH","color":"green","message":"Market favors accumulation."}
        elif ms>=0: mst={"label":"MIXED","color":"yellow","message":"Selective positioning."}
        elif ms>=-2: mst={"label":"CAUTIOUS","color":"orange","message":"Headwinds. Tighten risk."}
        else: mst={"label":"BEARISH","color":"red","message":"Multiple bearish signals. Reduce exposure."}

        sug = load_json(SUGGESTIONS_FILE) if os.path.exists(SUGGESTIONS_FILE) else {}
        state={"timestamp":datetime.now().isoformat(),"portfolio_summary":{"total_invested":total,"exchange":self.portfolio.get("exchange","")},
            "market_health":{"score":round(ms,2),"status":mst,"signals":market_signals},"coin_cards":coin_cards,"suggestions":sug}
        save_json(STATE_FILE, state)
        try:
            hist = load_json(HISTORY_FILE) if os.path.exists(HISTORY_FILE) else []
            if not isinstance(hist,list): hist=[]
            hist.append({"timestamp":state["timestamp"],"market_score":ms,
                "btc":coin_cards.get("bitcoin",{}).get("price"),"eth":coin_cards.get("ethereum",{}).get("price"),
                "sol":coin_cards.get("solana",{}).get("price")})
            save_json(HISTORY_FILE, hist[-500:])
        except: pass
        return state

def run_crypto_update():
    return CryptoSignalEngine().build_dashboard()

if __name__=="__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    state=run_crypto_update()
    print(f"\nMarket: {state['market_health']['status']['label']} ({state['market_health']['score']})")
    for cid,card in sorted(state["coin_cards"].items()):
        tag="💰" if not card.get("is_watchlist") else "👀"
        print(f"  {tag} {card['symbol']:5} ${card['price']:>10,.2f} | {card['status']:10} | score: {card['composite_score']:+.1f}")
