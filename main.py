"""
Book Reader - A Google Play Books style PDF reader
Features: Library, auto-save position, dark/sepia/light modes, zoom
"""
 
import fitz  # PyMuPDF
import os
import json
 
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.image import Image as KivyImage
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import get_color_from_hex
from kivy.storage.jsonstore import JsonStore
 
# ── App Data Directory ────────────────────────────────────────
def get_data_dir():
    if os.path.exists("/sdcard"):
        d = "/sdcard/BookReader"
    else:
        d = os.path.expanduser("~/BookReader")
    os.makedirs(d, exist_ok=True)
    return d
 
DATA_DIR = get_data_dir()
STORE_PATH = os.path.join(DATA_DIR, "library.json")
 
def load_library():
    if os.path.exists(STORE_PATH):
        try:
            with open(STORE_PATH, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}
 
def save_library(data):
    try:
        with open(STORE_PATH, "w") as f:
            json.dump(data, f)
    except:
        pass
 
# ── Global State ──────────────────────────────────────────────
library = load_library()   # {path: {page, total, title}}
current_pdf_path = None
current_page = 0
total_pages = 0
read_mode = "light"        # light | dark | sepia
 
THEMES = {
    "light": {
        "bg":      (0.97, 0.95, 0.90, 1),
        "page_bg": (1.00, 0.98, 0.94, 1),
        "bar_bg":  (0.20, 0.13, 0.08, 1),
        "text":    (0.15, 0.10, 0.05, 1),
        "accent":  (0.75, 0.35, 0.10, 1),
        "btn":     (0.75, 0.35, 0.10, 1),
        "btn_txt": (1.00, 1.00, 1.00, 1),
        "card":    (1.00, 0.97, 0.92, 1),
    },
    "dark": {
        "bg":      (0.10, 0.10, 0.12, 1),
        "page_bg": (0.12, 0.12, 0.15, 1),
        "bar_bg":  (0.07, 0.07, 0.09, 1),
        "text":    (0.90, 0.88, 0.85, 1),
        "accent":  (0.95, 0.60, 0.20, 1),
        "btn":     (0.95, 0.60, 0.20, 1),
        "btn_txt": (0.10, 0.10, 0.12, 1),
        "card":    (0.18, 0.18, 0.22, 1),
    },
    "sepia": {
        "bg":      (0.94, 0.87, 0.73, 1),
        "page_bg": (0.97, 0.91, 0.78, 1),
        "bar_bg":  (0.35, 0.22, 0.10, 1),
        "text":    (0.28, 0.17, 0.06, 1),
        "accent":  (0.60, 0.30, 0.05, 1),
        "btn":     (0.60, 0.30, 0.05, 1),
        "btn_txt": (1.00, 0.96, 0.88, 1),
        "card":    (0.97, 0.91, 0.78, 1),
    },
}
 
def T(key):
    return THEMES[read_mode][key]
 
 
# ── Helpers ───────────────────────────────────────────────────
def render_page(path, page_num, scale=1.0):
    doc  = fitz.open(path)
    page = doc[page_num]
    mat  = fitz.Matrix(2.0 * scale, 2.0 * scale)
    pix  = page.get_pixmap(matrix=mat, alpha=False)
    tex  = Texture.create(size=(pix.width, pix.height), colorfmt="rgb")
    tex.blit_buffer(pix.samples, colorfmt="rgb", bufferfmt="ubyte")
    tex.flip_vertical()
    doc.close()
    return tex, pix.width, pix.height
 
def get_book_title(path):
    return os.path.splitext(os.path.basename(path))[0]
 
def styled_btn(text, bg=None, fg=None, font_size="16sp", **kwargs):
    btn = Button(
        text=text,
        font_size=font_size,
        background_normal="",
        background_color=bg or T("btn"),
        color=fg or T("btn_txt"),
        **kwargs
    )
    return btn
 
 
