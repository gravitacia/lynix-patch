#![no_std]
use core::{
    alloc::{GlobalAlloc, Layout},
    ffi::c_void,
};
#[link(name = "kernel32")]
extern "system" {
    fn GetProcessHeap() -> *mut c_void;
    fn HeapAlloc(heap: *mut c_void, flags: u32, size: usize) -> *mut c_void;
    fn HeapFree(heap: *mut c_void, flags: u32, memory: *mut c_void) -> i32;
    fn TerminateProcess(process: *mut c_void, code: u32) -> i32;
}
struct Heap;
unsafe impl GlobalAlloc for Heap {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let Some(size) = layout
            .size()
            .checked_add(layout.align())
            .and_then(|n| n.checked_add(8))
        else {
            return core::ptr::null_mut();
        };
        let raw = HeapAlloc(GetProcessHeap(), 0, size) as *mut u8;
        if raw.is_null() {
            return raw;
        }
        let aligned = ((raw as usize + 8 + layout.align() - 1) & !(layout.align() - 1)) as *mut u8;
        (aligned.sub(8) as *mut *mut u8).write(raw);
        aligned
    }
    unsafe fn dealloc(&self, ptr: *mut u8, _: Layout) {
        HeapFree(GetProcessHeap(), 0, (ptr.sub(8) as *mut *mut c_void).read());
    }
}
#[global_allocator]
static ALLOC: Heap = Heap;
#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    unsafe {
        TerminateProcess(-1isize as *mut c_void, 0xc0000409);
    }
    loop {
        core::hint::spin_loop()
    }
}
#[no_mangle]
pub extern "system" fn DllMain(_: *mut c_void, _: u32, _: *mut c_void) -> i32 {
    1
}
#[no_mangle]
pub unsafe extern "system" fn RtlGetCompressionWorkSpaceSize(
    format: u16,
    compress: *mut u32,
    decompress: *mut u32,
) -> u32 {
    if compress.is_null() || decompress.is_null() {
        return 0xc000000d;
    }
    if format & 255 != 4 {
        return 0xc000025f;
    }
    compress.write(1);
    decompress.write(1);
    0
}
#[no_mangle]
pub unsafe extern "system" fn RtlDecompressBufferEx(
    format: u16,
    out: *mut u8,
    out_size: u32,
    input: *const u8,
    input_size: u32,
    final_size: *mut u32,
    _workspace: *mut c_void,
) -> u32 {
    if format & 255 != 4 {
        return 0xc000025f;
    }
    if out.is_null() || input.is_null() || final_size.is_null() {
        return 0xc000000d;
    }
    final_size.write(0);
    match ms_compress::decompress_xpress_huffman_buffer(
        core::slice::from_raw_parts(input, input_size as usize),
        core::slice::from_raw_parts_mut(out, out_size as usize),
    ) {
        Ok(n) => {
            final_size.write(n as u32);
            0
        }
        Err(_) => 0xc0000242,
    }
}
#[no_mangle]
pub static _fltused: i32 = 0;
#[link(name = "msvcrt")]
extern "C" {}
#[link(name = "ntdll")]
extern "C" {}
