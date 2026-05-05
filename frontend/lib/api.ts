const raw = process.env.NEXT_PUBLIC_API_BASE_URL || process.env.API_BASE_URL || '';
export const API_BASE_URL = raw.replace(/\/+$/, '');
if (process.env.NODE_ENV === 'production' && !API_BASE_URL) throw new Error('NEXT_PUBLIC_API_BASE_URL is required in production');
export async function apiFetch(path:string, init?:RequestInit){const url=`${API_BASE_URL}${path}`; const res=await fetch(url,{...init,headers:{'Content-Type':'application/json',...(init?.headers||{})}}); if(!res.ok){throw new Error(`${url} -> ${res.status}`)} return res.json();}
