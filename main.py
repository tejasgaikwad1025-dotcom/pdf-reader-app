"""
Book Reader - Crash-proof version for Android
- No RoundedRectangle (causes crashes)
- No PIL/Pillow
- Simple canvas only
"""
 
import fitz
import os
import json
 
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.image import Image as KivyImage
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
 
# ── Storage ───────────────────────────────────────────────────
def get_data_dir():
    for path in ["/sdcard/BookReader", os.path.expanduser("~/BookReader")]:
        try:
            os.makedirs(path, exist_ok=True)
            return path
        except:
            continue
    return "."
 
DATA_DIR  = get_data_dir()
SAVE_FILE = os.path.join(DATA_DIR, "library.json")
 
def load_lib():
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE) as f:
                return json.load(f)
    except:
        pass
    return {}
 
def save_lib(data):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
    except:
        pass
 
# ── Global state ──────────────────────────────────────────────
library   = load_lib()
cur_path  = None
cur_page  = 0
tot_pages = 0
theme     = "warm"
 
THEMES = {
    "warm":  {"bg":(0.98,0.95,0.90,1), "bar":(0.22,0.13,0.07,1),
              "btn":(0.80,0.38,0.10,1), "txt":(1,1,1,1),
              "lbl":(0.15,0.10,0.05,1), "card":(1,0.97,0.92,1)},
    "dark":  {"bg":(0.11,0.11,0.13,1), "bar":(0.07,0.07,0.09,1),
              "btn":(0.95,0.60,0.18,1), "txt":(1,1,1,1),
              "lbl":(0.88,0.86,0.82,1), "card":(0.18,0.18,0.22,1)},
    "sepia": {"bg":(0.93,0.86,0.72,1), "bar":(0.35,0.21,0.09,1),
              "btn":(0.60,0.28,0.05,1), "txt":(1,0.95,0.85,1),
              "lbl":(0.27,0.16,0.05,1), "card":(0.97,0.90,0.77,1)},
}
 
def C(key):
    return THEMES[theme][key]
 
def bg_rect(widget, color_key):
    with widget.canvas.before:
        col  = Color(*C(color_key))
        rect = Rectangle(size=widget.size, pos=widget.pos)
    def update(w, *_):
        col.rgba  = C(color_key)
        rect.size = w.size
        rect.pos  = w.pos
    widget.bind(size=update, pos=update)
 
def make_btn(text, bg=None, **kw):
    return Button(
        text=text,
        background_normal="",
        background_color=bg or C("btn"),
        color=C("txt"),
        **kw
    )
 
def render_page(path, page_num, zoom=1.0):
    doc  = fitz.open(path)
    page = doc[page_num]
    mat  = fitz.Matrix(2.0 * zoom, 2.0 * zoom)
    pix  = page.get_pixmap(matrix=mat, alpha=False)
    tex  = Texture.create(size=(pix.width, pix.height), colorfmt="rgb")
    tex.blit_buffer(pix.samples, colorfmt="rgb", bufferfmt="ubyte")
    tex.flip_vertical()
    doc.close()
    return tex, pix.width, pix.height
 
def book_title(path):
    return os.path.splitext(os.path.basename(path))[0]
 
 
