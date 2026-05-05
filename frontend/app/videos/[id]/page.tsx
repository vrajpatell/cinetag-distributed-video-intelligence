export default async function Page({params}:{params:Promise<{id:string}>}){const {id}=await params; return <main className='p-6'><h1 className='text-3xl'>Video {id}</h1></main>}
