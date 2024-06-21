import numpy as np
from moderngl import TRIANGLES
import trimesh
from scipy.spatial import distance_matrix
import networkx as nx

class Mesh:
    """Simply contains an array of triangles and an array of normals.
    Could be enhanced, for instance with an element buffer"""
    def __init__(self, P, N, C=None):
        self.P = P
        self.N = N
        self.C = C


class ObjMesh(Mesh):
    """An example of mesh loader, using the pywavefront module.
    Only load the first mesh of the file if there are more than one."""
    def __init__(self, filepath=None):
        if filepath is not None:
            self.load_mesh(filepath)
        
    def load_mesh(self,filepath):
        mesh=trimesh.load(filepath)
        self.mesh=mesh
        self.fixed_region = np.zeros(len(mesh.vertices),dtype=bool)
        self.deformable_region = np.zeros(len(mesh.vertices),dtype=bool)
        print(f"(Object has {len(self.mesh.vertices)} points)")
        self.create_weighted_graph()
        self.update_GL_variables()

    def export_mesh(self,filepath):
        self.mesh.export(filepath)

    def create_weighted_graph(self):
        graph = self.mesh.vertex_adjacency_graph
        self.graph = nx.Graph()

        # Add nodes to the weighted graph
        self.graph.add_nodes_from(graph.nodes())

        # Add edges with weights
        for u, v in graph.edges():
            distance = self.mesh.vertices[u] - self.mesh.vertices[v]
            weight = np.linalg.norm(distance)
            self.graph.add_edge(u, v, weight=weight)        


    def update_GL_variables(self):
        vertices = self.mesh.vertices
        faces = self.mesh.faces
        normals = self.mesh.vertex_normals
        colors = self.mesh.visual.vertex_colors.copy()
        colors[self.deformable_region] = [0,0,255,255]
        colors[self.fixed_region] = [255,0,0,255]

        self.P = vertices[faces.flatten()]
        self.N = normals[faces.flatten()]
        self.C = colors[faces.flatten()] / 255.0

    def add_fixed_region(self,indices):
        self.fixed_region[indices] = True
        self.clear_deformable_region()

    def add_deformable_region(self,indices):
        self.deformable_region[indices] = True

    def clear_fixed_region(self):
        self.fixed_region = np.zeros_like(self.fixed_region)
        self.clear_deformable_region()

    def clear_deformable_region(self):
        self.deformable_region = np.zeros_like(self.deformable_region)

    def calc_deformable_region(self,handle):
        min_dists,min_indices = self._geodestic_distances_from_fixed_region()

        handle_distances = np.linalg.norm(self.mesh.vertices - handle, axis=1)
        handle_index = np.argmin(handle_distances)

        handle_path_lengths = nx.single_source_dijkstra_path_length(self.graph, source=handle_index, weight='weight')

        handle2vertex = np.array([handle_path_lengths.get(j, np.inf) for j in range(len(self.mesh.vertices))])
        handle2min = handle2vertex[min_indices]
        self.deformable_region = (handle2vertex < handle2min)

        self.distance_info = {
            'vertex_to_fixed_region': min_dists,
            'vertex_to_handle': handle2vertex,
        }

    def deform(self,handle_original_position,handle_new_position):
        vertex_to_fixed_region = self.distance_info['vertex_to_fixed_region']
        vertex_to_handle = self.distance_info['vertex_to_handle']

        weight = vertex_to_fixed_region/((vertex_to_fixed_region + vertex_to_handle) + 1e-6)

        handle_shift = handle_new_position - handle_original_position

        self.mesh.vertices[self.deformable_region] += weight[self.deformable_region][:,np.newaxis] * handle_shift

        # Update the OpenGL variables
        self.update_GL_variables()

    def _euclidean_distances_from_fixed_region(self):
        vertices = self.mesh.vertices
        fixed_region_indices = np.where(self.fixed_region)[0]
        fixed_region_vertices = vertices[self.fixed_region]
        dists = distance_matrix(vertices, fixed_region_vertices)
        min_dists = np.min(dists, axis=1)
        min_indices = fixed_region_indices[np.argmin(dists, axis=1)]
        return min_dists,min_indices
        
    def _geodestic_distances_from_fixed_region(self):
        # Create the adjacency graph of the mesh
        weighted_graph = self.graph.copy()
        
        fixed_region_indices = np.where(self.fixed_region)[0]
        virtual_source = 'virtual_source'
        weighted_graph.add_node(virtual_source)

        for index in fixed_region_indices:
            weighted_graph.add_edge(virtual_source,index,weight=0)

        shortest_path_details = nx.single_source_dijkstra_path(weighted_graph, source=virtual_source, weight='weight')
        shortest_path_lengths = nx.single_source_dijkstra_path_length(weighted_graph, source=virtual_source, weight='weight')

        min_dists = np.array([shortest_path_lengths.get(j, np.inf) for j in range(len(self.mesh.vertices))])
        min_indices = np.zeros(len(self.mesh.vertices),dtype=int)

        for index,shortest_path in shortest_path_details.items():
            if index != virtual_source:
                min_indices[index] = shortest_path[1]
        return min_dists,min_indices

class RenderedMesh:
    """The equivalent of a Mesh, but stored in OpenGL buffers (on the GPU)
    ready to be rendered."""
    def __init__(self, ctx, objmesh, program):
        self.objmesh = objmesh
        self.ctx = ctx
        self.program = program
        self.update()
        # self.vboP = ctx.buffer(mesh.P.astype('f4').tobytes())
        # self.vboN = ctx.buffer(mesh.N.astype('f4').tobytes())
        # self.vboC = ctx.buffer(mesh.C.astype('f4').tobytes())
        # self.vao = ctx.vertex_array(
        #     program,
        #     [
        #         (self.vboP, "3f", "in_vert"),
        #         (self.vboN, "3f", "in_normal"),
        #         (self.vboC, "4f", "in_color"),
        #     ]
        # )
    
    def update(self):
        self.objmesh.update_GL_variables()
        self.vboP = self.ctx.buffer(self.objmesh.P.astype('f4').tobytes())
        self.vboN = self.ctx.buffer(self.objmesh.N.astype('f4').tobytes())
        self.vboC = self.ctx.buffer(self.objmesh.C.astype('f4').tobytes())
        self.vao = self.ctx.vertex_array(
            self.program,
            [
                (self.vboP, "3f", "in_vert"),
                (self.vboN, "3f", "in_normal"),
                (self.vboC, "4f", "in_color"),
            ]
        )

    def release(self):
        self.vboP.release()
        self.vboN.release()
        self.vboC.release()
        self.vao.release()

    def render(self, ctx):
        self.vao.render(TRIANGLES)
