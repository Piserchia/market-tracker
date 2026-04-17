import { useState, useEffect, useCallback } from "react";
const API = "http://localhost:8789";

const INFO = {
  "Fear & Greed Index": "Sentiment indicator (0-100) from Alternative.me. Below 20 = extreme fear (historically best buying opportunity). 20-40 = fear. 40-60 = neutral. 60-80 = greed. Above 80 = extreme greed (often marks local tops). Contrarian — buy when others fear.",
  "BTC Dominance": "Bitcoin's share of total crypto market cap. Above 60% = BTC Season (capital consolidating in BTC). Below 45% = Alt Season (capital rotating into ETH/SOL/alts). Currently ~58% — BTC Season.",
  "Total Market Cap": "Total value of all cryptocurrencies. Rising = capital flowing in. Falling = capital leaving. Current ~$2.5T vs 2021 peak of ~$3T.",
  "Stablecoin Supply": "Total USDT + USDC + stablecoins circulating. Called 'dry powder' — capital parked waiting to buy. Rising = bullish (more buyers). Falling = capital exiting.",
  "DXY (Dollar)": "US Dollar Index. Strong INVERSE correlation with crypto. DXY <100 = weak dollar = bullish crypto. Above 105 = headwind. Single most important macro signal for crypto.",
  "10Y Treasury": "10-year Treasury yield. Higher rates compress risk asset valuations. Above 4.5% = crypto pressure. Below 3.5% = tailwind. Crypto rallies typically align with rate cut expectations.",
  "Halving Cycle": "Months since April 2024 BTC halving. Historical pattern: BTC tops 12-18 months post-halving (Oct 2025 ATH fit). Past 24 months = cooling phase. Next halving ~April 2028.",
  "% from ATH": "Current price as % below all-time high. -60% or more = deeply discounted. Less than -10% = near highs. BTC ~42% from ATH, ETH ~59%, SOL ~68%.",
  "RSI": "Relative Strength Index (14-day). Momentum gauge 0-100. >75 = overbought. <30 = oversold. Crypto can stay >80 in strong rallies longer than stocks.",
  "200-SMA": "200-day Simple Moving Average. Above = bull territory. Below = bear territory. Most important indicator for cycle positioning.",
  "vs 200-SMA": "% distance from 200-day SMA. Above = uptrend. Below = downtrend. More than 30% below often marks bear market bottoms.",
  "Golden/Death Cross": "50-SMA crossing above 200-SMA = Golden Cross (bullish). Crossing below = Death Cross (bearish). Major trend-change signals.",
  "Vol": "Annualized volatility (30-day). Context: S&P 500 ~15-20%, BTC ~40-70%, ETH ~60-90%, SOL ~80-120%. Higher vol = bigger moves both ways.",
  "MCap": "Market cap = price × circulating supply. Total coin value. BTC dwarfs others at ~$1.5T.",
  "Rank": "Market cap rank across all cryptocurrencies. BTC #1, ETH #2, SOL ~#5-7. Rank changes signal capital rotation.",
  "Composite Score": "Sum of all indicator scores. +1.5+ = ACCUMULATE. 0 to +1.5 = HOLD. -1.5 to 0 = CAUTION. Below -1.5 = REDUCE.",
  "Market Score": "Sum of Layer 1 market health signals. Positive = constructive conditions. Negative = headwinds.",
  "core": "BTC/ETH — lowest relative risk, institutional anchors",
  "growth": "SOL/AVAX — high-performance L1s, higher volatility",
  "moderate": "LINK/XRP — infrastructure or utility plays",
  "speculative": "Smaller caps — size small, higher risk/reward",
  "MVRV Z-Score": "Bitcoin's most reliable valuation indicator. Market value vs realized value (average cost basis). Above 7 = cycle top. Below 0 = cycle bottom. Calls tops within 2 weeks historically.",
  "NUPL": "Net Unrealized Profit/Loss. Whether network as a whole is in profit or capitulation. Above 0.75 = Euphoria. Below 0 = Capitulation (best buying historically).",
  "Puell Multiple": "Bitcoin miner revenue vs 365-day avg. Above 4 = overvalued. Below 0.5 = miner capitulation = undervalued.",
};