# ── Library Screen ────────────────────────────────────────────
class LibraryScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()
 
    def _build(self):
        self.clear_widgets()
        root = BoxLayout(orientation="vertical")
 
        # Background
        with root.canvas.before:
            Color(*T("bg"))
            self._bg = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=lambda w,v: setattr(self._bg,"size",v),
                  pos =lambda w,v: setattr(self._bg,"pos", v))
 
        # ── Header ──
        header = BoxLayout(size_hint=(1, None), height=dp(70), padding=dp(12), spacing=dp(8))
        with header.canvas.before:
            Color(*T("bar_bg"))
            self._hbg = Rectangle(size=header.size, pos=header.pos)
        header.bind(size=lambda w,v: setattr(self._hbg,"size",v),
                    pos =lambda w,v: setattr(self._hbg,"pos", v))
 
        # Book icon + title
        icon_lbl = Label(text="📚", font_size="28sp", size_hint=(None,1), width=dp(44))
        title_lbl = Label(text="Book Reader", font_size="22sp", bold=True,
                          color=T("btn_txt"), halign="left", valign="middle",
                          size_hint=(1,1))
        title_lbl.bind(size=title_lbl.setter("text_size"))
        header.add_widget(icon_lbl)
        header.add_widget(title_lbl)
 
        # Theme toggle
        self.theme_btn = styled_btn("🌙", bg=T("accent"), font_size="20sp",
                                    size_hint=(None,1), width=dp(50))
        self.theme_btn.bind(on_press=self.cycle_theme)
        header.add_widget(self.theme_btn)
 
        root.add_widget(header)
 
        # ── Book Grid ──
        scroll = ScrollView(size_hint=(1,1))
        self.grid = GridLayout(cols=2, spacing=dp(12), padding=dp(12),
                               size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        scroll.add_widget(self.grid)
        root.add_widget(scroll)
 
        # ── Bottom Bar ──
        bot = BoxLayout(size_hint=(1, None), height=dp(60), padding=dp(10), spacing=dp(10))
        with bot.canvas.before:
            Color(*T("bar_bg"))
            self._bbg = Rectangle(size=bot.size, pos=bot.pos)
        bot.bind(size=lambda w,v: setattr(self._bbg,"size",v),
                 pos =lambda w,v: setattr(self._bbg,"pos", v))
 
        add_btn = styled_btn("+ Add Book", bg=T("accent"), font_size="17sp")
        add_btn.bind(on_press=self.open_file_chooser)
        bot.add_widget(add_btn)
        root.add_widget(bot)
 
        self.add_widget(root)
        self._populate_grid()
 
    def _populate_grid(self):
        self.grid.clear_widgets()
        if not library:
            lbl = Label(text="No books yet.\nTap '+ Add Book' to get started!",
                        font_size="16sp", color=T("text"),
                        halign="center", size_hint=(1, None), height=dp(120))
            lbl.bind(size=lbl.setter("text_size"))
            self.grid.add_widget(lbl)
            return
 
        for path, info in library.items():
            self.grid.add_widget(self._make_card(path, info))
 
    def _make_card(self, path, info):
        card = BoxLayout(orientation="vertical", size_hint=(1, None),
                         height=dp(160), padding=dp(8), spacing=dp(4))
        with card.canvas.before:
            Color(*T("card"))
            RoundedRectangle(size=card.size, pos=card.pos, radius=[dp(10)])
 
        # Book cover placeholder
        cover = BoxLayout(size_hint=(1, None), height=dp(90))
        with cover.canvas.before:
            Color(*T("accent"))
            RoundedRectangle(size=cover.size, pos=cover.pos, radius=[dp(8)])
        cover_lbl = Label(text="📖", font_size="36sp")
        cover.add_widget(cover_lbl)
        card.add_widget(cover)
 
        title = info.get("title", get_book_title(path))
        pg    = info.get("page", 0)
        total = info.get("total", 1)
        pct   = int((pg / max(total-1, 1)) * 100)
 
        name_lbl = Label(text=title, font_size="12sp", color=T("text"),
                         halign="center", size_hint=(1, None), height=dp(30),
                         text_size=(dp(130), None), shorten=True)
        card.add_widget(name_lbl)
 
        prog_lbl = Label(text=f"Page {pg+1}/{total}  •  {pct}%",
                         font_size="10sp", color=T("accent"),
                         size_hint=(1, None), height=dp(18))
        card.add_widget(prog_lbl)
 
        card.bind(on_touch_down=lambda w, t: self._open_book(path) if w.collide_point(*t.pos) else None)
 
        # Delete button
        del_btn = styled_btn("✕", bg=(0.8,0.2,0.2,1), font_size="12sp",
                             size_hint=(None, None), size=(dp(30), dp(24)),
                             pos_hint={"right":1})
        del_btn.bind(on_press=lambda *_: self._remove_book(path))
        card.add_widget(del_btn)
 
        return card
 
    def _open_book(self, path):
        global current_pdf_path, current_page, total_pages
        if not os.path.exists(path):
            self._show_error(f"File not found:\n{path}")
            return
        current_pdf_path = path
        info = library.get(path, {})
        current_page = info.get("page", 0)
        doc = fitz.open(path)
        total_pages = len(doc)
        doc.close()
        rs = self.manager.get_screen("reader")
        rs.refresh()
        self.manager.transition = SlideTransition(direction="left")
        self.manager.current = "reader"
 
    def _remove_book(self, path):
        if path in library:
            del library[path]
            save_library(library)
            self._build()
 
    def _show_error(self, msg):
        popup = Popup(title="Error",
                      content=Label(text=msg),
                      size_hint=(.8,.4))
        popup.open()
 
    def open_file_chooser(self, *_):
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        start = "/sdcard" if os.path.exists("/sdcard") else os.path.expanduser("~")
        fc = FileChooserListView(filters=["*.pdf"], path=start, size_hint=(1,1))
        content.add_widget(fc)
 
        btn_row = BoxLayout(size_hint=(1, None), height=dp(48), spacing=dp(8))
        sel_btn = styled_btn("Open", bg=T("accent"))
        can_btn = styled_btn("Cancel", bg=(.4,.4,.4,1))
        btn_row.add_widget(sel_btn)
        btn_row.add_widget(can_btn)
        content.add_widget(btn_row)
 
        popup = Popup(title="Choose a PDF", content=content, size_hint=(.95,.92))
 
        def do_open(*_):
            if fc.selection:
                path = fc.selection[0]
                doc = fitz.open(path)
                total = len(doc)
                doc.close()
                library[path] = {
                    "title": get_book_title(path),
                    "page": 0,
                    "total": total
                }
                save_library(library)
                popup.dismiss()
                self._build()
                self._open_book(path)
 
        sel_btn.bind(on_press=do_open)
        can_btn.bind(on_press=popup.dismiss)
        popup.open()
 
    def cycle_theme(self, *_):
        global read_mode
        modes = ["light", "sepia", "dark"]
        idx = modes.index(read_mode)
        read_mode = modes[(idx+1) % 3]
        icons = {"light":"☀️", "sepia":"📜", "dark":"🌙"}
        self._build()
 
    def on_enter(self):
        self._build()
 
 
# ── Reader Screen ─────────────────────────────────────────────
class ReaderScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._zoom = 1.0
        self._ui_visible = True
        self._build()
 
    def _build(self):
        self.clear_widgets()
        root = FloatLayout()
 
        # Page background
        with root.canvas.before:
            Color(*T("page_bg"))
            self._bg = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=lambda w,v: setattr(self._bg,"size",v),
                  pos =lambda w,v: setattr(self._bg,"pos", v))
 
        # Scroll area for page image
        self.scroll = ScrollView(size_hint=(1,1), pos_hint={"x":0,"y":0})
        self.page_img = KivyImage(allow_stretch=True, keep_ratio=True,
                                  size_hint=(None, None))
        self.scroll.add_widget(self.page_img)
        root.add_widget(self.scroll)
 
        # ── Top Bar ──
        self.top_bar = BoxLayout(
            size_hint=(1, None), height=dp(56),
            pos_hint={"x":0,"top":1}, padding=dp(6), spacing=dp(6))
        with self.top_bar.canvas.before:
            Color(*T("bar_bg"))
            self._tbg = Rectangle(size=self.top_bar.size, pos=self.top_bar.pos)
        self.top_bar.bind(
            size=lambda w,v: setattr(self._tbg,"size",v),
            pos =lambda w,v: setattr(self._tbg,"pos", v))
 
        back_btn = styled_btn("←", bg=T("accent"), font_size="22sp",
                              size_hint=(None,1), width=dp(48))
        back_btn.bind(on_press=self._go_home)
        self.top_bar.add_widget(back_btn)
 
        self.title_lbl = Label(text="", font_size="14sp",
                               color=T("btn_txt"), size_hint=(1,1),
                               halign="center", shorten=True)
        self.top_bar.add_widget(self.title_lbl)
 
        self.page_lbl = Label(text="0/0", font_size="13sp",
                              color=T("accent"), size_hint=(None,1),
                              width=dp(70))
        self.top_bar.add_widget(self.page_lbl)
 
        root.add_widget(self.top_bar)
 
        # ── Bottom Bar ──
        self.bot_bar = BoxLayout(
            size_hint=(1, None), height=dp(72),
            pos_hint={"x":0,"y":0}, padding=dp(6), spacing=dp(6))
        with self.bot_bar.canvas.before:
            Color(*T("bar_bg"))
            self._bbg = Rectangle(size=self.bot_bar.size, pos=self.bot_bar.pos)
        self.bot_bar.bind(
            size=lambda w,v: setattr(self._bbg,"size",v),
            pos =lambda w,v: setattr(self._bbg,"pos", v))
 
        prev_btn = styled_btn("◀", bg=T("accent"), font_size="20sp",
                              size_hint=(None,1), width=dp(52))
        prev_btn.bind(on_press=self.prev_page)
        self.bot_bar.add_widget(prev_btn)
 
        zoom_box = BoxLayout(orientation="vertical", size_hint=(1,1))
        zoom_lbl = Label(text="Zoom", font_size="11sp", color=T("btn_txt"),
                         size_hint=(1, None), height=dp(18))
        self.zoom_slider = Slider(min=0.5, max=3.0, value=self._zoom,
                                  size_hint=(1,1))
        self.zoom_slider.bind(value=self._on_zoom)
        zoom_box.add_widget(zoom_lbl)
        zoom_box.add_widget(self.zoom_slider)
        self.bot_bar.add_widget(zoom_box)
 
        next_btn = styled_btn("▶", bg=T("accent"), font_size="20sp",
                              size_hint=(None,1), width=dp(52))
        next_btn.bind(on_press=self.next_page)
        self.bot_bar.add_widget(next_btn)
 
        root.add_widget(self.bot_bar)
 
        # Tap center to toggle UI
        tap_zone = Widget(size_hint=(1,1))
        tap_zone.bind(on_touch_down=self._on_tap)
        root.add_widget(tap_zone)
 
        self.add_widget(root)
 
    def refresh(self):
        self._build()
        self.load_page()
 
    def load_page(self):
        if current_pdf_path is None:
            return
        try:
            tex, w, h = render_page(current_pdf_path, current_page, self._zoom)
            self.page_img.texture = tex
            self.page_img.size = (w, h)
            title = get_book_title(current_pdf_path)
            self.title_lbl.text = title
            self.page_lbl.text  = f"{current_page+1}/{total_pages}"
            self._save_progress()
        except Exception as e:
            self.page_lbl.text = "Error"
 
    def _save_progress(self):
        if current_pdf_path:
            library[current_pdf_path] = {
                "title": get_book_title(current_pdf_path),
                "page":  current_page,
                "total": total_pages,
            }
            save_library(library)
 
    def next_page(self, *_):
        global current_page
        if current_page < total_pages - 1:
            current_page += 1
            self.load_page()
 
    def prev_page(self, *_):
        global current_page
        if current_page > 0:
            current_page -= 1
            self.load_page()
 
    def _on_zoom(self, slider, val):
        self._zoom = val
        Clock.unschedule(self._delayed_render)
        Clock.schedule_once(self._delayed_render, 0.3)
 
    def _delayed_render(self, *_):
        self.load_page()
 
    def _on_tap(self, widget, touch):
        # Only toggle if tap is in center 40% of screen
        cx = Window.width  * 0.3
        cy = Window.height * 0.3
        if cx < touch.x < Window.width - cx:
            self._ui_visible = not self._ui_visible
            self.top_bar.opacity = 1 if self._ui_visible else 0
            self.bot_bar.opacity = 1 if self._ui_visible else 0
 
    def _go_home(self, *_):
        self._save_progress()
        self.manager.transition = SlideTransition(direction="right")
        self.manager.current = "library"
 
    def on_enter(self):
        self.refresh()
 
 
# ── App ───────────────────────────────────────────────────────
class BookReaderApp(App):
    def build(self):
        Window.clearcolor = T("bg")
        sm = ScreenManager()
        sm.add_widget(LibraryScreen(name="library"))
        sm.add_widget(ReaderScreen(name="reader"))
        return sm
 
 
if __name__ == "__main__":
    BookReaderApp().run()
 
