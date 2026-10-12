// Disposable QA project only. Tests a real exported TripoSG asset.
using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public static class Forge3DTripoSGValidation
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
            if(!string.IsNullOrEmpty(manifest.albedo))throw new InvalidOperationException("SG export must have no albedo.");
            // Reproduce reuse of a material left by an earlier textured package.
            Directory.CreateDirectory(folder+"/Materials");AssetDatabase.Refresh();
            var material=new Material(Shader.Find("Universal Render Pipeline/Lit"));
            var previous=AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/PreviousAlbedo.png");
            if(previous==null)throw new InvalidOperationException("Required real TripoSR texture fixture missing.");
            material.SetTexture("_BaseMap",previous);material.SetTexture("_MainTex",previous);
            AssetDatabase.CreateAsset(material,folder+"/Materials/Forge3D.mat");AssetDatabase.SaveAssets();
            Type importer=null;
            foreach(var assembly in AppDomain.CurrentDomain.GetAssemblies()){importer=assembly.GetType(manifest.editor_class);if(importer!=null)break;}
            if(importer==null)throw new InvalidOperationException("Importer not compiled.");
            importer.GetMethod("ImportPackage",BindingFlags.Static|BindingFlags.Public).Invoke(null,new object[]{folder});
            material=AssetDatabase.LoadAssetAtPath<Material>(folder+"/Materials/Forge3D.mat");
            if(material.GetTexture("_BaseMap")!=null||material.GetTexture("_MainTex")!=null)throw new InvalidOperationException("Stale albedo retained in geometry-only asset.");
            if(material.shader.name!="Universal Render Pipeline/Lit")throw new InvalidOperationException("Incorrect URP shader.");
            if(Mathf.Abs(material.GetFloat("_Smoothness")-0.35f)>0.001f)throw new InvalidOperationException("Incorrect smoothness.");
            Color color=material.GetColor("_BaseColor");
            if(Mathf.Abs(color.r-0.5f)>0.001f)throw new InvalidOperationException("Neutral base color lost.");
            var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(folder+"/Prefabs/Forge3D.prefab");
            if(prefab==null)throw new InvalidOperationException("Prefab missing.");
            var filters=prefab.GetComponentsInChildren<MeshFilter>();
            if(filters.Length==0)throw new InvalidOperationException("Mesh missing.");
            foreach(var filter in filters)foreach(var normal in filter.sharedMesh.normals)
                if(!float.IsFinite(normal.x)||!float.IsFinite(normal.y)||!float.IsFinite(normal.z)||normal.sqrMagnitude<0.5f)throw new InvalidOperationException("Invalid normals.");
            File.WriteAllText("Assets/sg_extra_validation.json","{\"passed\":true,\"stale_texture_cleared\":true,\"neutral_color\":0.5,\"normals_finite\":true}");
            Debug.Log("REAL_TRIPOSG_UNITY_URP_NO_TEXTURE_PASS");
            EditorApplication.Exit(0);
        }
        catch(Exception error){Debug.LogException(error);EditorApplication.Exit(1);}
    }
}
