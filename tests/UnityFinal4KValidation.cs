using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
public static class Forge3DFinal4KValidation
{
    public static void BatchValidate()
    {
        try
        {
            var renderer=AssetDatabase.LoadAssetAtPath<UniversalRendererData>("Assets/TestRenderer.asset");
            if(renderer==null){renderer=ScriptableObject.CreateInstance<UniversalRendererData>();AssetDatabase.CreateAsset(renderer,"Assets/TestRenderer.asset");}
            var urp=AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>("Assets/TestURP.asset");
            if(urp==null){urp=UniversalRenderPipelineAsset.Create(renderer);AssetDatabase.CreateAsset(urp,"Assets/TestURP.asset");}
            foreach(bool useUrp in new[]{true,false})
            {
                GraphicsSettings.defaultRenderPipeline=null;QualitySettings.renderPipeline=useUrp?urp:null;
                var report=Forge3DImporter.ImportPackage("Assets/Asset4K");
                if(report.textureWidth!=4096||report.textureHeight!=4096||report.normalTextureWidth!=4096||report.normalTextureHeight!=4096)throw new Exception("Exported 4K color/normal dimensions lost at Unity import.");
                if(!report.normalMapImported||!report.normalKeywordEnabled||report.triangles!=20000||!report.finiteVerticesAndUVs)throw new Exception("Mesh/normal import contract failed.");
                var material=AssetDatabase.LoadAssetAtPath<Material>("Assets/Asset4K/Materials/Forge3D.mat");
                if(material.shader.name!=(useUrp?"Universal Render Pipeline/Lit":"Standard"))throw new Exception("Incorrect pipeline material.");
                File.Copy("Assets/Asset4K/unity_import_report.json","Assets/Asset4K/unity_"+(useUrp?"urp":"builtin")+"_4k_report.json",true);
            }
            Debug.Log("ACTUAL_4K_COLOR_AND_NORMAL_URP_BUILTIN_PASS");EditorApplication.Exit(0);
        }
        catch(Exception error){Debug.LogException(error);EditorApplication.Exit(1);}
    }
}