const DEMO={timestamp:new Date().toISOString(),portfolio_summary:{total_invested:16300,exchange:"Coinbase"},market_health:{score:1.5,status:{label:"MIXED",color:"yellow",message:"Selective positioning — constructive setup with macro crosscurrents."},signals:[{name:"Fear & Greed Index",layer:1,value:34,score:0.5,status:"bullish",detail:"F&G 34 (Fear) — contrarian bullish"},{name:"BTC Dominance",layer:1,value:58.5,score:0.0,status:"neutral",detail:"BTC dom 58.5% — BTC season"},{name:"Total Market Cap",layer:1,value:2530,score:0.0,status:"neutral",detail:"$2,530B total"},{name:"Stablecoin Supply",layer:1,value:168,score:0.5,status:"bullish",detail:"$168B dry powder"},{name:"DXY (Dollar)",layer:1,value:99.8,score:0.5,status:"bullish",detail:"DXY 99.8 — weak dollar"},{name:"10Y Treasury",layer:1,value:4.29,score:0.0,status:"neutral",detail:"10Y 4.29%"},{name:"Halving Cycle",layer:1,value:24,score:0.0,status:"neutral",detail:"24 months post-halving — late cycle"}]},coin_cards:{solana:{coin_id:"solana",symbol:"SOL",name:"Solana",price:85.02,dollars:16300,is_watchlist:false,estimated_quantity:191.7,status:"CAUTION",status_color:"orange",composite_score:-0.5,risk_tier:"growth",signal_summary:{bullish:2,bearish:3,total:6},market:{market_cap:45920000000,market_cap_rank:7,ath:265,ath_change_percentage:-67.9,total_volume:3200000000},technicals:{rsi:38,pct_from_ath:-67.9,sma200:142,pct_vs_200sma:-40.1,volatility_ann:95,golden_cross:false},changes:{"24h":2.1,"7d":5.7,"30d":-6.4},role:"High-performance app platform. Your current holding.",sell_triggers:["Major network outage","DeFi exploit >$100M","ETF denied"],buy_signals:["SOL ETF approved","Alpenglow 150ms finality","Reclaims $100"],cycle_notes:"Down 68% from Jan 2026 highs. SEC commodity classification. 7+ ETF filings active.",signals:[{name:"% from ATH",layer:2,value:-67.9,score:0.5,status:"bullish",detail:"-68% from ATH — deeply discounted"},{name:"vs 200-SMA",layer:2,value:-40.1,score:-1.0,status:"bearish",detail:"BELOW 200-SMA by 40.1%"}]},bitcoin:{coin_id:"bitcoin",symbol:"BTC",name:"Bitcoin",price:73714,dollars:0,is_watchlist:true,status:"HOLD",status_color:"yellow",risk_tier:"core",composite_score:0.25,signal_summary:{bullish:2,bearish:2,total:5},market:{market_cap:1460000000000,market_cap_rank:1,ath:126198,ath_change_percentage:-41.6},technicals:{rsi:48,pct_from_ath:-41.6,pct_vs_200sma:-8.2,volatility_ann:45},changes:{"24h":0.9,"7d":4.2,"30d":-3.1},role:"Digital gold. Store of value. Institutional anchor.",sell_triggers:["MVRV Z-Score >7","ETF outflows >$1B for 5 days"],buy_signals:["MVRV Z-Score <0","Reclaims STH cost basis"],signals:[]},ethereum:{coin_id:"ethereum",symbol:"ETH",name:"Ethereum",price:2050,dollars:0,is_watchlist:true,status:"CAUTION",status_color:"orange",risk_tier:"core",composite_score:-0.75,signal_summary:{bullish:1,bearish:3,total:5},market:{market_cap:247000000000,market_cap_rank:2,ath:4954,ath_change_percentage:-58.6},technicals:{rsi:35,pct_from_ath:-58.6,pct_vs_200sma:-32.5,volatility_ann:65},changes:{"24h":1.6,"7d":6.1,"30d":-8.2},role:"DeFi settlement layer. Staking yield ~3-4%.",signals:[]}},suggestions:{}};

