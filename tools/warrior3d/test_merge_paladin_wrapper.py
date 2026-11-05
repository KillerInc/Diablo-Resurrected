"""Synthetic safeguards for exporter-only armature wrapper compatibility."""
import unittest
from merge_paladin_walk import logical_parent

class WrapperTests(unittest.TestCase):
 def test_identity_unanimated_wrapper_matches_scene_root(self):
  doc={'nodes':[{'name':'Armature','children':[1]},{'name':'root'}]}
  self.assertIsNone(logical_parent(doc,{1:0},1,{'root'}))
  self.assertIsNone(logical_parent({'nodes':[{'name':'root'}]}, {},0,{'root'}))
 def test_transformed_wrapper_is_not_ignored(self):
  doc={'nodes':[{'name':'Armature','translation':[1,0,0]},{'name':'root'}]}
  self.assertEqual(logical_parent(doc,{1:0},1,{'root'}),'Armature')
 def test_real_identity_bone_parent_is_not_ignored(self):
  doc={'nodes':[{'name':'pelvis'},{'name':'chest'}]}
  self.assertEqual(logical_parent(doc,{1:0},1,{'chest'}),'pelvis')
 def test_animated_wrapper_is_not_ignored(self):
  doc={'nodes':[{'name':'Armature'},{'name':'root'}]}
  self.assertEqual(logical_parent(doc,{1:0},1,{'Armature','root'}),'Armature')
 def test_skin_joint_wrapper_is_not_ignored(self):
  doc={'nodes':[{'name':'Armature'},{'name':'root'}],'skins':[{'joints':[0,1]}]}
  self.assertEqual(logical_parent(doc,{1:0},1,{'root'}),'Armature')
if __name__=='__main__':unittest.main()
