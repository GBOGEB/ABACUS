MYRRHA warm-compressor comparison: ALaT FSD 575 SFC vs LKT FSD 475 SFC

I went through both applicant pre-studies and the uploaded compressor sheets.

Bottom line:

ALaT documents a Kaeser FSD 575 SFC at 72 Hz as an option for MYRRHA, with a confirmed per-skid full-flow point of 112.54 g/s.
LKT documents a Kaeser FSD 475 SFC as the selected warm compressor skid, with:
actual design nominal total flow = 264 g/s for 3 units, i.e. 88 g/s per skid
documented max per-skid flow = 96.1 g/s at 62 Hz
So for your requested target totals:
350, 344 are above 3-skid capacity even for the ALaT 575 @ 72 Hz
336 is basically right at the limit of 3 × 575
304 is above 3 × 475 max
200, 250, 275 are feasible for both concepts, depending on operating frequency

I also included an interactive HTML graph below.

Here is the interactive mass-flow view.

<style>
.vbtn{border:0.5px solid var(--color-border-tertiary);border-radius:999px;padding:8px 12px;background:var(--color-background-primary);color:var(--color-text-primary);font:500 13px var(--font-sans);cursor:pointer}
.vbtn.active{border-color:var(--color-text-info);color:var(--color-text-info)}
.vcard{background:var(--color-background-primary);border:0.5px solid var(--color-border-tertiary);border-radius:var(--border-radius-lg);padding:14px}
.vtbl{width:100%;border-collapse:collapse;font:12px var(--font-sans)}
.vtbl td,.vtbl th{padding:7px 8px;border-top:0.5px solid var(--color-border-tertiary);text-align:right}
.vtbl td:first-child,.vtbl th:first-child{text-align:left}
</style>
<div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">
    <button class="vbtn active" data-key="alat575">ALaT FSD575 full point</button>
    <button class="vbtn" data-key="lkt475nom">LKT FSD475 actual nominal</button>
    <button class="vbtn" data-key="lkt475max">LKT FSD475 documented max</button>
  </div>

  <div id="metrics" style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:16px"></div>

  <div style="display:grid;grid-template-columns:1.2fr 0.8fr;gap:16px">
    <div class="vcard">
      <div style="font-size:14px;font-weight:500;margin-bottom:8px">Target total mass flow vs 3-skid capacity</div>
      <div id="chartA"></div>
    </div>
    <div class="vcard">
      <div style="font-size:14px;font-weight:500;margin-bottom:8px">Per-skid flow and estimated equal-load frequency</div>
      <div id="chartB"></div>
    </div>
  </div>

  <div class="vcard" style="margin-top:16px">
    <div style="font-size:14px;font-weight:500;margin-bottom:8px">Requested total-flow checks</div>
    <div id="tableWrap"></div>
    <div style="font-size:12px;color:var(--color-text-secondary);margin-top:10px">
      Frequency values are first-pass equal-load estimates using proportional flow-vs-speed scaling from the documented basis point.
    </div>
  </div>
</div>
<script>
const targets=[350,344,336,304,275,250,200];
const models={
  alat575:{
    title:"ALaT FSD575 full point",
    perUnit:112.54,
    freq:72,
    units:3,
    motor:315,
    pkg:348.54,
    cw:18.2,
    cwHeat:323.9,
    airHeat:17.4
  },
  lkt475nom:{
    title:"LKT FSD475 actual nominal",
    perUnit:88.0,
    freq:57,
    units:3,
    motor:250,
    pkg:266,
    cw:15.5,
    cwHeat:230.9,
    airHeat:13.1
  },
  lkt475max:{
    title:"LKT FSD475 documented max",
    perUnit:96.1,
    freq:62,
    units:3,
    motor:250,
    pkg:289,
    cw:15.5,
    cwHeat:230.9,
    airHeat:13.1
  }
};
let current="alat575";