const fmt=(n,d=2)=>n!=null?Number(n).toFixed(d):"—";
const fP=n=>n!=null?(n>=0?"+":"")+Number(n).toFixed(1)+"%":"—";
const f$=n=>n!=null?(n>=1000?"$"+Number(n).toLocaleString(undefined,{maximumFractionDigits:n>=10000?0:2}):"$"+fmt(n)):"—";
const fQ=n=>n!=null?(n>=1?fmt(n,2):fmt(n,4)):"—";
const TIER_C={core:"#00e676",growth:"#648cff",moderate:"#ffd600",speculative:"#ff9100"};
const STATUS_C={ACCUMULATE:{c:"#00e676",i:"🟢"},HOLD:{c:"#ffd600",i:"🟡"},CAUTION:{c:"#ff9100",i:"🟠"},REDUCE:{c:"#ff1744",i:"🔴"}};

function Info({keyName,short=false}){
  const[show,setShow]=useState(false);
  const text=INFO[keyName];if(!text)return null;
  return(<span style={{position:"relative",display:"inline-block",marginLeft:"4px"}}
    onMouseEnter={()=>setShow(true)} onMouseLeave={()=>setShow(false)}>
    <span style={{fontSize:short?"8px":"9px",color:"#555",border:"1px solid #333",borderRadius:"50%",width:short?"12px":"13px",height:short?"12px":"13px",display:"inline-flex",alignItems:"center",justifyContent:"center",cursor:"help",fontFamily:"monospace",lineHeight:1}}>i</span>
    {show&&<div style={{position:"absolute",bottom:"100%",left:"50%",transform:"translateX(-50%)",marginBottom:"6px",background:"#161b22",border:"1px solid #30363d",color:"#c8ccd4",padding:"8px 10px",borderRadius:"6px",fontSize:"11px",lineHeight:1.5,width:"300px",zIndex:100,boxShadow:"0 4px 12px rgba(0,0,0,0.5)",textAlign:"left",fontFamily:"-apple-system,sans-serif",fontWeight:400}}>{text}</div>}
  </span>);
}

function AddCoinForm({onAdd}){
  const[id,setId]=useState("");const[sym,setSym]=useState("");const[d,setD]=useState("");const[loading,setL]=useState(false);
  const submit=async()=>{if(!id)return;setL(true);try{
    const r=await fetch(`${API}/api/crypto/portfolio`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({coin_id:id.toLowerCase(),symbol:sym.toUpperCase()||id.toUpperCase(),dollars:Number(d)||0,analyze:true})});
    const j=await r.json();if(j.analysis_triggered)alert(`${sym||id} added! Claude analyzing...`);setId("");setSym("");setD("");if(onAdd)onAdd();
  }catch(e){alert("Failed: "+e.message)}finally{setL(false)}};
  return(<div style={{background:"#0d1117",borderRadius:"8px",border:"1px solid #1a1f2e",padding:"16px",marginBottom:"16px"}}>
    <div style={{fontSize:"10px",color:"#555",textTransform:"uppercase",letterSpacing:"1.5px",marginBottom:"10px",fontFamily:"monospace"}}>Add Coin / Update Position</div>
    <div style={{display:"flex",gap:"8px",flexWrap:"wrap",alignItems:"flex-end"}}>
      <div><div style={{fontSize:"9px",color:"#444",marginBottom:"4px"}}>COINGECKO ID</div><input value={id} onChange={e=>setId(e.target.value)} placeholder="chainlink" style={{background:"#161b22",border:"1px solid #30363d",color:"#e1e4e8",padding:"8px 12px",borderRadius:"6px",width:"120px",fontFamily:"monospace",fontSize:"13px"}}/></div>
      <div><div style={{fontSize:"9px",color:"#444",marginBottom:"4px"}}>SYMBOL</div><input value={sym} onChange={e=>setSym(e.target.value)} placeholder="LINK" style={{background:"#161b22",border:"1px solid #30363d",color:"#e1e4e8",padding:"8px 12px",borderRadius:"6px",width:"70px",fontFamily:"monospace",fontSize:"13px"}}/></div>
      <div><div style={{fontSize:"9px",color:"#444",marginBottom:"4px"}}>DOLLARS (0 = watchlist)</div><input value={d} onChange={e=>setD(e.target.value)} placeholder="0" type="number" style={{background:"#161b22",border:"1px solid #30363d",color:"#e1e4e8",padding:"8px 12px",borderRadius:"6px",width:"100px",fontFamily:"monospace",fontSize:"13px"}}/></div>
      <button onClick={submit} disabled={loading||!id} style={{background:loading?"#333":"#238636",border:"none",color:"#fff",padding:"8px 20px",borderRadius:"6px",cursor:loading?"wait":"pointer",fontSize:"13px",fontWeight:600}}>{loading?"Analyzing...":"Add Coin"}</button>
    </div>
    <div style={{fontSize:"9px",color:"#333",marginTop:"6px"}}>CoinGecko ID = lowercase slug from coingecko.com URL. Set dollars to 0 for watchlist.</div>
  </div>);
}

