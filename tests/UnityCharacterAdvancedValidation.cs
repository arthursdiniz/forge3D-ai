// Disposable validation project only; checks the actual exported candidate.
using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public static class Forge3DCharacterAdvancedValidation
{
    [Serializable] public class TestManifest { public string editor_class; public string albedo; }
    public static void BatchValidate()
    {
        try
        {
            var renderer=ScriptableObject.CreateInstance<UniversalRendererData>();
            AssetDatabase.CreateAsset(renderer,"Assets/TestRenderer.asset");
            var pipeline=UniversalRenderPipelineAsset.Create(renderer);
            AssetDatabase.CreateAsset(pipeline,"Assets/TestURP.asset");
            GraphicsSettings.defaultRenderPipeline=null;
            QualitySettings.renderPipeline=pipeline;
            const string folder="Assets/Forge3D_Asset";
            var manifest=JsonUtility.FromJson<TestManifest>(File.ReadAllText(folder+"/asset_manifest.json"));
            if(string.IsNullOrEmpty(manifest.albedo))throw new InvalidOperationException("Projected reference texture missing.");
            Type importer=null;
            foreach(var assembly in AppDomain.CurrentDomain.GetAssemblies()){importer=assembly.GetType(manifest.editor_class);if(importer!=null)break;}
            if(importer==null)throw new InvalidOperationException("Importer did not compile.");
            importer.GetMethod("ImportPackage",BindingFlags.Static|BindingFlags.Public).Invoke(null,new object[]{folder});
            var material=AssetDatabase.LoadAssetAtPath<Material>(folder+"/Materials/Forge3D.mat");
            if(material.shader.name!="Universal Render Pipeline/Lit")throw new InvalidOperationException("Incorrect URP shader.");
            if(Mathf.Abs(material.GetFloat("_Smoothness")-0.35f)>0.001f)throw new InvalidOperationException("Incorrect smoothness.");
            var texture=material.GetTexture("_BaseMap");
            if(texture==null||texture.width!=1024||texture.height!=1024)throw new InvalidOperationException("Reference atlas was lost/resized.");
            var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(folder+"/Prefabs/Forge3D.prefab");
            if(prefab==null)throw new InvalidOperationException("Prefab missing.");
            var filters=prefab.GetComponentsInChildren<MeshFilter>();
            if(filters.Length==0)throw new InvalidOperationException("Mesh missing.");
            foreach(var filter in filters)
            {
                var mesh=filter.sharedMesh;
                foreach(var normal in mesh.normals)
                    if(!float.IsFinite(normal.x)||!float.IsFinite(normal.y)||!float.IsFinite(normal.z)||normal.sqrMagnitude<0.5f)throw new InvalidOperationException("Invalid normals.");
                foreach(var uv in mesh.uv)
                    if(!float.IsFinite(uv.x)||!float.IsFinite(uv.y)||uv.x<-0.00001f||uv.y<-0.00001f||uv.x>1.00001f||uv.y>1.00001f)throw new InvalidOperationException("Invalid UV coordinates.");
            }
            if(!File.Exists(folder+"/HUNYUAN_LICENSE.txt")||!File.Exists(folder+"/HUNYUAN_NOTICE.txt"))throw new InvalidOperationException("License notices missing.");
            File.WriteAllText("Assets/character_extra_validation.json","{\"passed\":true,\"normals_finite_nonzero\":true,\"uv_finite_in_unit_square\":true,\"reference_atlas_1024\":true,\"license_included\":true}");
            Debug.Log("REAL_CHARACTER_ADVANCED_UNITY_IMPORT_PASS");
            EditorApplication.Exit(0);
        }
        catch(Exception error){Debug.LogException(error);EditorApplication.Exit(1);}
    }
}
