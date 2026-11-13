#!/usr/bin/env python3
"""Lynix-patch setup entry point; GTK is loaded only for the graphical UI."""
import argparse
import json
import os
from pathlib import Path
import runpy
import sys
import threading
import traceback

from backend import (Cancelled, Installer, Layout, RECOMMENDED, clean_environment,
                     detect_prefix, discover_proton, has_prefix, payload_root,
                     proton_name, read_config, valid_exe, valid_proton)


def support():
    script = Path(sys.argv[2])
    if script.name not in ('roblox-compression.py', 'cursor-visibility.py', 'prepare-proton.py'):
        raise SystemExit('Unknown support helper')
    # The frozen interpreter can run after the setup AppImage has been removed.
    env = clean_environment()
    os.environ.clear();os.environ.update(env)
    sys.argv = [str(script), *sys.argv[3:]]
    runpy.run_path(str(script), run_name='__main__')


def graphical(smoke=None):
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    from gi.repository import Gdk, GLib, Gtk, Pango

    class Window(Gtk.Window):
        def __init__(self):
            super().__init__(title='Lynix-patch')
            self.set_default_size(550, 430)
            self.set_resizable(False)
            self.set_position(Gtk.WindowPosition.CENTER)
            self.layout = Layout.current()
            self.cancel = threading.Event()
            self.installer = Installer(self.layout, progress=self.progress, cancel=self.cancel)
            self.busy = False;self.closing = False;self.complete = False
            self.protons = discover_proton(self.layout)
            config = read_config(self.layout.config/'config')
            self.exe = config.get('EXE_PATH', '')
            if not valid_exe(self.exe):
                guess = self.layout.home/'Downloads/UI.exe'
                self.exe = str(guess) if valid_exe(guess) else ''
            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
            outer.set_border_width(28);self.add(outer)
            top = Gtk.Box(spacing=14)
            icon = Gtk.Image.new_from_file(str(payload_root()/'setup/assets/lynix-patch.svg'))
            icon.set_pixel_size(52)
            # Loading the SVG at its intrinsic size would otherwise expand the form.
            from gi.repository import GdkPixbuf
            icon.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(str(payload_root()/'setup/assets/lynix-patch.svg'),52,52,True))
            top.pack_start(icon,False,False,0)
            title = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
            heading = Gtk.Label(xalign=0);heading.set_markup('<span size="xx-large" weight="bold">Lynix-patch</span>')
            title.pack_start(heading,False,False,0)
            title.pack_start(Gtk.Label(label='Set up Lynx on Linux.',xalign=0),False,False,0)
            top.pack_start(title,True,True,0);outer.pack_start(top,False,False,0)
            self.form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
            outer.pack_start(self.form,False,False,0)
            self.form.pack_start(Gtk.Label(label='Your UI.exe',xalign=0),False,False,0)
            self.exe_button = Gtk.Button(label='Choose UI.exe…')
            self.exe_button.connect('clicked',self.choose_exe)
            self.form.pack_start(self.exe_button,False,False,0)
            self.exe_label = Gtk.Label(xalign=0)
            self.exe_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE);self.exe_label.set_max_width_chars(62)
            self.exe_label.get_style_context().add_class('dim-label')
            self.form.pack_start(self.exe_label,False,False,0)
            proton_title = Gtk.Label(label='Proton',xalign=0);proton_title.set_margin_top(6)
            self.form.pack_start(proton_title,False,False,0)
            row = Gtk.Box(spacing=8)
            self.combo = Gtk.ComboBoxText();self.combo.set_hexpand(True)
            for path in self.protons:
                self.add_proton(path)
            self.combo.connect('changed',self.update)
            row.pack_start(self.combo,True,True,0)
            browse = Gtk.Button(label='Browse…');browse.connect('clicked',self.choose_proton)
            row.pack_start(browse,False,False,0);self.form.pack_start(row,False,False,0)
            self.proton_label = Gtk.Label(xalign=0);self.proton_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            self.proton_label.set_max_width_chars(62);self.proton_label.get_style_context().add_class('dim-label')
            self.form.pack_start(self.proton_label,False,False,0)
            tip = Gtk.Label(label=f'Recommended: {RECOMMENDED}. Other builds are selectable.',xalign=0)
            tip.get_style_context().add_class('dim-label');self.form.pack_start(tip,False,False,0)
            self.status = Gtk.Label(xalign=0);self.status.set_line_wrap(True);self.status.set_max_width_chars(62)
            prefix = detect_prefix(self.layout)
            self.initial_status = 'Existing Lynx installation found. Installed components will be reused.' if has_prefix(prefix) else 'Choose your files, then continue. Setup downloads the required components.'
            self.status.set_text(self.initial_status);outer.pack_start(self.status,False,False,0)
            self.bar = Gtk.ProgressBar();outer.pack_start(self.bar,False,False,0)
            footer = Gtk.Box(spacing=10)
            link = Gtk.LinkButton.new_with_label('https://github.com/synapzis/lynix','Based on the original Lynix')
            link.set_halign(Gtk.Align.START);footer.pack_start(link,False,False,0)
            self.button = Gtk.Button(label='Continue');self.button.get_style_context().add_class('suggested-action')
            self.button.connect('clicked',self.begin);footer.pack_end(self.button,False,False,0)
            outer.pack_start(footer,False,False,0)
            self.connect('delete-event',self.close)
            if self.protons:
                saved = config.get('PROTON_DIR')
                selected = str(Path(saved).resolve()) if saved and valid_proton(saved) else str(self.protons[0])
                self.combo.set_active_id(selected)
            self.update()

        def add_proton(self,path):
            name=proton_name(path)
            if name == RECOMMENDED:name += '  ·  Recommended'
            self.combo.append(str(path),name)

        def update(self,*_):
            self.exe_button.set_label(Path(self.exe).name if self.exe else 'Choose UI.exe…')
            self.exe_label.set_text(self.exe or 'Select your own copy. UI.exe is not included.')
            self.exe_label.set_tooltip_text(self.exe)
            proton=self.combo.get_active_id()
            self.proton_label.set_text(proton or 'No Proton found. Use Browse to select a build.')
            self.proton_label.set_tooltip_text(proton)
            self.button.set_sensitive(bool(valid_exe(self.exe) and proton and valid_proton(proton)))

        def choose_exe(self,*_):
            picker=Gtk.FileChooserNative.new('Choose UI.exe',self,Gtk.FileChooserAction.OPEN,'Select','Cancel')
            filt=Gtk.FileFilter();filt.set_name('Windows executables');filt.add_pattern('*.exe');filt.add_pattern('*.EXE');picker.add_filter(filt)
            all_files=Gtk.FileFilter();all_files.set_name('All files');all_files.add_pattern('*');picker.add_filter(all_files)
            if self.exe:picker.set_filename(self.exe)
            else:picker.set_current_folder(str(self.layout.home/'Downloads'))
            if picker.run()==Gtk.ResponseType.ACCEPT:self.exe=picker.get_filename();self.update()
            picker.destroy()

        def choose_proton(self,*_):
            picker=Gtk.FileChooserNative.new('Choose a Proton folder',self,Gtk.FileChooserAction.SELECT_FOLDER,'Select','Cancel')
            if self.combo.get_active_id():picker.set_current_folder(self.combo.get_active_id())
            if picker.run()==Gtk.ResponseType.ACCEPT:
                path=Path(picker.get_filename()).resolve()
                if valid_proton(path):
                    if path not in self.protons:self.protons.append(path);self.add_proton(path)
                    self.combo.set_active_id(str(path))
                else:self.status.set_text('That folder is not a Proton build. Select the folder containing “proton”.')
            picker.destroy()

        def progress(self,value,text):
            GLib.idle_add(self.show_progress,value,text)

        def show_progress(self,value,text):
            self.bar.set_fraction(max(self.bar.get_fraction(),min(value,1)))
            self.status.set_text(text)
            return False

        def begin(self,*_):
            self.busy=True;self.cancel.clear();self.bar.set_fraction(0)
            self.form.set_sensitive(False);self.button.set_sensitive(False);self.button.set_label('Setting up…')
            exe=self.exe;proton=self.combo.get_active_id()
            def work():
                try:self.installer.install(exe,proton)
                except Exception as exc:
                    self.installer.log.parent.mkdir(parents=True,exist_ok=True)
                    with self.installer.log.open('a') as f:traceback.print_exc(file=f)
                    GLib.idle_add(self.failed,str(exc))
                else:GLib.idle_add(self.finished)
            threading.Thread(target=work,daemon=True).start()

        def failed(self,error):
            self.busy=False
            if self.closing:self.destroy();Gtk.main_quit();return False
            self.form.set_sensitive(True);self.button.set_label('Try again');self.update()
            self.status.set_text(error)
            return False

        def finished(self):
            self.busy=False;self.complete=True
            self.status.set_text('Ready — launching Lynx…');self.bar.set_fraction(1)
            GLib.timeout_add(450,self.exit)
            return False

        def exit(self):
            self.destroy();Gtk.main_quit();return False

        def close(self,*_):
            if self.busy:
                self.closing=True;self.cancel.set();self.status.set_text('Cancelling setup…')
                return True
            Gtk.main_quit();return False

    window=Window();window.show_all()
    if smoke:
        def snapshot():
            pixbuf=Gdk.pixbuf_get_from_window(window.get_window(),0,0,window.get_allocated_width(),window.get_allocated_height())
            pixbuf.savev(str(smoke),'png',[],[])
            print(json.dumps({'title':window.get_title(),'continue_enabled':window.button.get_sensitive(),
                              'proton_count':len(window.protons),'ui_exe':window.exe,'status':window.status.get_text()}))
            window.exit();return False
        GLib.timeout_add(1100,snapshot)
    Gtk.main()
    if window.complete and not window.closing:
        window.installer.launch()
    return 0


