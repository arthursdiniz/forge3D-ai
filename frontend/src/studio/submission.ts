/** One user intent survives a lost HTTP response; a successful action permits a new run. */
export class SubmissionGuard {
  private active=false;
  private previous:{signature:string;key:string}|null=null;
  constructor(private createKey:()=>string=()=>crypto.randomUUID()){}
  start(signature:string):string|null{
    if(this.active)return null;
    this.active=true;
    if(this.previous?.signature!==signature)this.previous={signature,key:this.createKey()};
    return this.previous.key;
  }
  finish(success:boolean){this.active=false;if(success)this.previous=null;}
}
const files=new WeakMap<File,string>();
export function fileToken(file:File){let token=files.get(file);if(!token){token=crypto.randomUUID();files.set(file,token);}return token;}
