import { useState, useEffect, useCallback } from "react";
const API = "http://localhost:8789";

const DEMO={timestamp:new Date().toISOString(),portfolio_summary:{total_invested:16300,exchange:"Coinbase"},market_health:{score:1.5,status:{label:"MIXED",color:"yellow",message:"Selective positioning."},signals:[{name:"Fear & Greed Index",layer:1,value:34,score:0.5,status:"bullish",detail:"F&G 34 (Fear) — contrarian bullish"},{name:"BTC Dominance",layer:1,value:58.5,score:0.0,status:"neutral",detail:"BTC dom 58.5% — BTC season"},{name:"Total Market Cap",layer:1,value:2530,score:0.0,status:"neutral",detail:"$2,530B total"},{name:"Stablecoin Supply",layer:1,value:168,score:0.5,status:"bullish",detail:"$168B dry powder"},{name:"DXY",layer:1,value:99.8,score:0.5,status:"bullish",detail:"DXY 99.8 — weak dollar"},{name:"10Y Treasury",layer:1,value:4.29,score:0.0,status:"neutral",detail:"10Y 4.29%"},{name:"Halving Cycle",layer:1,value:24,score:0.0,status:"neutral",detail:"24 months post-halving — late cycle"}]},coin_cards:{solana:{coin_id:"solana",symbol:"SOL",name:"Solana",price:85.02,dollars:16300,is_watchlist:false,estimated_quantity:191.7,status:"CAUTION",status_color:"orange",composite_score:-0.5,signal_summary:{bullish:2,bearish:3,total:6},market:{market_cap:45920000000,market_cap_rank:7,ath:265,ath_change_percentage:-67.9,total_volume:3200000000},technicals:{rsi:38,pct_from_ath:-67.9,sma200:142,pct_vs_200sma:-40.1,volatility_ann:95},changes:{"24h":2.1,"7d":5.7,"30d":-6.4},role:"High-performance app platform. Your current holding ($16.3K).",sell_triggers:["Major network outage","DeFi exploit >$100M","ETF denied"],buy_signals:["SOL ETF approved","Alpenglow 150ms finality","Reclaims $100"],signals:[{name:"% from ATH",layer:2,value:-67.9,score:0.5,status:"bullish",detail:"-68% from ATH — deeply discounted"},{name:"RSI",layer:2,value:38,score:0.0,status:"neutral",detail:"RSI 38"},{name:"vs 200-SMA",layer:2,value:-40.1,score:-1.0,status:"bearish",detail:"BELOW 200-SMA by 40.1%"},{name:"Trend (50/200)",layer:2,value:-22,score:-0.5,status:"bearish",detail:"Death cross"},{name:"MACD",layer:2,value:-2.1,score:-0.25,status:"bearish",detail:"MACD negative"}]},bitcoin:{coin_id:"bitcoin",symbol:"BTC",name:"Bitcoin",price:73714,dollars:0,is_watchlist:true,status:"HOLD",status_color:"yellow",composite_score:0.25,signal_summary:{bullish:2,bearish:2,total:5},market:{market_cap:1460000000000,market_cap_rank:1,ath:126198,ath_change_percentage:-41.6},technicals:{rsi:48,pct_from_ath:-41.6,pct_vs_200sma:-8.2},changes:{"24h":0.9,"7d":4.2,"30d":-3.1},role:"Digital gold. Store of value. Institutional anchor.",sell_triggers:["MVRV Z-Score >7","ETF outflows >$1B for 5 days"],buy_signals:["MVRV Z-Score <0","Reclaims STH cost basis"],signals:[]},ethereum:{coin_id:"ethereum",symbol:"ETH",name:"Ethereum",price:2050,dollars:0,is_watchlist:true,status:"CAUTION",status_color:"orange",composite_score:-0.75,signal_summary:{bullish:1,bearish:3,total:5},market:{market_cap:247000000000,market_cap_rank:2,ath:4954,ath_change_percentage:-58.6},technicals:{rsi:35,pct_from_ath:-58.6,pct_vs_200sma:-32.5},changes:{"24h":1.6,"7d":6.1,"30d":-8.2},role:"DeFi settlement layer. Staking yield ~3-4%.",signals:[]}},suggestions:{}};

