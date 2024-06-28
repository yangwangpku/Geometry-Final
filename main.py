import moderngl
import struct
import glfw
import imgui
import numpy as np
import tkinter as tk
from tkinter import filedialog

from App import App
from Camera import Camera
from mesh import ObjMesh, RenderedMesh

class MyApp(App):
    def init(self):
        ctx = self.ctx
        # Load a mesh
        self.mesh = ObjMesh("sample-data/simplification.obj")

        # Load the glsl program
        self.program = ctx.program(
            vertex_shader=open("shaders/mesh.vert.glsl").read(),
            fragment_shader=open("shaders/mesh.frag.glsl").read(),
        )

        # Create the rendered mesh from the mesh and the program
        self.rendered_mesh = RenderedMesh(ctx, self.mesh, self.program)

        # Setup camera
        w, h = self.size()
        self.camera = Camera(w, h)

        # Initialize some value used in the UI
        self.brush_size = 0.02

        self.mode = "view"  # "view", "select" or "deform"
        self.handle = None

        # Initialize Tkinter for file dialog
        self.root = tk.Tk()
        self.root.withdraw()

    def load_mesh(self, file_path):
        self.mesh = ObjMesh(file_path)
        self.rendered_mesh = RenderedMesh(self.ctx, self.mesh, self.program)

    def export_mesh(self, file_path):
        self.mesh.export_mesh(file_path)

    def update(self, time, delta_time):
        # Update damping effect (and internal matrices)
        self.camera.update(time, delta_time)

    def render(self):
        ctx = self.ctx
        self.camera.set_uniforms(self.program)

        ctx.screen.clear(1.0, 1.0, 1.0, -1.0)

        ctx.enable_only(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        self.rendered_mesh.render(ctx)

    def on_key(self, key, scancode, action, mods):
        if key == glfw.KEY_ESCAPE:
            self.should_close()
        if key == glfw.KEY_R:
            self.clear_fixed_region()

    def on_mouse_move(self, x, y):
        self.camera.update_rotation(x, y)
        if self.mode == "deform":
            if glfw.get_mouse_button(self.window, glfw.MOUSE_BUTTON_RIGHT) == glfw.PRESS:
                self.move_handle_position(x,y)

    def on_mouse_button(self, button, action, mods):
        if action == glfw.PRESS and button == glfw.MOUSE_BUTTON_LEFT:
            x, y = self.mouse_pos()
            self.camera.start_rotation(x, y)
        if action == glfw.RELEASE and button == glfw.MOUSE_BUTTON_LEFT:
            self.camera.stop_rotation()

        if self.mode == "select":
            if action == glfw.PRESS and button == glfw.MOUSE_BUTTON_LEFT:
                x, y = self.mouse_pos()
                self.select_handle(x,y)

    def on_right_mouse_button_held(self):
        x, y = self.mouse_pos()
        if self.mode == "view":
            self.select_fixed_region(x, y)
        if self.mode == "select":
            self.select_deformable_region(x, y)

    def select_fixed_region(self, x, y):
        # global selected_vertices, vertices
        distance_threshold = self.brush_size
        ray_origin, ray_direction = self.camera.screen_to_world_ray(x, y)
        objmesh = self.rendered_mesh.objmesh
        mesh = self.rendered_mesh.objmesh.mesh
        locations, index_ray, index_tri = mesh.ray.intersects_location(
            ray_origins=[ray_origin],
            ray_directions=[ray_direction]
        )
        if len(locations) > 0:
            # Compute distances from the ray origin to each intersection point
            distances = np.linalg.norm(locations - ray_origin, axis=1)
            
            # Get the index of the closest intersection
            closest_index = np.argmin(distances)
            
            # Get the closest intersection point
            first_intersection_point = locations[closest_index]
        else:
            return
        vertices = mesh.vertices
        distances = np.linalg.norm(vertices - first_intersection_point, axis=1)
        selected_index = np.where(distances < distance_threshold)[0]
        objmesh.add_fixed_region(selected_index)
        self.rendered_mesh.update()

    def select_deformable_region(self, x, y):
        # global selected_vertices, vertices
        distance_threshold = self.brush_size
        ray_origin, ray_direction = self.camera.screen_to_world_ray(x, y)
        objmesh = self.rendered_mesh.objmesh
        mesh = self.rendered_mesh.objmesh.mesh
        locations, index_ray, index_tri = mesh.ray.intersects_location(
            ray_origins=[ray_origin],
            ray_directions=[ray_direction]
        )
        if len(locations) > 0:
            # Compute distances from the ray origin to each intersection point
            distances = np.linalg.norm(locations - ray_origin, axis=1)
            
            # Get the index of the closest intersection
            closest_index = np.argmin(distances)
            
            # Get the closest intersection point
            first_intersection_point = locations[closest_index]
        else:
            return
        vertices = mesh.vertices
        distances = np.linalg.norm(vertices - first_intersection_point, axis=1)
        selected_index = np.where(distances < distance_threshold)[0]
        objmesh.add_deformable_region(selected_index)
        self.rendered_mesh.update()



    def select_handle(self, x, y):
        # global selected_vertices, vertices
        distance_threshold = self.brush_size
        ray_origin, ray_direction = self.camera.screen_to_world_ray(x, y)
        objmesh = self.rendered_mesh.objmesh
        mesh = self.rendered_mesh.objmesh.mesh
        locations, index_ray, index_tri = mesh.ray.intersects_location(
            ray_origins=[ray_origin],
            ray_directions=[ray_direction]
        )
        if len(locations) > 0:
            # Compute distances from the ray origin to each intersection point
            distances = np.linalg.norm(locations - ray_origin, axis=1)
            
            # Get the index of the closest intersection
            closest_index = np.argmin(distances)
            
            # Get the closest intersection point
            first_intersection_point = locations[closest_index]
            self.handle = first_intersection_point

            self.rendered_mesh.objmesh.calc_deformable_region(self.handle)
            self.rendered_mesh.update()

    def move_handle_position(self, x, y):
        if self.handle is None:
            return
        original_position = self.handle
        ray_origin, ray_direction = self.camera.screen_to_world_ray(x, y)
        distance = np.linalg.norm(original_position - ray_origin)
        new_position = ray_origin + distance * ray_direction    # Keep the distance from the camera
        self.handle = new_position
        self.rendered_mesh.objmesh.deform(original_position, new_position)
        self.rendered_mesh.update()

    def draw_handle(self):
        if self.handle is not None:    
            draw_list = imgui.get_background_draw_list()
            x,y = self.camera.world_to_screen(self.handle)
            p_min = (x - 5, y - 5)
            p_max = (x + 5, y + 5)
            color = imgui.get_color_u32_rgba(0.0, 1.0, 0.0, 1.0)  # Green color
            draw_list.add_rect_filled(p_min[0], p_min[1], p_max[0], p_max[1], color)



    def clear_fixed_region(self):
        self.rendered_mesh.objmesh.clear_fixed_region()
        self.rendered_mesh.update()

    def on_resize(self, width, height):
        self.camera.resize(width, height)
        self.ctx.viewport = (0, 0, width, height)

    def on_scroll(self, x, y):
        self.camera.zoom(y)

    def ui(self):
        
        """Use the imgui module here to draw the UI"""
        if imgui.begin_main_menu_bar():
            if imgui.begin_menu("File", True):

                clicked_quit, selected_quit = imgui.menu_item(
                    "Quit", 'Esc', False, True
                )

                clicked_redo, selected_redo = imgui.menu_item(
                    "Clear fixed region", 'R', False, True
                )

                if clicked_quit:
                    self.should_close()
                if clicked_redo:
                    self.clear_fixed_region()

                imgui.end_menu()
            imgui.end_main_menu_bar()

        imgui.set_next_window_size(300, 200)

        imgui.begin("Control", True)

        # Button to open file dialog and load new mesh
        if imgui.button("Load Mesh"):
            file_path = filedialog.askopenfilename(
                filetypes=[("OBJ files", "*.obj"), ("All files", "*.*")]
            )
            if file_path:
                self.load_mesh(file_path)

        # Button to open file dialog and save the mesh
        if imgui.button("Export Mesh"):
            file_path = filedialog.asksaveasfilename(
                defaultextension=".obj",
                filetypes=[("OBJ files", "*.obj"), ("All files", "*.*")]
            )
            if file_path:
                self.export_mesh(file_path)

        self.shape_need_update = False
        changed, self.brush_size = imgui.input_float(
            "Brush Size", self.brush_size, step=0.02, format="%.02f"
        )
        if self.brush_size < 0.0:
            self.brush_size = 0.0

        if imgui.button("View"):
            self.mode = 'view'
        if imgui.button("select"):
            self.mode = 'select'
        if imgui.button("deform"):
            self.mode = 'deform'

        

        # Draw a small box on the screen
        if self.handle is not None:
            self.draw_handle()

        imgui.end()

def main():
    app = MyApp(1280, 720, "Python 3d Mesh Deformation")
    app.main_loop()

if __name__ == "__main__":
    main()