def main():
    if len(sys.argv)>2 and sys.argv[1]=='--support':
        support();return 0
    parser=argparse.ArgumentParser(description='Lynix-patch setup')
    parser.add_argument('--check',action='store_true',help='Print installation discovery information')
    parser.add_argument('--install',action='store_true',help='Run setup without the graphical form')
    parser.add_argument('--exe',type=Path)
    parser.add_argument('--proton',type=Path)
    parser.add_argument('--prefix',type=Path)
    parser.add_argument('--no-launch',action='store_true')
    parser.add_argument('--test-root',type=Path,help=argparse.SUPPRESS)
    parser.add_argument('--smoke-test',type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args()
    layout=Layout.isolated(args.test_root) if args.test_root else Layout.current()
    if args.check:
        print(json.dumps({'protons':[{'path':str(p),'name':proton_name(p),'recommended':proton_name(p)==RECOMMENDED} for p in discover_proton(layout)],
                          'prefix':str(detect_prefix(layout)),'config':read_config(layout.config/'config')},indent=2));return 0
    if args.install:
        if not args.exe or not args.proton:parser.error('--install requires --exe and --proton')
        installer=Installer(layout=layout,progress=lambda value,text:print(f'{value:.0%} {text}',flush=True))
        try:installer.install(args.exe,args.proton,args.prefix)
        except (OSError,RuntimeError,ValueError,Cancelled) as exc:print(str(exc),file=sys.stderr);return 1
        if not args.no_launch:installer.launch()
        return 0
    return graphical(args.smoke_test)


if __name__=='__main__':
    raise SystemExit(main())
