(()=>{const cache={};const base='https://cdn.jsdelivr.net/npm/lucide-static@0.460.0/icons/';
class RI extends HTMLElement{static get observedAttributes(){return['name','size','stroke']}
connectedCallback(){this.r()}attributeChangedCallback(){if(this.isConnected)this.r()}
r(){const n=this.getAttribute('name');if(!n)return;const s=this.getAttribute('size')||20;const sw=this.getAttribute('stroke')||2.75;
this.style.width=this.style.height=s+'px';
const put=t=>{if(this.getAttribute('name')!==n||!t)return;this.innerHTML=t.replace(/width="24"/,'width="'+s+'"').replace(/height="24"/,'height="'+s+'"').replace(/stroke-width="2"/,'stroke-width="'+sw+'"')};
const c=cache[n];if(typeof c==='string')return put(c);
if(!c)cache[n]=fetch(base+n+'.svg').then(r=>r.ok?r.text():'').then(t=>(cache[n]=t,t)).catch(()=>'');
Promise.resolve(cache[n]).then(put)}}
if(!customElements.get('r-icon'))customElements.define('r-icon',RI)})();
