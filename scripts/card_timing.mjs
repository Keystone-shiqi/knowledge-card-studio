export function cardTimes(scene,cards){
 const at=scene.card_at??cards.map((_,i)=>.3+i*Math.max(0,scene.duration-1.2)/cards.length);
 if(!Array.isArray(at)||at.length!==cards.length||at.some((v,i)=>!Number.isFinite(v)||v<0||v>scene.duration-.4||(i>0&&v<=at[i-1])))throw Error('Invalid card_at in scene '+scene.index);
 return at;
}
