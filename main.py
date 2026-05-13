import fitz  # PyMuPDF
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image as KivyImage
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.graphics import Color, Rectangle
from kivy.uix.widget import Widget
import io
from PIL import Image as PILImage

# ── Global state ──────────────────────────────────────────────
current_pdf_path = None
current_page     = 0
total_pages      = 0
font_scale       = 1.0
dark_mode        = False

BG_DARK   = (0.12, 0.12, 0.12, 1)
BG_LIGHT  = (1,    1,    1,    1)
TXT_DARK  = (1,    1,    1,    1)
TXT_LIGHT = (0.1,  0.1,  0.1,  1)


# ── Helpers ───────────────────────────────────────────────────
def get_bg():  return BG_DARK  if dark_mode else BG_LIGHT
def get_fg():  return TXT_DARK if dark_mode else TXT_LIGHT


def render_page_texture(path, page_num, scale=1.0):
    """Render a PDF page → Kivy Texture."""
    doc  = fitz.open(path)
    page = doc[page_num]
    mat  = fitz.Matrix(2.0 * scale, 2.0 * scale)   # 2× for crisp display
    pix  = page.get_pixmap(matrix=mat, alpha=False)
    img  = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
    buf  = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    tex  = Texture.create(size=(pix.width, pix.height), colorfmt="rgb")
    tex.blit_buffer(pix.samples, colorfmt="rgb", bufferfmt="ubyte")
    tex.flip_vertical()
    doc.close()
    return tex, pix.width, pix.height


# ── Screens ───────────────────────────────────────────────────
class HomeScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build_ui()

    def _build_ui(self):
        self.layout = BoxLayout(orientation="vertical", padding=30, spacing=20)
        self._apply_bg()

        title = Label(text="📖 PDF Reader", font_size="28sp",
                      bold=True, color=get_fg(), size_hint=(1, .2))
        self.layout.add_widget(title)

        open_btn = Button(text="Open PDF", font_size="18sp",
                          size_hint=(.6, .15), pos_hint={"center_x": .5},
                          background_color=(0.2, 0.6, 1, 1), color=(1,1,1,1))
        open_btn.bind(on_press=self.open_file_chooser)
        self.layout.add_widget(open_btn)

        # Dark/Light toggle
        self.theme_btn = Button(
            text="Switch to Dark Mode", font_size="15sp",
            size_hint=(.6, .12), pos_hint={"center_x": .5},
            background_color=(.3,.3,.3,1), color=(1,1,1,1))
        self.theme_btn.bind(on_press=self.toggle_theme)
        self.layout.add_widget(self.theme_btn)

        self.add_widget(self.layout)

    def _apply_bg(self):
        with self.layout.canvas.before:
            Color(*get_bg())
            self._rect = Rectangle(size=self.layout.size, pos=self.layout.pos)
        self.layout.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, *_):
        self._rect.size = self.layout.size
        self._rect.pos  = self.layout.pos

    def toggle_theme(self, *_):
        global dark_mode
        dark_mode = not dark_mode
        self.theme_btn.text = "Switch to Light Mode" if dark_mode else "Switch to Dark Mode"
        # Rebuild reader if already open
        rs = self.manager.get_screen("reader")
        rs.refresh_theme()

    def open_file_chooser(self, *_):
        content = BoxLayout(orientation="vertical")
        fc = FileChooserListView(filters=["*.pdf"], path="/sdcard")
        content.add_widget(fc)

        btn_row = BoxLayout(size_hint=(1, .1))
        select  = Button(text="Open")
        cancel  = Button(text="Cancel")
        btn_row.add_widget(select)
        btn_row.add_widget(cancel)
        content.add_widget(btn_row)

        popup = Popup(title="Choose PDF", content=content,
                      size_hint=(.95, .95))

        def do_select(*_):
            if fc.selection:
                self._load_pdf(fc.selection[0])
                popup.dismiss()

        select.bind(on_press=do_select)
        cancel.bind(on_press=popup.dismiss)
        popup.open()

    def _load_pdf(self, path):
        global current_pdf_path, current_page, total_pages
        current_pdf_path = path
        current_page     = 0
        doc              = fitz.open(path)
        total_pages      = len(doc)
        doc.close()
        rs = self.manager.get_screen("reader")
        rs.load_page()
        self.manager.current = "reader"


class ReaderScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build_ui()

    def _build_ui(self):
        self.root_layout = BoxLayout(orientation="vertical")

        # ── Top bar ──────────────────────────────────────────
        top = BoxLayout(size_hint=(1, .08), padding=4, spacing=6)
        with top.canvas.before:
            Color(.15,.15,.15,1)
            self._top_rect = Rectangle(size=top.size, pos=top.pos)
        top.bind(size=lambda w,v: setattr(self._top_rect,"size",v),
                 pos =lambda w,v: setattr(self._top_rect,"pos", v))

        back_btn = Button(text="←", font_size="20sp", size_hint=(.12,1),
                          background_color=(.2,.2,.2,1), color=(1,1,1,1))
        back_btn.bind(on_press=lambda *_: setattr(self.manager,"current","home"))
        top.add_widget(back_btn)

        self.page_label = Label(text="Page 0 / 0", font_size="14sp",
                                color=(1,1,1,1), size_hint=(.5,1))
        top.add_widget(self.page_label)

        prev_btn = Button(text="◀", font_size="18sp", size_hint=(.12,1),
                          background_color=(.25,.25,.25,1), color=(1,1,1,1))
        prev_btn.bind(on_press=self.prev_page)
        top.add_widget(prev_btn)

        next_btn = Button(text="▶", font_size="18sp", size_hint=(.12,1),
                          background_color=(.25,.25,.25,1), color=(1,1,1,1))
        next_btn.bind(on_press=self.next_page)
        top.add_widget(next_btn)

        self.root_layout.add_widget(top)

        # ── Page display ─────────────────────────────────────
        self.scroll = ScrollView(size_hint=(1, .82))
        self.page_img = KivyImage(allow_stretch=True, keep_ratio=True)
        self.scroll.add_widget(self.page_img)
        self.root_layout.add_widget(self.scroll)

        # ── Bottom bar: font slider ───────────────────────────
        bot = BoxLayout(size_hint=(1, .10), padding=8, spacing=8)
        with bot.canvas.before:
            Color(.15,.15,.15,1)
            self._bot_rect = Rectangle(size=bot.size, pos=bot.pos)
        bot.bind(size=lambda w,v: setattr(self._bot_rect,"size",v),
                 pos =lambda w,v: setattr(self._bot_rect,"pos", v))

        bot.add_widget(Label(text="A-", font_size="14sp",
                             color=(1,1,1,1), size_hint=(.1,1)))
        self.font_slider = Slider(min=0.5, max=2.5, value=1.0, size_hint=(.7,1))
        self.font_slider.bind(value=self.on_font_change)
        bot.add_widget(self.font_slider)
        bot.add_widget(Label(text="A+", font_size="20sp",
                             color=(1,1,1,1), size_hint=(.1,1)))

        self.root_layout.add_widget(bot)
        self.add_widget(self.root_layout)

    def refresh_theme(self):
        pass   # Page background handled by PDF render itself

    def load_page(self):
        if current_pdf_path is None:
            return
        tex, w, h = render_page_texture(
            current_pdf_path, current_page, self.font_slider.value)
        self.page_img.texture = tex
        self.page_img.size    = (w, h)
        self.page_label.text  = f"Page {current_page+1} / {total_pages}"

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

    def on_font_change(self, slider, val):
        global font_scale
        font_scale = val
        self.load_page()


# ── App entry point ───────────────────────────────────────────
class PDFReaderApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(ReaderScreen(name="reader"))
        return sm


if __name__ == "__main__":
    PDFReaderApp().run()
