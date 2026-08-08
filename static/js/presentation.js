const slides=[...document.querySelectorAll('.slide')];
const no=document.getElementById('slideNo');
const total=document.getElementById('slideTotal');
const bar=document.getElementById('progressBar');
const sectionTitle=document.getElementById('presentSectionTitle');
let i=0;
let wheelLock=false;
let touchStartX=0;
let touchStartY=0;

total.textContent=String(slides.length).padStart(2,'0');

function show(n){
  i=Math.max(0,Math.min(slides.length-1,n));
  slides.forEach((slide,index)=>{
    const active=index===i;
    slide.classList.toggle('active',active);
    if(active) slide.scrollTop=0;
  });
  no.textContent=String(i+1).padStart(2,'0');
  bar.style.width=((i+1)/slides.length*100)+'%';
  if(sectionTitle) sectionTitle.textContent=slides[i]?.dataset.title||'IMSA';
}

function next(){show(i+1)}
function prev(){show(i-1)}

document.getElementById('nextSlide').onclick=next;
document.getElementById('prevSlide').onclick=prev;
document.getElementById('fullscreen').onclick=()=>{
  document.fullscreenElement?document.exitFullscreen():document.documentElement.requestFullscreen().catch(()=>{});
};

addEventListener('keydown',event=>{
  if(['ArrowRight','ArrowDown','PageDown',' '].includes(event.key)){event.preventDefault();next()}
  if(['ArrowLeft','ArrowUp','PageUp'].includes(event.key)){event.preventDefault();prev()}
  if(event.key==='Home'){event.preventDefault();show(0)}
  if(event.key==='End'){event.preventDefault();show(slides.length-1)}
  if(event.key.toLowerCase()==='f'){event.preventDefault();document.getElementById('fullscreen').click()}
});

addEventListener('wheel',event=>{
  const active=slides[i];
  if(!active||wheelLock)return;

  const canDown=active.scrollTop+active.clientHeight<active.scrollHeight-4;
  const canUp=active.scrollTop>4;
  if((event.deltaY>0&&canDown)||(event.deltaY<0&&canUp))return;

  wheelLock=true;
  event.deltaY>0?next():prev();
  setTimeout(()=>wheelLock=false,520);
},{passive:true});

addEventListener('touchstart',event=>{
  const touch=event.changedTouches[0];
  touchStartX=touch.clientX;
  touchStartY=touch.clientY;
},{passive:true});

addEventListener('touchend',event=>{
  const touch=event.changedTouches[0];
  const dx=touch.clientX-touchStartX;
  const dy=touch.clientY-touchStartY;
  if(Math.abs(dx)>65&&Math.abs(dx)>Math.abs(dy)*1.25){
    dx<0?next():prev();
  }
},{passive:true});

show(0);
