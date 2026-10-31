"""Identify only the disconnected rear-band geometry of the selected H3 shield."""
def shell_triangles(mesh):
 mesh.calc_loop_triangles();parents=list(range(len(mesh.vertices)))
 def root(i):
  while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
  return i
 for edge in mesh.edges:
  a,b=map(root,edge.vertices);parents[a]=b
 groups={}
 for v in mesh.vertices:groups.setdefault(root(v.index),[]).append(v)
 bands=set()
 for vertices in groups.values():
  if min(v.co.z for v in vertices)<0:
   assert max(v.co.z for v in vertices)<.09,'Unexpected shield component crosses front face'
   bands.update(v.index for v in vertices)
 assert bands and len(bands)<len(mesh.vertices)//2
 shell=[tuple(t.vertices) for t in mesh.loop_triangles if not all(i in bands for i in t.vertices)]
 rear=[tuple(t.vertices) for t in mesh.loop_triangles if all(i in bands for i in t.vertices)]
 return shell,rear