const fmt=(n,d=2)=>n!=null?Number(n).toFixed(d):"—";
const fP=n=>n!=null?(n>=0?"+":"")+Number(n).toFixed(1)+"%":"—";
const f$=n=>n!=null?(n>=1000?"$"+Number(n).toLocaleString(undefined,{maximumFractionDigits:n>=10000?0:2}):"$"+fmt(n)):"—";
const fQ=n=>n!=null?(n>=1?fmt(n,2):fmt(n,4)):"—";
const TIER_C={core:"#00e676",growth:"#648cff",moderate:"#ffd600",speculative:"#ff9100"};
const STATUS_C={ACCUMULATE:{c:"#00e676",i:"🟢"},HOLD:{c:"#ffd600",i:"🟡"},CAUTION:{c:"#ff9100",i:"🟠"},REDUCE:{c:"#ff1744",i:"🔴"}};

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
    <div style={{fontSize:"9px",color:"#333",marginTop:"6px"}}>CoinGecko ID = lowercase slug from coingecko.com URL. Set dollars to 0 to add to watchlist only.</div>
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
        {!isWL&&<span style={{fontSize:"9px",color:tierColor,padding:"2px 6px",borderRadius:"3px",background:`${tierColor}15`,fontFamily:"monospace"}}>{card.risk_tier}</span>}
      </div>
      <div style={{display:"flex",alignItems:"center",gap:"12px"}}>
        <span style={{fontSize:"16px",fontWeight:600,color:"#e1e4e8",fontFamily:"monospace"}}>{f$(card.price)}</span>
        {!isWL&&<span style={{fontSize:"12px",fontWeight:700,color:sc.c,padding:"2px 8px",borderRadius:"4px",background:`${sc.c}15`,fontFamily:"monospace"}}>{sc.i} {card.status}</span>}
        <span style={{fontSize:"13px",fontWeight:700,color:card.composite_score>=0?"#00e676":"#ff1744",fontFamily:"'JetBrains Mono'"}}>{card.composite_score>=0?"+":""}{fmt(card.composite_score,1)}</span>
      </div>
    </div>

    <div style={{display:"flex",gap:"16px",marginTop:"8px",fontSize:"11px",fontFamily:"monospace",flexWrap:"wrap"}}>
      {!isWL&&<><span style={{color:"#555"}}>Position: <span style={{color:"#e1e4e8"}}>{f$(card.dollars)}</span></span>
        {card.estimated_quantity&&<span style={{color:"#555"}}>Qty: <span style={{color:"#e1e4e8"}}>{fQ(card.estimated_quantity)} {card.symbol}</span></span>}</>}
      {card.market?.market_cap&&<span style={{color:"#555"}}>MCap: <span style={{color:"#8a8f98"}}>{f$(card.market.market_cap/1e9)}B</span></span>}
      {card.market?.market_cap_rank&&<span style={{color:"#555"}}>Rank: <span style={{color:"#8a8f98"}}>#{card.market.market_cap_rank}</span></span>}
      {card.technicals?.pct_from_ath!=null&&<span style={{color:card.technicals.pct_from_ath>-20?"#ff9100":"#8a8f98"}}>{card.technicals.pct_from_ath.toFixed(0)}% from ATH</span>}
      {card.changes&&Object.entries(card.changes).map(([k,v])=><span key={k} style={{color:v>=0?"#00e676":"#ff1744"}}>{k}: {fP(v)}</span>)}
    </div>

    {card.role&&<div style={{fontSize:"10px",color:"#444",marginTop:"6px",fontStyle:"italic"}}>{card.role}</div>}

    {expanded&&<div style={{marginTop:"12px",paddingTop:"12px",borderTop:"1px solid #1a1f2e"}}>
      {card.technicals&&<div style={{display:"flex",gap:"16px",flexWrap:"wrap",marginBottom:"10px",fontSize:"11px",fontFamily:"monospace"}}>
        {card.technicals.rsi!=null&&<span style={{color:"#555"}}>RSI: <span style={{color:card.technicals.rsi>75?"#ff1744":card.technicals.rsi<30?"#00e676":"#e1e4e8"}}>{card.technicals.rsi}</span></span>}
        {card.technicals.sma200&&<span style={{color:"#555"}}>200-SMA: <span style={{color:"#8a8f98"}}>{f$(card.technicals.sma200)}</span></span>}
        {card.technicals.pct_vs_200sma!=null&&<span style={{color:card.technicals.pct_vs_200sma>0?"#00e676":"#ff1744"}}>{card.technicals.pct_vs_200sma>0?"+":""}{card.technicals.pct_vs_200sma}% vs 200-SMA</span>}
        {card.technicals.golden_cross!=null&&<span style={{color:card.technicals.golden_cross?"#00e676":"#ff1744"}}>{card.technicals.golden_cross?"Golden Cross":"Death Cross"}</span>}
        {card.technicals.volatility_ann&&<span style={{color:"#555"}}>Vol: <span style={{color:card.technicals.volatility_ann>100?"#ff9100":"#8a8f98"}}>{card.technicals.volatility_ann}% ann</span></span>}
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

    {/* Header */}
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
      {/* Market Health + Portfolio */}
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"16px",marginBottom:"24px"}}>
        <div style={{background:"#0d1117",borderRadius:"8px",border:"1px solid #1a1f2e",padding:"20px"}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:"12px"}}>
            <span style={{fontSize:"11px",color:"#555",textTransform:"uppercase",letterSpacing:"2px",fontFamily:"monospace"}}>Market Health</span>
            <span style={{fontSize:"20px",fontWeight:700,color:ms.color||"#555",fontFamily:"'JetBrains Mono'"}}>{mh.score>=0?"+":""}{fmt(mh.score||0,1)}</span>
          </div>
          <div style={{padding:"8px 12px",borderRadius:"6px",background:`${ms.color||"#555"}10`,border:`1px solid ${ms.color||"#555"}25`,fontSize:"13px",color:ms.color,fontWeight:500,marginBottom:"12px"}}>{ms.message||""}</div>
          {mh.signals?.map((sig,i)=>{const c=sig.status==="bullish"?"#00e676":sig.status==="bearish"?"#ff1744":"#ffd600";return(
            <div key={i} style={{display:"flex",justifyContent:"space-between",padding:"5px 0",borderBottom:"1px solid #1a1f2e",fontSize:"11px"}}>
              <span style={{color:"#8a8f98"}}>{sig.name}</span>
              <span style={{color:c,fontFamily:"monospace"}}>{typeof sig.value==="number"?(sig.value>100?sig.value.toLocaleString():sig.value):""} — {sig.status}</span>
            </div>)})}
        </div>

        <div style={{background:"#0d1117",borderRadius:"8px",border:"1px solid #1a1f2e",padding:"20px"}}>
          <div style={{fontSize:"11px",color:"#555",textTransform:"uppercase",letterSpacing:"2px",fontFamily:"monospace",marginBottom:"12px"}}>Crypto Portfolio</div>
          <div style={{fontSize:"28px",fontWeight:700,color:"#e1e4e8",fontFamily:"'Space Grotesk'",marginBottom:"4px"}}>{f$(s.portfolio_summary?.total_invested||0)}</div>
          <div style={{fontSize:"11px",color:"#555",marginBottom:"16px"}}>on {s.portfolio_summary?.exchange||"Exchange"}</div>

          {/* Quick price boxes for BTC/ETH/SOL */}
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

      {/* Add Coin Form */}
      <AddCoinForm onAdd={fetchData}/>

      {/* Main Content */}
      <div style={{display:"grid",gridTemplateColumns:"1fr 360px",gap:"24px"}}>
        <div>
          {/* Holdings */}
          {held.length>0&&<>
            <div style={{fontSize:"11px",color:"#555",textTransform:"uppercase",letterSpacing:"2px",fontFamily:"monospace",marginBottom:"10px"}}>Holdings ({held.length})</div>
            {held.map((c,i)=><CoinCard key={i} card={c}/>)}</>}

          {/* Watchlist */}
          {watchlist.length>0&&<>
            <div style={{fontSize:"11px",color:"#555",textTransform:"uppercase",letterSpacing:"2px",fontFamily:"monospace",marginBottom:"10px",marginTop:"24px"}}>Watchlist ({watchlist.length})</div>
            {watchlist.map((c,i)=><CoinCard key={i} card={c}/>)}</>}
        </div>

        {/* Suggestions Sidebar */}
        <div>
          {suggestions&&<>
            {suggestions.market_summary&&<div style={{background:"#0d1117",borderRadius:"8px",border:"1px solid #1a1f2e",padding:"16px",marginBottom:"16px"}}>
              <div style={{fontSize:"10px",color:"#555",textTransform:"uppercase",letterSpacing:"1.5px",marginBottom:"8px",fontFamily:"monospace"}}>Claude's Crypto Research</div>
              <div style={{fontSize:"12px",color:"#c8ccd4",lineHeight:1.6,marginBottom:"8px"}}>{suggestions.market_summary}</div>
              {suggestions.on_chain_highlights&&<div style={{fontSize:"11px",color:"#8a8f98",lineHeight:1.5,padding:"8px",background:"rgba(247,147,26,0.04)",borderRadius:"4px",borderLeft:"2px solid #f7931a",marginBottom:"8px"}}>{suggestions.on_chain_highlights}</div>}
              {suggestions.btc_cycle_assessment&&<div style={{fontSize:"11px",color:"#648cff",marginBottom:"6px"}}>Cycle: {suggestions.btc_cycle_assessment}</div>}
              <div style={{fontSize:"11px",color:suggestions.sector_sentiment==="bullish"?"#00e676":suggestions.sector_sentiment==="bearish"?"#ff1744":"#ffd600",fontWeight:600}}>{suggestions.sector_sentiment?.toUpperCase()}</div>
              <div style={{fontSize:"9px",color:"#333",marginTop:"6px",fontFamily:"monospace"}}>{suggestions._generated_at||""}</div>
            </div>}

            {suggestions.new_suggestions?.length>0&&<div style={{marginBottom:"16px"}}>
              <div style={{fontSize:"10px",color:"#648cff",textTransform:"uppercase",letterSpacing:"1.5px",marginBottom:"8px",fontFamily:"monospace"}}>New Coin Ideas</div>
              {suggestions.new_suggestions.map((s,i)=><div key={i} style={{background:"#0d1117",border:"1px solid #1a1f2e",borderLeft:"3px solid #648cff",borderRadius:"8px",padding:"12px",marginBottom:"6px"}}>
                <div style={{fontSize:"13px",fontWeight:700,color:"#e1e4e8",fontFamily:"monospace"}}>{s.symbol} <span style={{fontWeight:400,fontSize:"11px",color:"#8a8f98"}}>{s.name}</span></div>
                <div style={{fontSize:"11px",color:"#8a8f98",marginTop:"4px"}}>{s.why_now}</div>
                {s.suggested_allocation_usd&&<div style={{fontSize:"10px",color:"#648cff",marginTop:"4px"}}>Suggested: {f$(s.suggested_allocation_usd)}</div>}
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

          {/* On-Chain Indicators Note */}
          <div style={{background:"#0d1117",borderRadius:"8px",border:"1px solid #1a1f2e",padding:"16px",marginTop:"16px"}}>
            <div style={{fontSize:"10px",color:"#555",textTransform:"uppercase",letterSpacing:"1.5px",marginBottom:"8px",fontFamily:"monospace"}}>On-Chain Status</div>
            <div style={{fontSize:"11px",color:"#444",lineHeight:1.6}}>
              MVRV Z-Score, NUPL, Puell Multiple, and exchange reserve data require premium API access (CryptoQuant/Glassnode). Check these manually:
            </div>
            <div style={{marginTop:"8px",display:"flex",flexDirection:"column",gap:"4px"}}>
              {[["MVRV Z-Score","bitcoinmagazinepro.com/charts/mvrv-zscore"],["NUPL","lookintobitcoin.com"],["Puell Multiple","bitcoinmagazinepro.com/charts/puell-multiple"],["Fear & Greed","alternative.me/crypto/fear-and-greed-index"]].map(([name,url])=>(
                <div key={name} style={{fontSize:"10px"}}><span style={{color:"#8a8f98"}}>{name}: </span><span style={{color:"#648cff"}}>{url}</span></div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div style={{marginTop:"32px",fontSize:"10px",color:"#333",fontFamily:"monospace",display:"flex",justifyContent:"space-between"}}>
        <span>Crypto Dashboard v1.0 — Not financial advice</span>
        <span>Data: CoinGecko + DeFiLlama | {cards.length} coins tracked</span>
      </div>
    </div>
  </div>);
}
