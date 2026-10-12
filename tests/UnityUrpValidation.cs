// Copied only to a disposable test project, not exported to user packages.
using System;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public static class Forge3DURPValidation
{
    [Serializable] public class TestManifest { public string editor_class; }
    public static void BatchValidate()
    {
        try
        {
            var renderer = AssetDatabase.LoadAssetAtPath<UniversalRendererData>("Assets/Forge3DTestRenderer.asset");
            if(renderer==null){renderer=ScriptableObject.CreateInstance<UniversalRendererData>();AssetDatabase.CreateAsset(renderer,"Assets/Forge3DTestRenderer.asset");}
            var pipeline = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>("Assets/Forge3DTestURP.asset");
            if(pipeline==null){pipeline=UniversalRenderPipelineAsset.Create(renderer);AssetDatabase.CreateAsset(pipeline,"Assets/Forge3DTestURP.asset");}
            // Exercise QualitySettings-only override: default remains null.
            GraphicsSettings.defaultRenderPipeline=null;
            QualitySettings.renderPipeline=pipeline;
            AssetDatabase.SaveAssets();
            foreach (string folder in new[]{"Assets/AssetA","Assets/AssetB","Assets/AssetC"})
            {
                if(!Directory.Exists(folder))throw new InvalidOperationException("Required quality fixture missing: "+folder);
                var manifest=JsonUtility.FromJson<TestManifest>(File.ReadAllText(folder+"/asset_manifest.json"));
                Type importer=null;
                foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies()) { importer=assembly.GetType(manifest.editor_class); if(importer!=null)break; }
                if(importer==null)throw new InvalidOperationException("Importer class not compiled: "+manifest.editor_class);
                importer.GetMethod("ImportPackage",BindingFlags.Static|BindingFlags.Public).Invoke(null,new object[]{folder});
                var material=AssetDatabase.LoadAssetAtPath<Material>(folder+"/Materials/Forge3D.mat");
                if(material.shader.name!="Universal Render Pipeline/Lit")throw new InvalidOperationException("Incorrect URP shader: "+material.shader.name);
                if(material.GetTexture("_BaseMap")==null)throw new InvalidOperationException("URP albedo missing");
                if(Mathf.Abs(material.GetFloat("_Smoothness")-0.35f)>0.001f)throw new InvalidOperationException("Roughness factor lost");
                if(folder=="Assets/AssetC"&&material.GetTexture("_BaseMap").width!=2048)throw new InvalidOperationException("2048 texture lost");
                if(AssetDatabase.LoadAssetAtPath<GameObject>(folder+"/Prefabs/Forge3D.prefab")==null)throw new InvalidOperationException("Prefab missing");
            }
            Debug.Log("FORGE3D_URP_MULTIPLE_IMPORT_PASS");
            EditorApplication.Exit(0);
        }
        catch(Exception error) { Debug.LogException(error); EditorApplication.Exit(1); }
    }
}
