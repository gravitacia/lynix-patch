/* Verify the downloaded Cabinet DLL and the open-source XPRESS helper together. */
typedef unsigned long DWORD;
typedef unsigned long long SIZE;
__declspec(dllimport) void* __stdcall LoadLibraryA(const char*);
__declspec(dllimport) void* __stdcall GetProcAddress(void*,const char*);
__declspec(dllimport) void __stdcall ExitProcess(DWORD);
void mainCRTStartup(void) {
    void* library = LoadLibraryA("cabinet-test.dll");
    if (!library) ExitProcess(20);
    typedef int (__stdcall *Create)(DWORD,void*,void**);
    typedef int (__stdcall *Decompress)(void*,const void*,SIZE,void*,SIZE,SIZE*);
    typedef int (__stdcall *Close)(void*);
    Create create = (Create)GetProcAddress(library,"CreateDecompressor");
    Decompress decompress = (Decompress)GetProcAddress(library,"Decompress");
    Close close = (Close)GetProcAddress(library,"CloseDecompressor");
    if (!create || !decompress || !close) ExitProcess(21);
    void* decoder = 0;
    if (!create(0x20000004,0,&decoder)) ExitProcess(22);
    unsigned char input[260] = {0}, output[4] = {0};
    input[32]=16;input[33]=1;input[257]=96;
    SIZE size=0;
    if (!decompress(decoder,input,260,output,4,&size)) ExitProcess(23);
    if (size!=4 || output[0]!='A' || output[1]!='B' || output[2]!='B' || output[3]!='A') ExitProcess(24);
    if (!close(decoder)) ExitProcess(25);
    ExitProcess(0);
}