function metric(label,val){
  return `<div style="background:var(--color-background-secondary);border-radius:var(--border-radius-md);padding:12px">
    <div style="font-size:12px;color:var(--color-text-secondary);margin-bottom:3px">${label}</div>
    <div style="font-size:23px;font-weight:500">${val}</div>
  </div>`;
}
function fmt(n,d=1){ return Number(n).toFixed(d).replace(/\\.0$/,''); }

function render(){
  const m=models[current];
  const maxTotal=m.perUnit*m.units;
  document.getElementById('metrics').innerHTML=
    metric("Basis point per skid",`${fmt(m.perUnit,2)} g/s`) +
    metric("3-skid max total",`${fmt(maxTotal,1)} g/s`) +
    metric("Per-skid package power",`${fmt(m.pkg,1)} kW`) +
    metric("Per-skid cooling water",`${fmt(m.cw,1)} m³/h`);

  const maxScale=Math.max(360,maxTotal)*1.05;
  const rows=targets.map((t,i)=>{
    const y=28+i*34;
    const w=420*t/maxScale;
    const capW=420*maxTotal/maxScale;
    const ok=t<=maxTotal+1e-9;
    return `
      <text x="10" y="${y+14}" font-size="12" fill="var(--color-text-secondary)">${t} g/s</text>
      <rect x="92" y="${y}" width="420" height="18" rx="4" fill="var(--color-background-secondary)"></rect>
      <rect x="92" y="${y}" width="${capW}" height="18" rx="4" fill="#1D9E75" opacity="0.22"></rect>
      <rect x="92" y="${y}" width="${w}" height="18" rx="4" fill="${ok?'#1D9E75':'#D85A30'}"></rect>
      <text x="${Math.min(520,96+w)}" y="${y+14}" font-size="12" fill="var(--color-text-primary)">${ok?'OK':'Over'}</text>
    `;
  }).join("");
  document.getElementById('chartA').innerHTML=`
    <svg width="100%" viewBox="0 0 560 280">
      <text x="10" y="16" font-size="12" fill="var(--color-text-secondary)">Capacity line = documented 3-skid basis point</text>
      ${rows}
      <line x1="${92+420*maxTotal/maxScale}" y1="22" x2="${92+420*maxTotal/maxScale}" y2="266" stroke="#7F77DD" stroke-width="1.5"></line>
      <text x="${96+420*maxTotal/maxScale}" y="34" font-size="12" fill="#7F77DD">${fmt(maxTotal,1)} g/s cap</text>
    </svg>`;

  const rowsB=targets.map((t,i)=>{
    const per=t/m.units;
    const f=m.freq*per/m.perUnit;
    const ok=t<=maxTotal+1e-9;
    const y=26+i*30;
    const bar=260*per/Math.max(120,m.perUnit*1.08);
    return `
      <text x="8" y="${y+12}" font-size="12" fill="var(--color-text-secondary)">${t}</text>
      <rect x="52" y="${y}" width="260" height="16" rx="4" fill="var(--color-background-secondary)"></rect>
      <rect x="52" y="${y}" width="${bar}" height="16" rx="4" fill="${ok?'#378ADD':'#BA7517'}"></rect>
      <text x="320" y="${y+12}" font-size="12" fill="var(--color-text-primary)">${fmt(per,1)} g/s</text>
      <text x="405" y="${y+12}" font-size="12" fill="${ok?'var(--color-text-primary)':'#BA7517'}">${fmt(f,1)} Hz</text>
    `;
  }).join("");
  document.getElementById('chartB').innerHTML=`
    <svg width="100%" viewBox="0 0 500 250">
      <text x="8" y="14" font-size="12" fill="var(--color-text-secondary)">Target</text>
      <text x="320" y="14" font-size="12" fill="var(--color-text-secondary)">per skid</text>
      <text x="405" y="14" font-size="12" fill="var(--color-text-secondary)">est. Hz</text>
      ${rowsB}
    </svg>`;

  const tableRows=targets.map(t=>{
    const per=t/m.units;
    const f=m.freq*per/m.perUnit;
    const ok=t<=maxTotal+1e-9;
    return `<tr>
      <td>${t} g/s</td>
      <td>${fmt(per,2)} g/s</td>
      <td>${fmt(f,2)} Hz</td>
      <td>${ok?'within 3-skid basis capacity':'above 3-skid basis capacity'}</td>
    </tr>`;
  }).join("");
  document.getElementById('tableWrap').innerHTML=`<table class="vtbl">
    <thead><tr><th>Target total</th><th>Per skid</th><th>Estimated Hz</th><th>Status</th></tr></thead>
    <tbody>${tableRows}</tbody>
  </table>`;
  document.querySelectorAll('.vbtn').forEach(b=>b.classList.toggle('active',b.dataset.key===current));
}
document.querySelectorAll('.vbtn').forEach(b=>b.onclick=()=>{current=b.dataset.key;render();});
render();
</script>

