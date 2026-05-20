/* Shared chrome: theme + font selectors, nav highlight */
(function(){
  let T='light',F='aptos';
  try{T=localStorage.getItem('myrrha-theme')||'light';}catch(e){}
  try{F=localStorage.getItem('myrrha-font')||'aptos';}catch(e){}
  document.documentElement.setAttribute('data-theme',T);
  document.body && document.body.setAttribute('data-font',F);
  window.MYRRHA={
    nav:[
      ['index.html','Hub'],
      ['slides.html','Slides'],
      ['reports.html','Reports'],
      ['tables.html','Tables'],
      ['graphs.html','Graphs'],
      ['status.html','Status'],
      ['truth.html','Truth'],
      ['utilities.html','Utilities'],
      ['review-dmaic.html','DMAIC'],
      ['action-tracker.html','Actions'],
      ['artifact-tracker.html','Artifacts'],
      ['weighted-priority.html','Priority'],
      ['bt-ranking.html','BT Rank'],
      ['bt-artifacts.html','BT Arts'],
      ['bt-scatter.html','Scatter'],
      ['vendor-kaeser.html','Kaeser'],
      ['qa-interactive.html','QA'],
      ['qa-test-suite.html','Tests'],
      ['responsive-review.html','Responsive'],
      ['artifact-index.html','Index'],
      ['changelog-dev.html','Changelog'],
      ['stats-proofs.html','Proofs'],
      ['interaction-analysis.html','Deps'],
      ['testing-strategy.html','Testing'],
      ['code-quality.html','Quality'],
      ['bt-validation.html','BT Valid'],
      ['dmaic-statistical.html','BT DMAIC'],
      ['search-index.html','Search'],
    ],
    mountChrome(activeFile, title){
      const bar=document.createElement('div');bar.className='topbar';
      const here=location.pathname.split('/').pop()||'index.html';
      bar.innerHTML=`
        <div class="brand">⚙ MYRRHA · WCS Handover</div>
        <span class="ver">v0.4.7</span>
        <nav>${this.nav.map(([h,n])=>`<a href="${h}" class="${h===here?'active':''}">${n}</a>`).join('')}</nav>
        <div class="controls">
          <select id="themeSel" title="Theme">
            <option value="light">☀ Light</option>
            <option value="dark">☾ Dark</option>
          </select>
          <select id="fontSel" title="Font">
            <option value="aptos">Aptos</option>
            <option value="consolas">Consolas</option>
          </select>
        </div>`;
      document.body.insertBefore(bar,document.body.firstChild);
      const ts=document.getElementById('themeSel');ts.value=T;
      ts.onchange=e=>{try{localStorage.setItem('myrrha-theme',e.target.value);}catch(e){}document.documentElement.setAttribute('data-theme',e.target.value)};
      const fs=document.getElementById('fontSel');fs.value=F;
      fs.onchange=e=>{try{localStorage.setItem('myrrha-font',e.target.value);}catch(e){}document.body.setAttribute('data-font',e.target.value)};
    }
  };
  document.addEventListener('DOMContentLoaded',()=>{
    document.body.setAttribute('data-font',F);
    if(!document.body.querySelector('.topbar')) MYRRHA.mountChrome();
  });
})();

/* Shared MYRRHA dataset (single source of truth, mirrored from truth.html) */
window.MYRRHA_DATA={
  baseline:{flow:350,pressure:14,unit:'g/s @ barG'},
  targets:[200,250,275,304,336,344,350],
  models:{
    alat575:{label:'ALaT FSD 575 SFC',perUnit:112.54,freq:72,units:3,deployed:2,deployedFlow:220,
            motor:315,pkg:348.54,shaft:314.05,cw:18.2,cwHeat:323.9,airHeat:17.4,waste:14.2,noise:75,oil:173,weight:6770},
    lkt475nom:{label:'LKT FSD 475 SFC nominal',perUnit:88,freq:57,units:3,deployed:3,deployedFlow:264,
            motor:250,pkg:266,shaft:null,cw:15.5,cwHeat:230.9,airHeat:13.1,waste:5.1,noise:74,oil:180,weight:6400},
    lkt475max:{label:'LKT FSD 475 SFC max',perUnit:96.1,freq:62,units:3,deployed:3,deployedFlow:288.3,
            motor:250,pkg:289,shaft:null,cw:15.5,cwHeat:230.9,airHeat:13.1,waste:5.1,noise:74,oil:180,weight:6400}
  }
};
