import numpy as np
from scipy.spatial.transform import Rotation

from utils import perspective

class Camera:
    def __init__(self, width, height):
        self.sensitivity = 0.01
        self.zoom_sensitivity = 0.1
        self.momentum = 0.93

        self._zoom = 2
        self.rot = Rotation.identity()
        self.previous_mouse_pos = None
        self.angular_velocity = None
        self.rot_around_vertical = 0
        self.rot_around_horizontal = 0
        self.width = width
        self.height = height
        self.resize(width, height)

    def resize(self, width, height):
        self.perspectiveMatrix = perspective(np.radians(80), width/height, 0.01, 100.0)

    def zoom(self, steps):
        self._zoom *= pow(1 - self.zoom_sensitivity, steps)

    def update(self, time, delta_time):
        if self.previous_mouse_pos is None and self.angular_velocity is not None:
            self._damping()

        self.rot = Rotation.identity()
        self.rot *= Rotation.from_rotvec(self.rot_around_horizontal * np.array([1,0,0]))
        self.rot *= Rotation.from_rotvec(self.rot_around_vertical * np.array([0,1,0]))

        viewMatrix = np.eye(4)
        viewMatrix[:3,:3] = self.rot.as_matrix()
        viewMatrix[0:3,3] = 0, 0, -self._zoom
        self.viewMatrix = viewMatrix

    def set_uniforms(self, program):
        if "uPerspectiveMatrix" in program:
            program["uPerspectiveMatrix"].write(self.perspectiveMatrix.T.astype('f4').tobytes())
        if "uViewMatrix" in program:
            program["uViewMatrix"].write(self.viewMatrix.T.astype('f4').tobytes())

    def start_rotation(self, x, y):
        self.previous_mouse_pos = x, y

    def update_rotation(self, x, y):
        if self.previous_mouse_pos is None:
            return
        sx, sy = self.previous_mouse_pos
        dx = x - sx
        dy = y - sy
        self._rotate(dx, dy)
        self.previous_mouse_pos = x, y

    def stop_rotation(self):
        self.previous_mouse_pos = None

    def _rotate(self, dx, dy):
        self.rot_around_vertical += dx * self.sensitivity
        self.rot_around_horizontal += dy * self.sensitivity
        self.rot_around_horizontal = np.clip(self.rot_around_horizontal, -np.pi / 2, np.pi / 2)
        self.angular_velocity = dx, dy

    def _damping(self):
        dx, dy = self.angular_velocity
        if dx * dx + dy * dy < 1e-6:
            self.angular_velocity = None
        else:
            self._rotate(dx * self.momentum, dy * self.momentum)

    def screen_to_world_ray(self, x, y):
        # Convert screen coordinates to normalized device coordinates (NDC)
        x = 2.0 * x / self.width - 1.0
        y = 1.0 - 2.0 * y / self.height

        # Clip coordinates
        clip_coords = np.array([x, y, -1.0, 1.0], dtype=np.float32)
        # Compute the inverse of the projection matrix
        inv_proj_matrix = np.linalg.inv(self.perspectiveMatrix)

        # Transform clip coordinates to view space
        view_space_pos = inv_proj_matrix @ clip_coords
        view_space_pos[2] = -1.0  # Set to -1 for a forward-facing ray
        view_space_pos[3] = 0.0   # Set to 0 for a direction vector

        # Compute the inverse of the view matrix
        inv_view_matrix = np.linalg.inv(self.viewMatrix)
        eye_position = inv_view_matrix[:3, 3]

        # Transform view space coordinates to world space
        world_space_pos = inv_view_matrix @ view_space_pos

        # Normalize the direction
        ray_direction = world_space_pos[:3]
        ray_direction /= np.linalg.norm(ray_direction)

        return eye_position,ray_direction

    def world_to_screen(self, world_pos):
        view_pos = self.viewMatrix @ np.array([*world_pos, 1])
        clip_pos = self.perspectiveMatrix @ view_pos
        clip_pos /= clip_pos[3]
        x = (clip_pos[0] + 1) / 2 * self.width
        y = (1 - clip_pos[1]) / 2 * self.height
        return x, y