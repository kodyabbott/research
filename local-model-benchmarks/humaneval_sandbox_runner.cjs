'use strict';
const fs = require('fs');
const {getQuickJS} = require('./state/coding-sandbox/node_modules/quickjs-emscripten');
(async()=>{
 const input=JSON.parse(fs.readFileSync(0,'utf8'));
 const Q=await getQuickJS();const rows=[];
 for(const task of input.tasks){
  const runtime=Q.newRuntime();runtime.setMemoryLimit(64*1024*1024);runtime.setMaxStackSize(512*1024);
  const deadline=Date.now()+Math.min(input.timeoutMs||2000,5000);runtime.setInterruptHandler(()=>Date.now()>deadline);
  const vm=runtime.newContext();let keeper,stats;
  let row={id:task.id,passed:false};
  try{
   const bootstrap=vm.evalCode(`(()=>{let count=0,failed=0,seed=42;Object.defineProperty(Math,'random',{value:()=>{seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;return (seed>>>0)/4294967296;},writable:false,configurable:false});const c=Object.freeze({assert(v){count++;if(!v)failed++;},log(){},error(){}});Object.defineProperty(globalThis,'console',{value:c,writable:false,configurable:false});return ()=>({count,failed});})()`);
   if(bootstrap.error){const e=vm.dump(bootstrap.error);bootstrap.error.dispose();throw Error(JSON.stringify(e));}
   keeper=bootstrap.value;
   for(const [phase,code] of [['candidate',task.code],['tests',task.test]]){
    const evaluated=vm.evalCode(code,phase+'.js');
    if(evaluated.error){row.error=vm.dump(evaluated.error);row.phase=phase;evaluated.error.dispose();break;}
    evaluated.value.dispose();
   }
   const called=vm.callFunction(keeper,vm.undefined);
   if(called.error){row.error=vm.dump(called.error);called.error.dispose();}
   else{stats=called.value;Object.assign(row,vm.dump(stats));}
   row.passed=!row.error&&row.count>0&&row.failed===0;
  }catch(e){row.error=String(e);}
  finally{if(stats)stats.dispose();if(keeper)keeper.dispose();vm.dispose();runtime.dispose();}
  rows.push(row);
 }
 process.stdout.write(JSON.stringify({rows}));
})().catch(e=>{process.stderr.write(String(e));process.exitCode=1;});