function CoinCard({card}){
  const[expanded,setE]=useState(false);
  const sc=STATUS_C[card.status]||STATUS_C.HOLD;
  const tierColor=TIER_C[card.risk_tier]||"#555";
  const isWL=card.is_watchlist||card.dollars===0;
  return(<div style={{background:isWL?"#080b12":"#0d1117",border:`1px solid ${isWL?"#12151e":"#1a1f2e"}`,borderLeft:`3px solid ${isWL?"#333":sc.c}`,borderRadius:"8px",padding:"14px",marginBottom:"8px",cursor:"pointer",opacity:isWL?0.75:1}} onClick={()=>setE(!expanded)}>
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
      <div style={{display:"flex",alignItems:"center",gap:"10px"}}>
        <span style={{fontSize:"18px",fontWeight:700,color:"#e1e4e8",fontFamily:"'Space Grotesk'"}}>{card.symbol}</span>
        <span style={{fontSize:"11px",color:"#8a8f98"}}>{card.name}</span>
        {isWL&&<span style={{fontSize:"9px",color:"#555",padding:"2px 6px",borderRadius:"3px",border:"1px solid #222",fontFamily:"monospace"}}>WATCHLIST</span>}
        {!isWL&&<>
          <span style={{fontSize:"9px",color:tierColor,padding:"2px 6px",borderRadius:"3px",background:`${tierColor}15`,fontFamily:"monospace"}}>{card.risk_tier}</span>
          <Info keyName={card.risk_tier} short/>
        </>}
      </div>
      <div style={{display:"flex",alignItems:"center",gap:"12px"}}>
        <span style={{fontSize:"16px",fontWeight:600,color:"#e1e4e8",fontFamily:"monospace"}}>{f$(card.price)}</span>
        {!isWL&&<span style={{fontSize:"12px",fontWeight:700,color:sc.c,padding:"2px 8px",borderRadius:"4px",background:`${sc.c}15`,fontFamily:"monospace"}}>{sc.i} {card.status}</span>}
        <span style={{display:"flex",alignItems:"center"}}>
          <span style={{fontSize:"13px",fontWeight:700,color:card.composite_score>=0?"#00e676":"#ff1744",fontFamily:"'JetBrains Mono'"}}>{card.composite_score>=0?"+":""}{fmt(card.composite_score,1)}</span>
          <Info keyName="Composite Score" short/>
        </span>
      </div>
    </div>

    <div style={{display:"flex",gap:"16px",marginTop:"8px",fontSize:"11px",fontFamily:"monospace",flexWrap:"wrap"}}>
      {!isWL&&<><span style={{color:"#555"}}>Position: <span style={{color:"#e1e4e8"}}>{f$(card.dollars)}</span></span>
        {card.estimated_quantity&&<span style={{color:"#555"}}>Qty: <span style={{color:"#e1e4e8"}}>{fQ(card.estimated_quantity)} {card.symbol}</span></span>}</>}
      {card.market?.market_cap&&<span style={{color:"#555",display:"inline-flex",alignItems:"center"}}>MCap<Info keyName="MCap" short/>: <span style={{color:"#8a8f98",marginLeft:"4px"}}>{f$(card.market.market_cap/1e9)}B</span></span>}
      {card.market?.market_cap_rank&&<span style={{color:"#555",display:"inline-flex",alignItems:"center"}}>Rank<Info keyName="Rank" short/>: <span style={{color:"#8a8f98",marginLeft:"4px"}}>#{card.market.market_cap_rank}</span></span>}
      {card.technicals?.pct_from_ath!=null&&<span style={{color:card.technicals.pct_from_ath>-20?"#ff9100":"#8a8f98",display:"inline-flex",alignItems:"center"}}>{card.technicals.pct_from_ath.toFixed(0)}% from ATH<Info keyName="% from ATH" short/></span>}
      {card.changes&&Object.entries(card.changes).map(([k,v])=><span key={k} style={{color:v>=0?"#00e676":"#ff1744"}}>{k}: {fP(v)}</span>)}
    </div>

    {card.role&&<div style={{fontSize:"10px",color:"#444",marginTop:"6px",fontStyle:"italic"}}>{card.role}</div>}

    {expanded&&<div style={{marginTop:"12px",paddingTop:"12px",borderTop:"1px solid #1a1f2e"}}>
      {card.technicals&&<div style={{display:"flex",gap:"16px",flexWrap:"wrap",marginBottom:"10px",fontSize:"11px",fontFamily:"monospace"}}>
        {card.technicals.rsi!=null&&<span style={{color:"#555",display:"inline-flex",alignItems:"center"}}>RSI<Info keyName="RSI" short/>: <span style={{color:card.technicals.rsi>75?"#ff1744":card.technicals.rsi<30?"#00e676":"#e1e4e8",marginLeft:"4px"}}>{card.technicals.rsi}</span></span>}
        {card.technicals.sma200&&<span style={{color:"#555",display:"inline-flex",alignItems:"center"}}>200-SMA<Info keyName="200-SMA" short/>: <span style={{color:"#8a8f98",marginLeft:"4px"}}>{f$(card.technicals.sma200)}</span></span>}
        {card.technicals.pct_vs_200sma!=null&&<span style={{color:card.technicals.pct_vs_200sma>0?"#00e676":"#ff1744",display:"inline-flex",alignItems:"center"}}>{card.technicals.pct_vs_200sma>0?"+":""}{card.technicals.pct_vs_200sma}% vs 200-SMA<Info keyName="vs 200-SMA" short/></span>}
        {card.technicals.golden_cross!=null&&<span style={{color:card.technicals.golden_cross?"#00e676":"#ff1744",display:"inline-flex",alignItems:"center"}}>{card.technicals.golden_cross?"Golden Cross":"Death Cross"}<Info keyName="Golden/Death Cross" short/></span>}
        {card.technicals.volatility_ann&&<span style={{color:"#555",display:"inline-flex",alignItems:"center"}}>Vol<Info keyName="Vol" short/>: <span style={{color:card.technicals.volatility_ann>100?"#ff9100":"#8a8f98",marginLeft:"4px"}}>{card.technicals.volatility_ann}% ann</span></span>}
      </div>}

      {card.signals?.map((s,i)=>{const c=s.status==="bullish"?"#00e676":s.status==="bearish"?"#ff1744":"#ffd600";return(
        <div key={i} style={{display:"flex",justifyContent:"space-between",padding:"4px 0",borderBottom:"1px solid #0a0e16",fontSize:"11px"}}>
          <span style={{color:"#8a8f98"}}>{s.name}</span><span style={{color:c,fontFamily:"monospace"}}>{s.detail}</span></div>)})}

      {card.sell_triggers?.length>0&&<div style={{marginTop:"10px"}}><div style={{fontSize:"9px",color:"#ff1744",textTransform:"uppercase",letterSpacing:"1px",marginBottom:"4px"}}>Sell Triggers</div>
        {card.sell_triggers.map((t,i)=><div key={i} style={{fontSize:"10px",color:"#555",padding:"2px 0"}}>• {t}</div>)}</div>}
      {card.buy_signals?.length>0&&<div style={{marginTop:"6px"}}><div style={{fontSize:"9px",color:"#00e676",textTransform:"uppercase",letterSpacing:"1px",marginBottom:"4px"}}>Buy Signals</div>
        {card.buy_signals.map((t,i)=><div key={i} style={{fontSize:"10px",color:"#555",padding:"2px 0"}}>• {t}</div>)}</div>}
      {card.cycle_notes&&<div style={{fontSize:"10px",color:"#444",marginTop:"8px",padding:"8px",background:"rgba(100,140,255,0.04)",borderRadius:"4px",borderLeft:"2px solid #648cff"}}>{card.cycle_notes}</div>}
    </div>}
  </div>);
}

export default function CryptoDashboard(){
  const[state,setState]=useState(DEMO);const[suggestions,setSuggestions]=useState(null);
  const[loading,setLoading]=useState(false);const[live,setLive]=useState(false);

  const fetchData=useCallback(async()=>{try{setLoading(true);
    const[sr,sugr]=await Promise.all([fetch(`${API}/api/crypto/state`).catch(()=>null),fetch(`${API}/api/crypto/suggestions`).catch(()=>null)]);
    if(sr?.ok){const d=await sr.json();if(!d.error){setState(d);setLive(true);}}
    if(sugr?.ok){const d=await sugr.json();if(!d.error&&!d.message)setSuggestions(d);}
  }catch{}finally{setLoading(false)}},[]);

  useEffect(()=>{fetchData();const i=setInterval(fetchData,60000);return()=>clearInterval(i);},[fetchData]);

  const s=state;const mh=s.market_health||{};const ms=mh.status||{};
  const cards=Object.values(s.coin_cards||{});
  const held=cards.filter(c=>!c.is_watchlist).sort((a,b)=>(b.dollars||0)-(a.dollars||0));
  const watchlist=cards.filter(c=>c.is_watchlist);
  const refresh=async()=>{try{await fetch(`${API}/api/crypto/refresh`,{method:"POST"});setTimeout(fetchData,8000)}catch{}};
  const research=async()=>{try{await fetch(`${API}/api/crypto/research`,{method:"POST"});alert("Crypto research started.")}catch(e){alert(e.message)}};

  return(<div style={{minHeight:"100vh",background:"#080b12",color:"#e1e4e8",fontFamily:"'Instrument Sans',-apple-system,sans-serif"}}>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;600;700&family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet"/>

    <div style={{background:"#0d1117",borderBottom:`2px solid ${ms.color||"#333"}30`,padding:"12px 24px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
      <div style={{display:"flex",alignItems:"center",gap:"16px"}}>
        <span style={{fontSize:"16px",fontWeight:700,fontFamily:"'Space Grotesk'"}}>
          <span style={{color:"#f7931a"}}>₿</span> CRYPTO DASHBOARD</span>
        <span style={{fontSize:"10px",padding:"3px 8px",borderRadius:"4px",background:live?"rgba(0,230,118,0.1)":"rgba(255,214,0,0.1)",color:live?"#00e676":"#ffd600",fontFamily:"monospace"}}>{live?"● LIVE":"◌ DEMO"}</span>
      </div>
      <div style={{display:"flex",gap:"8px"}}>
        <button onClick={research} style={{background:"rgba(247,147,26,0.1)",border:"1px solid rgba(247,147,26,0.3)",color:"#f7931a",padding:"6px 12px",borderRadius:"6px",cursor:"pointer",fontSize:"11px",fontFamily:"monospace"}}>🔬 Research</button>
        <button onClick={refresh} disabled={loading} style={{background:"rgba(255,255,255,0.06)",border:"1px solid #1a1f2e",color:"#8a8f98",padding:"6px 12px",borderRadius:"6px",cursor:loading?"wait":"pointer",fontSize:"11px",fontFamily:"monospace"}}>{loading?"⟳ ...":"⟳ Refresh"}</button>
      </div>
    </div>

    <div style={{maxWidth:"1400px",margin:"0 auto",padding:"24px"}}>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"16px",marginBottom:"24px"}}>
        <div style={{background:"#0d1117",borderRadius:"8px",border:"1px solid #1a1f2e",padding:"20px"}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"12px"}}>
            <span style={{fontSize:"11px",color:"#555",textTransform:"uppercase",letterSpacing:"2px",fontFamily:"monospace",display:"flex",alignItems:"center"}}>Market Health<Info keyName="Market Score"/></span>
            <span style={{fontSize:"20px",fontWeight:700,color:ms.color||"#555",fontFamily:"'JetBrains Mono'"}}>{mh.score>=0?"+":""}{fmt(mh.score||0,1)}</span>
          </div>
          <div style={{padding:"8px 12px",borderRadius:"6px",background:`${ms.color||"#555"}10`,border:`1px solid ${ms.color||"#555"}25`,fontSize:"13px",color:ms.color,fontWeight:500,marginBottom:"12px"}}>{ms.message||""}</div>
          {mh.signals?.map((sig,i)=>{const c=sig.status==="bullish"?"#00e676":sig.status==="bearish"?"#ff1744":"#ffd600";return(
            <div key={i} style={{display:"flex",justifyContent:"space-between",padding:"5px 0",borderBottom:"1px solid #1a1f2e",fontSize:"11px"}}>
              <span style={{color:"#8a8f98",display:"flex",alignItems:"center"}}>{sig.name}<Info keyName={sig.name} short/></span>
              <span style={{color:c,fontFamily:"monospace"}}>{typeof sig.value==="number"?(sig.value>100?sig.value.toLocaleString():sig.value):""} — {sig.status}</span>
            </div>)})}
        </div>

        <div style={{background:"#0d1117",borderRadius:"8px",border:"1px solid #1a1f2e",padding:"20px"}}>
          <div style={{fontSize:"11px",color:"#555",textTransform:"uppercase",letterSpacing:"2px",fontFamily:"monospace",marginBottom:"12px"}}>Crypto Portfolio</div>
          <div style={{fontSize:"28px",fontWeight:700,color:"#e1e4e8",fontFamily:"'Space Grotesk'",marginBottom:"4px"}}>{f$(s.portfolio_summary?.total_invested||0)}</div>
          <div style={{fontSize:"11px",color:"#555",marginBottom:"16px"}}>on {s.portfolio_summary?.exchange||"Exchange"}</div>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:"8px"}}>
            {["bitcoin","ethereum","solana"].map(cid=>{const c=s.coin_cards?.[cid];if(!c)return null;return(
              <div key={cid} style={{background:"#161b22",borderRadius:"6px",padding:"10px",textAlign:"center"}}>
                <div style={{fontSize:"12px",fontWeight:700,color:"#e1e4e8"}}>{c.symbol}</div>
                <div style={{fontSize:"16px",fontWeight:600,color:"#e1e4e8",fontFamily:"monospace"}}>{f$(c.price)}</div>
                <div style={{fontSize:"11px",color:(c.changes?.["24h"]||0)>=0?"#00e676":"#ff1744",fontFamily:"monospace"}}>{fP(c.changes?.["24h"])}</div>
              </div>)})}
          </div>
        </div>
      </div>

      <AddCoinForm onAdd={fetchData}/>

      <div style={{display:"grid",gridTemplateColumns:"1fr 360px",gap:"24px"}}>
        <div>
          {held.length>0&&<>
            <div style={{fontSize:"11px",color:"#555",textTransform:"uppercase",letterSpacing:"2px",fontFamily:"monospace",marginBottom:"10px"}}>Holdings ({held.length})</div>
            {held.map((c,i)=><CoinCard key={i} card={c}/>)}</>}
          {watchlist.length>0&&<>
            <div style={{fontSize:"11px",color:"#555",textTransform:"uppercase",letterSpacing:"2px",fontFamily:"monospace",marginBottom:"10px",marginTop:"24px"}}>Watchlist ({watchlist.length})</div>
            {watchlist.map((c,i)=><CoinCard key={i} card={c}/>)}</>}
        </div>

        <div>
          {suggestions&&<>
            {suggestions.market_summary&&<div style={{background:"#0d1117",borderRadius:"8px",border:"1px solid #1a1f2e",padding:"16px",marginBottom:"16px"}}>
              <div style={{fontSize:"10px",color:"#555",textTransform:"uppercase",letterSpacing:"1.5px",marginBottom:"8px",fontFamily:"monospace"}}>Claude's Crypto Research</div>
              <div style={{fontSize:"12px",color:"#c8ccd4",lineHeight:1.6,marginBottom:"8px"}}>{suggestions.market_summary}</div>
              {suggestions.on_chain_highlights&&<div style={{fontSize:"11px",color:"#8a8f98",lineHeight:1.5,padding:"8px",background:"rgba(247,147,26,0.04)",borderRadius:"4px",borderLeft:"2px solid #f7931a",marginBottom:"8px"}}>{suggestions.on_chain_highlights}</div>}
              {suggestions.btc_cycle_assessment&&<div style={{fontSize:"11px",color:"#648cff",marginBottom:"6px"}}>Cycle: {suggestions.btc_cycle_assessment}</div>}
              <div style={{fontSize:"11px",color:suggestions.sector_sentiment==="bullish"?"#00e676":suggestions.sector_sentiment==="bearish"?"#ff1744":"#ffd600",fontWeight:600}}>{suggestions.sector_sentiment?.toUpperCase()}</div>
            </div>}
            {suggestions.new_suggestions?.length>0&&<div style={{marginBottom:"16px"}}>
              <div style={{fontSize:"10px",color:"#648cff",textTransform:"uppercase",letterSpacing:"1.5px",marginBottom:"8px",fontFamily:"monospace"}}>New Coin Ideas</div>
              {suggestions.new_suggestions.map((sg,i)=><div key={i} style={{background:"#0d1117",border:"1px solid #1a1f2e",borderLeft:"3px solid #648cff",borderRadius:"8px",padding:"12px",marginBottom:"6px"}}>
                <div style={{fontSize:"13px",fontWeight:700,color:"#e1e4e8",fontFamily:"monospace"}}>{sg.symbol} <span style={{fontWeight:400,fontSize:"11px",color:"#8a8f98"}}>{sg.name}</span></div>
                <div style={{fontSize:"11px",color:"#8a8f98",marginTop:"4px"}}>{sg.why_now}</div>
                {sg.suggested_allocation_usd&&<div style={{fontSize:"10px",color:"#648cff",marginTop:"4px"}}>Suggested: {f$(sg.suggested_allocation_usd)}</div>}
              </div>)}</div>}
            {suggestions.risks_to_watch?.length>0&&<div style={{background:"#0d1117",borderRadius:"8px",border:"1px solid #1a1f2e",padding:"16px"}}>
              <div style={{fontSize:"10px",color:"#ff9100",textTransform:"uppercase",letterSpacing:"1.5px",marginBottom:"8px",fontFamily:"monospace"}}>Risks to Watch</div>
              {suggestions.risks_to_watch.map((r,i)=><div key={i} style={{fontSize:"11px",color:"#8a8f98",padding:"4px 0",borderBottom:"1px solid #0a0e16"}}>⚠️ {typeof r==="string"?r:r.risk||r.description||JSON.stringify(r)}</div>)}
            </div>}
          </>}

          {!suggestions&&<div style={{background:"#0d1117",borderRadius:"8px",border:"1px solid #1a1f2e",padding:"24px",textAlign:"center"}}>
            <div style={{fontSize:"11px",color:"#555",marginBottom:"12px"}}>No crypto research yet</div>
            <button onClick={research} style={{background:"rgba(247,147,26,0.1)",border:"1px solid rgba(247,147,26,0.3)",color:"#f7931a",padding:"8px 16px",borderRadius:"6px",cursor:"pointer",fontSize:"12px"}}>Run Research</button>
          </div>}

          <div style={{background:"#0d1117",borderRadius:"8px",border:"1px solid #1a1f2e",padding:"16px",marginTop:"16px"}}>
            <div style={{fontSize:"10px",color:"#555",textTransform:"uppercase",letterSpacing:"1.5px",marginBottom:"8px",fontFamily:"monospace",display:"flex",alignItems:"center"}}>On-Chain Indicators<Info keyName="MVRV Z-Score"/></div>
            <div style={{fontSize:"11px",color:"#444",lineHeight:1.6}}>
              MVRV Z-Score, NUPL, Puell Multiple require premium APIs. Check these manually:
            </div>
            <div style={{marginTop:"8px",display:"flex",flexDirection:"column",gap:"4px"}}>
              {[["MVRV Z-Score","bitcoinmagazinepro.com/charts/mvrv-zscore"],["NUPL","lookintobitcoin.com"],["Puell Multiple","bitcoinmagazinepro.com/charts/puell-multiple"],["Fear & Greed","alternative.me/crypto/fear-and-greed-index"]].map(([name,url])=>(
                <div key={name} style={{fontSize:"10px",display:"flex",alignItems:"center"}}><span style={{color:"#8a8f98"}}>{name}<Info keyName={name} short/>: </span><span style={{color:"#648cff",marginLeft:"4px"}}>{url}</span></div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div style={{marginTop:"32px",fontSize:"10px",color:"#333",fontFamily:"monospace",display:"flex",justifyContent:"space-between"}}>
        <span>Crypto Dashboard v1.1 — Hover (i) icons for explanations — Not financial advice</span>
        <span>Data: CoinGecko + DeFiLlama | {cards.length} coins tracked</span>
      </div>
    </div>
  </div>);
}