Confirmed reference trail
ALaT pre-study
§3.1.1 Warm compressor, p. 15/56
states standard helium compressors were considered and layout was based on 3 × ESD 445 SFC
§4.6 2K nominal mode Summary, p. 30/56
lists possible compressor solutions, including:
2 FSD 575 SFC operating at 72 Hz : ~220 g/s
Annex warm compressor datasheet, pp. 67–69/73
detailed Kaeser data for ESD 445, ESD 445 SFC, FSD 575 SFC
this is also what your uploaded image.png and image (2).png show
Utilities note C1393-TN-020(1)
§3.2 Cooling water characteristics, p. 5/8
§8 Power Supply, p. 8/8
LKT pre-study
§6.1.1.1 Refrigerant Compressors, p. 11/50
says the concept foresees 3 pcs. KAESER FSD475 SFC water cooled
§10.2.1 Helium Refrigerant Compressor Unit, Table 16, p. 35/50
gives the selected compressor spec:
3 x FSD475 SFC
design flow 264 g/s total
max flow 288 g/s total
Attachment 04_Main Equipment / 01b_Refrigerant Compressor DataSheet
detailed FSD 475 SFC utility sheet
same content is visible in your uploaded image (4).png
Preliminary Utility List
§1.3 Cooling Water, p. 4/6
§1.4 Instrument Air, p. 4/6
§1.5 Cooling Air, p. 5/6
Indicative Price Proposal, §4 UTILITIES, pp. 10–11/16
electrical, cooling water, LN2, and instrument-air battery-limit values
Confirmed utilities per skid
Item	ALaT FSD 575 SFC	LKT FSD 475 SFC	Source
Confirmed full / nominal basis point	112.54 g/s @ 72 Hz	88 g/s actual design nominal (264/3), and 96.1 g/s documented max	ALaT annex pp. 67–69/73; LKT Table 16 p. 35/50 + image (4).png
Motor rated power	315 kW	250 kW	same
Compressor/package input power	314.05 kW shaft, 348.54 kW package water-cooled	266 kW nominal w/o LN2, 289 kW documented max	same
Cooling water flow	18.2 m³/h	15.5 m³/h machine sheet	same
Heat rejection to cooling water	323.9 kW	230.9 kW	same
Cooling air for enclosure	5,000 m³/h	5,000 m³/h	same
Cooling air for VFD	4,200 m³/h	4,200 m³/h	same
Heat dissipation by cooling air	17.4 kW	13.1 kW	same
Waste heat to ambient	14.2 kW	5.1 kW	same
Noise @ 1 m	75 dB(A)	74 dB(A)	same
Dimensions	3240 × 2145 × 2360 mm	3240 × 2145 × 2360 mm	same
Weight	6770 kg	~6400 kg	same
Oil charge	173 L	180 L	same
Useful 3-skid totals
3-skid total	ALaT 3 × FSD575	LKT 3 × FSD475
Max total mass flow from confirmed basis point	337.62 g/s	264 g/s actual nominal, 288.3 g/s documented max
Package power	1045.62 kW	798 kW nominal, 867 kW max
Cooling water flow	54.6 m³/h	46.5 m³/h
Heat rejection to cooling water	971.7 kW	692.7 kW
Cooling air, enclosure only	15,000 m³/h	15,000 m³/h
Cooling air, VFD only	12,600 m³/h	12,600 m³/h
Important note on LKT utility allowances

