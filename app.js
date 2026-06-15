
let jobId=null, routes=[], summary=[], invalid=[];
const map=L.map("map").setView([-10.911148,-37.059038],11);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19}).addTo(map);
let layer=L.layerGroup().addTo(map);

document.getElementById("form").addEventListener("submit", async e=>{
 e.preventDefault();
 const fd=new FormData(e.target);
 fd.set("file",document.getElementById("file").files[0]);
 document.getElementById("status").textContent="Processando...";
 const res=await fetch("/api/upload",{method:"POST",body:fd});
 const data=await res.json();
 if(!res.ok){document.getElementById("status").textContent="Erro";return;}
 jobId=data.job_id; routes=data.routes; summary=data.summary; invalid=data.invalid;
 render();
 document.getElementById("status").textContent="Roteirização gerada.";
});

function render(){
 document.getElementById("pedidos").textContent=routes.length;
 document.getElementById("rotas").textContent=summary.length;
 document.getElementById("invalidos").textContent=invalid.length;
 document.getElementById("km").textContent=summary.reduce((s,r)=>s+Number(r.KM_ROTA_ESTIMADO||0),0).toFixed(1);
 table("summaryTable",summary,true);
 table("routesTable",routes,true);
 table("invalidTable",invalid,true);
 renderMap();
 renderRomaneio();
}

function table(id,data,links){
 const el=document.getElementById(id);
 if(!data.length){el.innerHTML="<tr><td>Sem dados</td></tr>";return;}
 const cols=Object.keys(data[0]);
 let h="<thead><tr>"+cols.map(c=>`<th>${c}</th>`).join("")+"</tr></thead><tbody>";
 data.forEach(r=>{
   h+="<tr>"+cols.map(c=>{
     const v=r[c]??"";
     if(links&&String(v).startsWith("https://"))return`<td><a href="${v}" target="_blank">Abrir</a></td>`;
     if(c==="COR"||c==="COR_SPR")return`<td><span style="display:inline-block;width:16px;height:16px;border-radius:50%;background:${v}"></span></td>`;
     return`<td>${v}</td>`;
   }).join("")+"</tr>";
 });
 h+="</tbody>";el.innerHTML=h;
}

function latKey(r){return Object.keys(r).find(k=>k.toLowerCase().includes("latitude"))}
function lonKey(r){return Object.keys(r).find(k=>k.toLowerCase().includes("longitude"))}

function renderMap(){
 layer.clearLayers();
 const bounds=[];
 summary.forEach(s=>{
   const rs=routes.filter(r=>r.SPR_FINAL===s.SPR).sort((a,b)=>Number(a.SEQ_SPR)-Number(b.SEQ_SPR));
   const pts=[[-10.911148,-37.059038]];
   rs.forEach(r=>{
     const lat=Number(String(r[latKey(r)]).replace(",","."));
     const lon=Number(String(r[lonKey(r)]).replace(",","."));
     if(!isNaN(lat)&&!isNaN(lon)){
       pts.push([lat,lon]);bounds.push([lat,lon]);
       L.circleMarker([lat,lon],{radius:7,color:r.COR_SPR,fillColor:r.COR_SPR,fillOpacity:.9}).addTo(layer).bindPopup(`<b>${r.SPR_FINAL}</b><br>Seq ${r.SEQ_SPR}<br><a href="${r.LINK_PEDIDO_MAPS}" target="_blank">Pedido Maps</a>`);
     }
   });
   L.polyline(pts,{color:s.COR,weight:4}).addTo(layer).bindPopup(`<b>${s.SPR}</b><br><a href="${s.LINK_GOOGLE_MAPS}" target="_blank">Abrir Maps</a>`);
 });
 if(bounds.length)map.fitBounds(bounds,{padding:[30,30]});
}

function tab(id){
 document.querySelectorAll(".tab").forEach(t=>t.classList.add("hidden"));
 document.getElementById(id).classList.remove("hidden");
}

function exportCsv(){if(jobId)window.open(`/api/job/${jobId}/export.csv`,"_blank")}

function renderRomaneio(){
 const el=document.getElementById("romaneio");
 let h="";
 summary.forEach(s=>{
  const rs=routes.filter(r=>r.SPR_FINAL===s.SPR).sort((a,b)=>Number(a.SEQ_SPR)-Number(b.SEQ_SPR));
  h+=`<div style="page-break-after:always;padding:20px"><h2>GW Express - Romaneio ${s.SPR}</h2><p>Pedidos: ${s.QTD_PEDIDOS} | KM: ${s.KM_ROTA_ESTIMADO}</p><table><thead><tr><th>Seq</th><th>Pedido</th><th>Endereço</th><th>Assinatura</th></tr></thead><tbody>`;
  rs.forEach(r=>{
   const pedido=r["Waybill No"]||r["Tracking Number"]||r.ID_ROTA||"";
   const end=r["Consignee Address"]||r.Address||r["Endereço"]||"";
   h+=`<tr><td>${r.SEQ_SPR}</td><td>${pedido}</td><td>${end}</td><td></td></tr>`;
  });
  h+="</tbody></table></div>";
 });
 el.innerHTML=h;
}
function printRomaneio(){window.print()}
