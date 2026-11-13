typedef unsigned long DWORD;
typedef unsigned long long SIZE;
__declspec(dllimport) void* __stdcall LoadLibraryA(const char*);
__declspec(dllimport) void* __stdcall GetProcAddress(void*,const char*);
__declspec(dllimport) void __stdcall ExitProcess(DWORD);
void mainCRTStartup(void) {
 void* lib=LoadLibraryA("lynrtl.dll"); if(!lib) ExitProcess(10);
 typedef DWORD (__stdcall *Work)(unsigned short,DWORD*,DWORD*);
 typedef DWORD (__stdcall *Dec)(unsigned short,unsigned char*,DWORD,const unsigned char*,DWORD,DWORD*,void*);
 Work w=(Work)GetProcAddress(lib,"RtlGetCompressionWorkSpaceSize");
 Dec d=(Dec)GetProcAddress(lib,"RtlDecompressBufferEx");
 if(!w||!d) ExitProcess(11);
 DWORD a=0,b=0,n=0;
 if(w(4,&a,&b)||!a||!b) ExitProcess(12);
 unsigned char in[260]={0},out[4]={0};
 in[32]=16; in[33]=1; in[257]=96;
 if(d(4,out,4,in,260,&n,0)||n!=4) ExitProcess(13);
 if(out[0]!='A'||out[1]!='B'||out[2]!='B'||out[3]!='A') ExitProcess(14);
 if(d(4,out,4,in,2,&n,0)==0) ExitProcess(15);
 ExitProcess(0);
}
