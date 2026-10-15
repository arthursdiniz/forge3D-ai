using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
public static class UnityHairValidation
{
    static void Check(bool condition,string message){if(!condition)throw new Exception(message);}
    public static void BatchValidate()
    {
        try
        {
            var renderer=ScriptableObject.CreateInstance<UniversalRendererData>();AssetDatabase.CreateAsset(renderer,"Assets/HairRenderer.asset");
            var urp=UniversalRenderPipelineAsset.Create(renderer);AssetDatabase.CreateAsset(urp,"Assets/HairURP.asset");
            foreach(bool useUrp in new[]{true,false})
            {
                GraphicsSettings.defaultRenderPipeline=null;QualitySettings.renderPipeline=useUrp?urp:null;
                foreach(var name in new[]{"BaselineAsset","HairAsset"})
                {
                    var folder="Assets/"+name;var manifest=JsonUtility.FromJson<Forge3DImporter.Manifest>(File.ReadAllText(folder+"/asset_manifest.json"));var report=Forge3DImporter.ImportPackage(folder);
                    Check(report.passed&&report.normalsAndUVs&&report.finiteVerticesAndUVs,"Mesh channels failed: "+name);
                    Check(report.triangles==manifest.fbx_validation.before.triangles,"Triangle count changed: "+name);
                    Check(report.materials==manifest.materials.Length,"Material slots changed: "+name);
                    var dimensions=manifest.fbx_validation.before.dimensions;
                    Check(Mathf.Abs(report.dimensions[0]-dimensions[0])<.002f&&Mathf.Abs(report.dimensions[1]-dimensions[2])<.002f&&Mathf.Abs(report.dimensions[2]-dimensions[1])<.002f,"Units/up-axis changed: "+name);
                    var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(report.prefab);Check(prefab!=null,"Prefab missing");
                    foreach(var meshRenderer in prefab.GetComponentsInChildren<MeshRenderer>())foreach(var material in meshRenderer.sharedMaterials)
                    {
                        Check(material.shader.name==(useUrp?"Universal Render Pipeline/Lit":"Standard"),"Wrong shader");
                        var texture=material.GetTexture(useUrp?"_BaseMap":"_MainTex");Check(texture!=null,"Albedo missing");
                        Check((AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(texture)) as TextureImporter).sRGBTexture,"Wrong albedo color space");
                    }
                    File.Copy(folder+"/unity_import_report.json",folder+"/unity_"+(useUrp?"urp":"builtin")+".json",true);
                }
                var before=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/BaselineAsset/Prefabs/Forge3D.prefab"));
                var after=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HairAsset/Prefabs/Forge3D.prefab"));
                foreach(var source in before.GetComponentsInChildren<MeshFilter>())
                {
                    var matches=after.GetComponentsInChildren<MeshFilter>().Where(f=>f.sharedMesh.triangles.Length==source.sharedMesh.triangles.Length).ToArray();Check(matches.Length==1,"Ambiguous original mesh match");
                    var target=matches[0];var a=source.sharedMesh;var b=target.sharedMesh;Check(a.vertexCount==b.vertexCount&&a.triangles.SequenceEqual(b.triangles),"Original mesh indexing changed");
                    var av=a.vertices;var bv=b.vertices;var an=a.normals;var bn=b.normals;var au=a.uv;var bu=b.uv;
                    for(int i=0;i<av.Length;i++)
                    {
                        Check(Vector3.Distance(source.transform.TransformPoint(av[i]),target.transform.TransformPoint(bv[i]))<.00001f,"Original world geometry/orientation changed");
                        Check(Vector3.Distance(source.transform.TransformDirection(an[i]),target.transform.TransformDirection(bn[i]))<.00001f,"Original normals changed");
                        Check(Vector2.Distance(au[i],bu[i])<.00001f,"Original UV changed");
                    }
                }
                UnityEngine.Object.DestroyImmediate(before);UnityEngine.Object.DestroyImmediate(after);
            }
            Debug.Log("HAIR_BASELINE_PRESERVATION_UV_NORMAL_MATERIAL_SCALE_URP_BUILTIN_PASS");EditorApplication.Exit(0);
        }
        catch(Exception error){Debug.LogException(error);EditorApplication.Exit(1);}
    }
}
