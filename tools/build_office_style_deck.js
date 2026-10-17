/** Synthetic PPTX input fixture. No external assets or classified source. */
'use strict';
const pptxgen = require('pptxgenjs');
let slideQA = null;
try {
  slideQA = require(process.env.OPENAI_SLIDES_HELPERS || '/home/oai/skills/slides/pptxgenjs_helpers');
} catch (_error) {
  // Source builds outside the visual QA environment need not import hosted helpers.
  // Render and inspect the final deck before publishing or using it as a template.
}
const out = process.argv[2];
if (!out) { throw new Error('output .pptx path required'); }
const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'CODE PURPLE synthetic fixtures';
pptx.subject = 'Real PPTX style input; synthetic data';
pptx.title = 'CODE PURPLE / Office Style Input Reference';
pptx.lang = 'en-GB';
pptx.theme = {headFontFace:'Aptos Display', bodyFontFace:'Aptos', lang:'en-GB'};
const C={navy:'17283F',blue:'216BB0',teal:'138D88',amber:'D88731',pale:'ECF4F7',white:'FFFFFF',slate:'5F6D78',red:'B94B45'};
const S=pptx.ShapeType;
function bg(slide){slide.background={color:'FFFFFF'};slide.addShape(S.rect,{x:0,y:0,w:0.17,h:7.5,line:{color:C.teal},fill:{color:C.teal}});}
function label(slide,txt,x,y,w,color=C.teal){slide.addText(txt,{x,y,w,h:0.3,fontFace:'Aptos',fontSize:10,bold:true,color,margin:0,charSpacing:1.3,breakLine:false});}
function title(slide,txt){slide.addText(txt,{x:0.7,y:0.90,w:11.5,h:0.63,fontFace:'Aptos Display',fontSize:28,bold:true,color:C.navy,margin:0,breakLine:false});}
function bottom(slide,n){slide.addText(`SYNTHETIC INPUT  /  STYLE-FEED TEST ONLY     ${n}/3`,{x:0.72,y:7.04,w:11.9,h:0.22,fontFace:'Aptos',fontSize:9,color:C.slate,margin:0});}
let slide=pptx.addSlide();bg(slide);
label(slide,'CODE PURPLE  /  TEST INPUT',0.75,0.55,8);
slide.addText('Style evidence across\nOffice artifacts',{x:0.75,y:1.18,w:8.15,h:1.72,fontFace:'Aptos Display',fontSize:34,bold:true,color:C.navy,margin:0,breakLine:false});
slide.addText('DOCX  /  XLSX  /  PPTX',{x:0.78,y:3.05,w:7,h:0.5,fontFace:'Aptos',fontSize:19,color:C.blue,margin:0});
slide.addShape(S.rect,{x:0.77,y:4.12,w:7.8,h:1.25,rectRadius:0.15,line:{color:C.pale},fill:{color:C.pale}});
slide.addText('Illustrative controls only — not source-bound engineering acceptance.',{x:1.05,y:4.44,w:7.2,h:0.6,fontFace:'Aptos',fontSize:17,color:C.navy,margin:0});
slide.addShape(S.arc,{x:9.6,y:1.25,w:2.4,h:2.4,line:{color:C.teal,width:5},fill:{color:'FFFFFF',transparency:100}});
slide.addShape(S.ellipse,{x:10.14,y:1.8,w:1.32,h:1.32,line:{color:C.blue,width:1.5},fill:{color:C.blue}});
bottom(slide,1);
slide.addNotes('Synthetic dataset. Observed counts are not native ABACUS statuses.');
slide=pptx.addSlide();bg(slide);label(slide,'FORMAT & EVIDENCE  /  TYPOGRAPHY',0.75,0.47,8);title(slide,'A governed evidence panel');
const cols=[['N1','PASS',52,0,C.teal],['N2','PASS',53,0,C.teal],['N3','FAIL',53,1,C.red],['N4','FAIL',54,2,C.red],['N5','FAIL',56,1,C.red],['N6','PASS',58,0,C.teal]];
slide.addText('Six synthetic revisions',{x:0.74,y:1.62,w:5,h:0.5,fontFace:'Aptos Display',fontSize:18,bold:true,color:C.navy,margin:0});
slide.addShape(S.rect,{x:0.75,y:2.25,w:11.8,h:0.52,line:{color:C.blue},fill:{color:C.blue}});
const wx=[0.94,3.3,6.25,9.5];
['WAVE','STATUS','TESTS PASS','TESTS FAIL'].forEach((t,i)=>slide.addText(t,{x:wx[i],y:2.35,w:2.1,h:0.28,color:C.white,bold:true,fontSize:11,margin:0}));
cols.forEach((item,i)=>{const y=2.78+i*0.52;slide.addShape(S.rect,{x:0.75,y,w:11.8,h:0.51,line:{color:C.white,transparency:100},fill:{color:i%2?'F4F8FA':'FFFFFF'}});[item[0],item[1],String(item[2]),String(item[3])].forEach((t,j)=>slide.addText(t,{x:wx[j],y:y+0.12,w:2,h:0.24,color:j===1?item[4]:C.navy,fontSize:12,bold:j===1,margin:0}));});
slide.addText('A visible red test remains a failing test. No pass can override a separate governance block.',{x:0.75,y:6.32,w:11.2,h:0.45,color:C.amber,fontFace:'Aptos',fontSize:13,italic:true,margin:0});
bottom(slide,2);slide.addNotes('Demonstration values; not measured production coverage.');
slide=pptx.addSlide();bg(slide);label(slide,'VISUAL STYLE  /  DESIGN TOKENS',0.75,0.47,8);title(slide,'Typography, palette & hierarchy');
slide.addText('Aptos Display / Heading',{x:0.77,y:1.65,w:10.6,h:0.7,color:C.navy,fontFace:'Aptos Display',fontSize:28,bold:true,margin:0});
slide.addText('Aptos / Body text for measured evidence and controls',{x:0.77,y:2.48,w:11.4,h:0.5,color:C.slate,fontFace:'Aptos',fontSize:18,margin:0});
const colors=[['NAVY',C.navy],['BLUE',C.blue],['TEAL',C.teal],['AMBER',C.amber],['PALE',C.pale]];
colors.forEach((d,i)=>{let x=0.77+i*2.42;slide.addShape(S.rect,{x,y:3.55,w:2.05,h:1.2,line:{color:d[1]},fill:{color:d[1]}});slide.addText(d[0],{x,y:4.92,w:2.2,h:0.32,fontFace:'Aptos',fontSize:12,bold:true,color:C.navy,margin:0});slide.addText('#'+d[1],{x,y:5.32,w:2.2,h:0.35,fontFace:'Aptos',fontSize:11,color:C.slate,margin:0});});
slide.addText('Source bytes ≠ derived styles ≠ governance approval',{x:0.77,y:6.35,w:11.5,h:0.35,fontFace:'Aptos',fontSize:14,color:C.blue,bold:true,margin:0});bottom(slide,3);
if (slideQA) {
  for (const item of pptx._slides) {
    slideQA.warnIfSlideHasOverlaps(item, pptx);
    slideQA.warnIfSlideElementsOutOfBounds(item, pptx);
  }
}
pptx.writeFile({fileName:out});