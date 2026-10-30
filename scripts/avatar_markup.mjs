const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function avatarMarkup(m){
 if(!m.avatar)return '';
 if(m.avatar_kind==='static'||m.avatar_kind==='poses')return m.avatar_cues.map((c,i)=>`<img id="avatar-image-${i}" class="clip avatar" src="${esc(c.image)}" data-start="${c.start}" data-duration="${c.duration}" data-track-index="3" alt="人物形象">`).join('');
 return `<video id="avatar" class="clip avatar" src="media/avatar.mp4" data-start="0" data-duration="${m.duration}" data-track-index="3" muted playsinline></video>`;
}