# ══════════════════════════════════════════════════════════════
# Library Screen
# ══════════════════════════════════════════════════════════════
class LibraryScreen(Screen):
 
    def on_enter(self):
        self._build()
 
    def _build(self):
        self.clear_widgets()
        root = BoxLayout(orientation="vertical")
        bg_rect(root, "bg")
 
        # Header
        hdr = BoxLayout(size_hint=(1, None), height=65, padding=8, spacing=8)
        bg_rect(hdr, "bar")
        title = Label(text="Book Reader", font_size="22sp", bold=True,
                      color=C("txt"), size_hint=(1,1),
                      halign="left", valign="middle")
        title.bind(size=title.setter("text_size"))
        hdr.add_widget(title)
        th_labels = {"warm":"Dark", "dark":"Sepia", "sepia":"Light"}
        th_btn = make_btn(th_labels[theme], font_size="14sp",
                          size_hint=(None,1), width=80)
        th_btn.bind(on_press=self._cycle_theme)
        hdr.add_widget(th_btn)
        root.add_widget(hdr)
 
        # Book list
        scroll = ScrollView(size_hint=(1,1))
        self.grid = GridLayout(cols=1, spacing=4, padding=8,
                               size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        scroll.add_widget(self.grid)
        root.add_widget(scroll)
 
        # Bottom bar
        bot = BoxLayout(size_hint=(1, None), height=60, padding=8)
        bg_rect(bot, "bar")
        add_btn = make_btn("+ Add Book", font_size="17sp")
        add_btn.bind(on_press=self._pick_file)
        bot.add_widget(add_btn)
        root.add_widget(bot)
 
        self.add_widget(root)
        self._fill_grid()
 
    def _fill_grid(self):
        self.grid.clear_widgets()
        if not library:
            lbl = Label(
                text="No books yet. Tap + Add Book to open a PDF.",
                font_size="15sp", color=C("lbl"),
                size_hint=(1, None), height=80,
                halign="center")
            lbl.bind(size=lbl.setter("text_size"))
            self.grid.add_widget(lbl)
            return
        for path, info in list(library.items()):
            self.grid.add_widget(self._make_row(path, info))
 
    def _make_row(self, path, info):
        row = BoxLayout(size_hint=(1, None), height=75,
                        padding=8, spacing=6)
        bg_rect(row, "card")
 
        icon = Label(text="📖", font_size="28sp",
                     size_hint=(None,1), width=44)
        row.add_widget(icon)
 
        title = info.get("title", book_title(path))
        pg    = info.get("page", 0)
        total = info.get("total", 1)
        pct   = int(pg / max(total-1,1) * 100)
 
        info_col = BoxLayout(orientation="vertical", size_hint=(1,1))
        t = Label(text=title, font_size="15sp", bold=True,
                  color=C("lbl"), halign="left", valign="bottom",
                  size_hint=(1,None), height=34, shorten=True)
        t.bind(size=t.setter("text_size"))
        p = Label(text=f"Page {pg+1}/{total}  {pct}% read",
                  font_size="12sp", color=C("btn"),
                  halign="left", size_hint=(1,None), height=24)
        p.bind(size=p.setter("text_size"))
        info_col.add_widget(t)
        info_col.add_widget(p)
        row.add_widget(info_col)
 
        read_btn = make_btn("Read", font_size="14sp",
                            size_hint=(None,1), width=65)
        read_btn.bind(on_press=lambda *_: self._open(path))
        row.add_widget(read_btn)
 
        del_btn = make_btn("X", bg=(0.75,0.18,0.18,1),
                           font_size="14sp", size_hint=(None,1), width=38)
        del_btn.bind(on_press=lambda *_: self._delete(path))
        row.add_widget(del_btn)
 
        return row
 
    def _open(self, path):
        global cur_path, cur_page, tot_pages
        if not os.path.exists(path):
            Popup(title="Error",
                  content=Label(text="File not found:\n"+path),
                  size_hint=(.8,.35)).open()
            return
        cur_path = path
        cur_page = library.get(path, {}).get("page", 0)
        try:
            doc = fitz.open(path)
            tot_pages = len(doc)
            doc.close()
        except Exception as e:
            Popup(title="Error",
                  content=Label(text=f"Cannot open:\n{e}"),
                  size_hint=(.8,.35)).open()
            return
        self.manager.current = "reader"
 
    def _delete(self, path):
        library.pop(path, None)
        save_lib(library)
        self._build()
 
    def _pick_file(self, *_):
        content = BoxLayout(orientation="vertical", spacing=6, padding=6)
        start = "/sdcard" if os.path.exists("/sdcard") else \
                os.path.expanduser("~")
        fc = FileChooserListView(filters=["*.pdf"], path=start)
        content.add_widget(fc)
        btns = BoxLayout(size_hint=(1,None), height=48, spacing=6)
        ok  = make_btn("Open")
        can = make_btn("Cancel", bg=(0.4,0.4,0.4,1))
        btns.add_widget(ok)
        btns.add_widget(can)
        content.add_widget(btns)
        popup = Popup(title="Select PDF", content=content,
                      size_hint=(.95,.92))
 
        def do_open(*_):
            if not fc.selection:
                return
            path = fc.selection[0]
            try:
                doc   = fitz.open(path)
                total = len(doc)
                doc.close()
            except Exception as e:
                popup.dismiss()
                Popup(title="Error",
                      content=Label(text=str(e)),
                      size_hint=(.8,.3)).open()
                return
            library[path] = {"title":book_title(path),
                             "page":0, "total":total}
            save_lib(library)
            popup.dismiss()
            self._build()
            self._open(path)
 
        ok.bind(on_press=do_open)
        can.bind(on_press=popup.dismiss)
        popup.open()
 
    def _cycle_theme(self, *_):
        global theme
        theme = {"warm":"dark","dark":"sepia","sepia":"warm"}[theme]
        self._build()
 
 
# ══════════════════════════════════════════════════════════════
# Reader Screen
# ══════════════════════════════════════════════════════════════
class ReaderScreen(Screen):
    _zoom = 1.0
 
    def on_enter(self):
        self._build()
        Clock.schedule_once(lambda dt: self._load(), 0.15)
 
    def _build(self):
        self.clear_widgets()
        root = BoxLayout(orientation="vertical")
        bg_rect(root, "bg")
 
        # Top bar
        self.top = BoxLayout(size_hint=(1,None), height=56,
                             padding=6, spacing=6)
        bg_rect(self.top, "bar")
        back = make_btn("<", font_size="22sp",
                        size_hint=(None,1), width=50)
        back.bind(on_press=self._go_back)
        self.top.add_widget(back)
        self.title_lbl = Label(text="", font_size="14sp",
                               color=C("txt"), size_hint=(1,1),
                               halign="center", shorten=True)
        self.title_lbl.bind(size=self.title_lbl.setter("text_size"))
        self.top.add_widget(self.title_lbl)
        self.pg_lbl = Label(text="", font_size="13sp",
                            color=C("btn"), size_hint=(None,1), width=80)
        self.top.add_widget(self.pg_lbl)
        root.add_widget(self.top)
 
        # Page view
        self.scroll = ScrollView(size_hint=(1,1))
        self.img = KivyImage(allow_stretch=True, keep_ratio=True,
                             size_hint=(None,None))
        self.scroll.add_widget(self.img)
        root.add_widget(self.scroll)
 
        # Bottom bar
        bot = BoxLayout(size_hint=(1,None), height=64,
                        padding=6, spacing=6)
        bg_rect(bot, "bar")
        prev = make_btn("< Prev", font_size="15sp",
                        size_hint=(None,1), width=90)
        prev.bind(on_press=self._prev)
        bot.add_widget(prev)
 
        zm = BoxLayout(orientation="vertical", size_hint=(1,1))
        zm.add_widget(Label(text="Zoom", font_size="11sp",
                            color=C("txt"), size_hint=(1,None), height=18))
        self.slider = Slider(min=0.5, max=3.0, value=self._zoom)
        self.slider.bind(value=self._zoom_ch)
        zm.add_widget(self.slider)
        bot.add_widget(zm)
 
        nxt = make_btn("Next >", font_size="15sp",
                       size_hint=(None,1), width=90)
        nxt.bind(on_press=self._next)
        bot.add_widget(nxt)
        root.add_widget(bot)
 
        self.add_widget(root)
 
    def _load(self):
        if cur_path is None:
            return
        try:
            tex, w, h = render_page(cur_path, cur_page, self._zoom)
            self.img.texture = tex
            self.img.size    = (w, h)
            self.title_lbl.text = book_title(cur_path)
            self.pg_lbl.text    = f"{cur_page+1}/{tot_pages}"
            self._save()
        except Exception as e:
            self.pg_lbl.text = "Error"
 
    def _save(self):
        if cur_path:
            library[cur_path] = {"title":book_title(cur_path),
                                 "page":cur_page, "total":tot_pages}
            save_lib(library)
 
    def _prev(self, *_):
        global cur_page
        if cur_page > 0:
            cur_page -= 1
            self._load()
 
    def _next(self, *_):
        global cur_page
        if cur_page < tot_pages - 1:
            cur_page += 1
            self._load()
 
    def _zoom_ch(self, s, val):
        self._zoom = val
        Clock.unschedule(self._dl)
        Clock.schedule_once(self._dl, 0.4)
 
    def _dl(self, *_):
        self._load()
 
    def _go_back(self, *_):
        self._save()
        self.manager.current = "library"
 
 
# ══════════════════════════════════════════════════════════════
# App Entry
# ══════════════════════════════════════════════════════════════
class BookReaderApp(App):
    def build(self):
        self.title = "Book Reader"
        Window.clearcolor = C("bg")
        sm = ScreenManager()
        sm.add_widget(LibraryScreen(name="library"))
        sm.add_widget(ReaderScreen(name="reader"))
        return sm
 
if __name__ == "__main__":
    BookReaderApp().run()
 
 