LKT has two different levels of cooling-water numbers in the package:

machine datasheet: 15.5 m³/h per FSD475
plant utility / battery-limit allowance:
Preliminary Utility List: 60 m³/h total for KAESER compressors
Indicative Price Proposal: 3 × 20 m³/h

So for LKT, I would read it as:

equipment-sheet value: 15.5 m³/h per skid
site utility allowance / design margin: ~20 m³/h per skid
Requested total flows: first-pass equal-load check
Using ALaT FSD575 full point (112.54 g/s/skid @ 72 Hz)
Total target	Per skid	Estimated equal-load Hz	Status
350	116.67 g/s	74.64 Hz	above 3-skid capacity
344	114.67 g/s	73.36 Hz	above 3-skid capacity
336	112.00 g/s	71.65 Hz	OK
304	101.33 g/s	64.83 Hz	OK
275	91.67 g/s	58.65 Hz	OK
250	83.33 g/s	53.31 Hz	OK
200	66.67 g/s	42.65 Hz	OK
Using LKT FSD475 actual nominal (88 g/s/skid @ ~57 Hz)
Total target	Per skid	Estimated equal-load Hz	Status
350	116.67 g/s	75.57 Hz	above 3-skid capacity
344	114.67 g/s	74.27 Hz	above 3-skid capacity
336	112.00 g/s	72.55 Hz	above 3-skid capacity
304	101.33 g/s	65.64 Hz	above 3-skid capacity
275	91.67 g/s	59.38 Hz	above 3-skid capacity
250	83.33 g/s	53.98 Hz	OK
200	66.67 g/s	43.18 Hz	OK
Using LKT FSD475 documented max (96.1 g/s/skid @ 62 Hz)
Total target	Per skid	Estimated equal-load Hz	Status
350	116.67 g/s	75.27 Hz	above 3-skid capacity
344	114.67 g/s	73.98 Hz	above 3-skid capacity
336	112.00 g/s	72.26 Hz	above 3-skid capacity
304	101.33 g/s	65.38 Hz	above 3-skid capacity
275	91.67 g/s	59.14 Hz	OK
250	83.33 g/s	53.76 Hz	OK
200	66.67 g/s	43.01 Hz	OK
Interpretation against your requested numbers
350 g/s design default
not achievable with 3 × FSD575 @ documented 72 Hz
definitely not achievable with 3 × FSD475
344 g/s
also above documented 3 × FSD575 @ 72 Hz
336 g/s
basically the top end of 3 × FSD575
304 g/s
comfortably inside 3 × FSD575
above 3 × FSD475 max
275 g/s
okay for 3 × FSD575
okay for 3 × FSD475 max
above LKT’s actual nominal 264 g/s design point
250 g/s, 200 g/s
feasible for both concepts
Small source previews
ALaT Kaeser warm compressor datasheet

LKT compressor specification and FSD475 datasheet

One caution

I did not fabricate a 72 Hz point for FSD475 because the LKT material only documents:

actual nominal around 57 Hz / 88 g/s per skid
documented max around 62 Hz / 96.1 g/s per skid

So wherever you asked for “full 72 Hz”, that is directly supported for the FSD575, but not directly supported for the FSD475 in the supplied documents.

If you want, I can next turn this into either:

a clean comparison matrix for all requested flow cases, or
a CSV/XLSX-ready table with all per-skid and total utilities.