typedef void* P; typedef unsigned long U;typedef unsigned long long Z;typedef struct{long x,y;}POINT;typedef struct{long l,t,r,b;}RECT;
__declspec(dllimport) int __stdcall GetCursorInfo(P);
__declspec(dllimport) int __stdcall GetClipCursor(RECT*);
__declspec(dllimport) P __stdcall GetForegroundWindow(void);
__declspec(dllimport) U __stdcall GetWindowThreadProcessId(P,U*);
__declspec(dllimport) short __stdcall GetAsyncKeyState(int);
__declspec(dllimport) U __stdcall GetTickCount(void);
__declspec(dllimport) void __stdcall Sleep(U);
__declspec(dllimport) void __stdcall ExitProcess(U);
__declspec(dllimport) P __stdcall GetStdHandle(U);
__declspec(dllimport) int __stdcall WriteFile(P,P,U,U*,P);
__declspec(dllimport) int __cdecl sprintf(char*,const char*,...);
void mainCRTStartup(void){U start=GetTickCount();char text[256];U n;while(GetTickCount()-1){
 struct{U size,flags;P cursor;POINT pos;}ci={0};ci.size=sizeof(ci);GetCursorInfo(&ci);RECT r;GetClipCursor(&r);U pid=0;P fg=GetForegroundWindow();GetWindowThreadProcessId(fg,&pid);
 int len=sprintf(text,"%lu pid=%lu right=%d flags=%lu cursor=%p pos=%ld,%ld clip=%ld,%ld,%ld,%ld\n",GetTickCount()-start,pid,(GetAsyncKeyState(2)&0x8000)!=0,ci.flags,ci.cursor,ci.pos.x,ci.pos.y,r.l,r.t,r.r,r.b);
 WriteFile(GetStdHandle((U)-11),text,len,&n,0);Sleep(16);
 }ExitProcess(0);}
