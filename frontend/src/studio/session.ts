const key='forge3d.studio.selection.v1';
export function readSession():Record<string,string>{try{return JSON.parse(sessionStorage.getItem(key)||'{}');}catch{return {};}}
export function saveSession(value:Record<string,string>){try{sessionStorage.setItem(key,JSON.stringify(value));}catch{/* Storage may be disabled; current tab remains usable. */}}
