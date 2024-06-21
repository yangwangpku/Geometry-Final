import glfw
import moderngl
import imgui
from imgui.integrations.glfw import GlfwRenderer as ImguiRenderer

class App:
    def __init__(self, width = 640, height = 480, title = "Hello world"):
        imgui.create_context()

        if not glfw.init():
            return
        
        self.window = glfw.create_window(width, height, title, None, None)
        if not self.window:
            glfw.terminate()
            return

        glfw.make_context_current(self.window)
        self.ctx = moderngl.create_context(require=460)

        self.impl = ImguiRenderer(self.window, attach_callbacks=False)
        
        glfw.set_key_callback(self.window, self._on_key)
        glfw.set_cursor_pos_callback(self.window, self._on_mouse_move)
        glfw.set_mouse_button_callback(self.window, self._on_mouse_button)
        glfw.set_window_size_callback(self.window, self._on_resize)
        glfw.set_char_callback(self.window, self._on_char)
        glfw.set_scroll_callback(self.window, self._on_scroll)

        self.init()

    def main_loop(self):
        previous_time = glfw.get_time()

        # Loop until the user closes the window
        while not glfw.window_should_close(self.window):
            glfw.poll_events()
            self.impl.process_inputs()

            current_time = glfw.get_time()
            delta_time = current_time - previous_time
            previous_time = current_time
            self.update(current_time, delta_time)
            self.render()

            imgui.new_frame()
            self.ui()
            imgui.render()
            self.impl.render(imgui.get_draw_data())

            # Check if the left mouse button is pressed
            if glfw.get_mouse_button(self.window, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS:
                self._on_left_mouse_button_held()

            # Check if the right mouse button is pressed
            if glfw.get_mouse_button(self.window, glfw.MOUSE_BUTTON_RIGHT) == glfw.PRESS:
                self._on_right_mouse_button_held()

            glfw.swap_buffers(self.window)

        self.impl.shutdown()
        glfw.terminate()

    def should_close(self):
        glfw.set_window_should_close(self.window, True)

    def mouse_pos(self):
        return glfw.get_cursor_pos(self.window)

    def size(self):
        return glfw.get_window_size(self.window)

    def init(self):
        pass

    def update(self, time):
        pass

    def render(self):
        pass

    def ui(self):
        pass

    def _on_key(self, window, key, scancode, action, mods):
        self.impl.keyboard_callback(window, key, scancode, action, mods)
        self.on_key(key, scancode, action, mods)

    def on_key(self, key, scancode, action, mods):
        pass

    def _on_char(self, window, codepoint):
        self.impl.char_callback(window, codepoint)
        self.on_char(codepoint)

    def on_char(self, codepoint):
        pass

    def _on_mouse_move(self, window, x, y):
        self.impl.mouse_callback(window, x, y)
        self.on_mouse_move(x, y)

    def on_mouse_move(self, x, y):
        pass

    def _on_mouse_button(self, window, button, action, mods):
        if not imgui.get_io().want_capture_mouse:
            self.on_mouse_button(button, action, mods)

    def on_mouse_button(self, button, action, mods):
        pass

    def _on_scroll(self, window, xoffset, yoffset):
        self.impl.scroll_callback(window, xoffset, yoffset)
        self.on_scroll(xoffset, yoffset)

    def on_scroll(self, xoffset, yoffset):
        pass

    def _on_resize(self, window, width, height):
        self.impl.resize_callback(window, width, height)
        self.on_resize(width, height)

    def on_resize(self, width, height):
        pass

    def _on_left_mouse_button_held(self):
        self.on_left_mouse_button_held()
    
    def on_left_mouse_button_held(self):
        pass

    def _on_right_mouse_button_held(self):
        self.on_right_mouse_button_held()

    def on_right_mouse_button_held(self):
        pass