function toggleFilters(){const f=document.getElementById('filters');if(f)f.classList.toggle('open')}
function clearFilters(){location.href='/catalog'}

const favKey='drivekz_favorites';
function getFavs(){try{return JSON.parse(localStorage.getItem(favKey)||'[]')}catch{return []}}
function setFavs(ids){localStorage.setItem(favKey,JSON.stringify(ids))}
function syncHearts(){const ids=getFavs();document.querySelectorAll('[data-favorite]').forEach(h=>{const on=ids.includes(Number(h.dataset.favorite));h.classList.toggle('active',on);h.textContent=on?'♥':'♡'})}
document.addEventListener('click',e=>{const h=e.target.closest('[data-favorite]');if(!h)return;e.preventDefault();const id=Number(h.dataset.favorite);let ids=getFavs();ids=ids.includes(id)?ids.filter(x=>x!==id):[...ids,id];setFavs(ids);syncHearts()})

function todayISO(){return new Date().toISOString().slice(0,10)}
function calcDays(s,e){if(!s||!e)return 0;const d1=new Date(s),d2=new Date(e);const n=Math.round((d2-d1)/86400000);return n>0?n:0}
let currentSubtotal=0,currentDiscount=0;

function updateBooking(){
  const s=document.getElementById('pickup_date'),e=document.getElementById('return_date');
  if(!s||!e)return;
  const total=document.getElementById('live-total'),submit=document.getElementById('submit-booking'),note=document.getElementById('availability');
  const days=calcDays(s.value,e.value);
  if(!days){if(total)total.textContent='Выберите корректные даты';if(submit)submit.disabled=true;return}
  let extra=0;document.querySelectorAll('input[name="extras"]:checked').forEach(x=>extra+=(window.extraPrices?.[x.value]||0));
  currentSubtotal=(window.bookingPrice||0)*days+extra; currentDiscount=0;
  if(total)total.textContent=currentSubtotal.toLocaleString('ru-RU')+' ₸';
  if(window.bookingCarId){fetch(`/api/check-availability?car_id=${window.bookingCarId}&start=${s.value}&end=${e.value}`).then(r=>r.json()).then(x=>{if(note){note.textContent=x.available?'✓ Автомобиль свободен на выбранные даты':'✕ Автомобиль уже занят на часть выбранного периода';note.className='availability-note '+(x.available?'ok':'no')}if(submit)submit.disabled=!x.available})}
}

document.addEventListener('change',e=>{if(['pickup_date','return_date'].includes(e.target.id)||e.target.name==='extras')updateBooking()})

function checkDetail(){const s=document.getElementById('detail-pickup'),e=document.getElementById('detail-return'),n=document.getElementById('detail-availability'),a=document.getElementById('book-link');if(!s||!e||!s.value||!e.value)return;const days=calcDays(s.value,e.value);if(!days){n.textContent='Выберите дату возврата позже даты получения';n.className='availability-note no';a.classList.add('disabled');return}fetch(`/api/check-availability?car_id=${window.detailCarId}&start=${s.value}&end=${e.value}`).then(r=>r.json()).then(x=>{n.textContent=x.available?'✓ Свободен на выбранные даты':'✕ На эти даты автомобиль занят';n.className='availability-note '+(x.available?'ok':'no');a.classList.toggle('disabled',!x.available);a.href=x.available?`/booking/${window.detailCarId}?pickup=${s.value}&return=${e.value}`:'#'})}
document.addEventListener('change',e=>{if(['detail-pickup','detail-return'].includes(e.target.id))checkDetail()})

async function applyPromo(){const input=document.getElementById('promo-code'),out=document.getElementById('promo-result'),total=document.getElementById('live-total');if(!input||!out)return;if(!currentSubtotal){out.textContent='Сначала выберите даты';out.className='availability-note no';return}const code=input.value.trim();if(!code){out.textContent='Введите промокод';out.className='availability-note no';return}const r=await fetch(`/api/promo?code=${encodeURIComponent(code)}&amount=${currentSubtotal}`);const x=await r.json();if(x.valid){currentDiscount=x.discount;out.textContent=`✓ Промокод применён: ${x.label}`;out.className='availability-note ok';if(total)total.textContent=(currentSubtotal-currentDiscount).toLocaleString('ru-RU')+' ₸'}else{currentDiscount=0;out.textContent='Промокод не найден или истёк';out.className='availability-note no';if(total)total.textContent=currentSubtotal.toLocaleString('ru-RU')+' ₸'}}

async function checkAdminBooking(){const car=document.getElementById('admin-car-id'),s=document.getElementById('admin-pickup'),e=document.getElementById('admin-return'),note=document.getElementById('admin-availability'),submit=document.getElementById('admin-submit'),total=document.getElementById('admin-total');if(!car||!s||!e||!s.value||!e.value)return;const days=calcDays(s.value,e.value);if(!days){note.textContent='Дата возврата должна быть позже';note.className='availability-note no';submit.disabled=true;return}const opt=car.options[car.selectedIndex];if(total&&!total.dataset.manual)total.value=(Number(opt.dataset.price||0)*days);const r=await fetch(`/api/check-availability?car_id=${car.value}&start=${s.value}&end=${e.value}`);const x=await r.json();note.textContent=x.available?'✓ Автомобиль свободен':'✕ На эти даты автомобиль уже занят';note.className='availability-note '+(x.available?'ok':'no');submit.disabled=!x.available}

function initGallery(){const tabs=document.getElementById('gallery-tabs'),label=document.getElementById('gallery-label');if(!tabs)return;tabs.addEventListener('click',e=>{const b=e.target.closest('[data-gallery]');if(!b)return;tabs.querySelectorAll('button').forEach(x=>x.classList.remove('active'));b.classList.add('active');if(label)label.textContent=b.dataset.gallery})}

function initSortButton(){document.querySelectorAll('.mobile-filter-sticky button').forEach(btn=>{if(btn.textContent.includes('Сортировка'))btn.addEventListener('click',()=>{const s=document.querySelector('.sort-form select');if(s){s.focus();s.click()}})})}

document.addEventListener('DOMContentLoaded',()=>{
  syncHearts();
  const grid=document.getElementById('favorites-grid');if(grid){const ids=getFavs();grid.querySelectorAll('.favorite-server-card').forEach(x=>{if(!ids.includes(Number(x.dataset.id)))x.remove()});if(!grid.children.length)grid.innerHTML='<div class="empty empty-pro"><b>Избранное пока пусто</b><p>Нажмите ♡ на карточке автомобиля, чтобы сохранить его.</p><a class="btn btn-dark" href="/catalog">Перейти в каталог</a></div>'}
  const today=todayISO();document.querySelectorAll('input[type=date]').forEach(i=>{if(!i.min)i.min=today});
  const q=new URLSearchParams(location.search);if(q.get('focus')==='search'){const el=document.querySelector('input[name="q"]');if(el)el.focus()}
  const promoBtn=document.getElementById('apply-promo');if(promoBtn)promoBtn.addEventListener('click',applyPromo);
  if(document.getElementById('pickup_date'))updateBooking();
  ['admin-car-id','admin-pickup','admin-return'].forEach(id=>document.getElementById(id)?.addEventListener('change',checkAdminBooking));
  document.getElementById('admin-total')?.addEventListener('input',e=>e.target.dataset.manual='1');
  initGallery();initSortButton();
});
