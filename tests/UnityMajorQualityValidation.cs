using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
public static class Forge3DMajorValidation
{
    public static void BatchValidate()
    {
        try
        {
            var renderer=ScriptableObject.CreateInstance<UniversalRendererData>();AssetDatabase.CreateAsset(renderer,"Assets/TestRenderer.asset");
            var urp=UniversalRenderPipelineAsset.Create(renderer);AssetDatabase.CreateAsset(urp,"Assets/TestURP.asset");
            foreach(bool useUrp in new[]{true,false})
            {
                GraphicsSettings.defaultRenderPipeline=null;QualitySettings.renderPipeline=useUrp?urp:null;
                var report=Forge3DImporter.ImportPackage("Assets/AssetLow");
                if(!report.normalMapImported||report.normalMapType!="NormalMap"||!report.normalKeywordEnabled)throw new Exception("Real normal map not configured.");
                if(report.textureWidth!=2048||report.triangles!=20000)throw new Exception("Low poly budget/2K atlas lost.");
                var material=AssetDatabase.LoadAssetAtPath<Material>("Assets/AssetLow/Materials/Forge3D.mat");
                if(material.shader.name!=(useUrp?"Universal Render Pipeline/Lit":"Standard"))throw new Exception("Incorrect pipeline material.");
                File.Copy("Assets/AssetLow/unity_import_report.json","Assets/AssetLow/unity_"+(useUrp?"urp":"builtin")+"_report.json",true);
                var geometry=Forge3DImporter.ImportPackage("Assets/AssetGeometry");
                if(geometry.normalMapImported||geometry.normalKeywordEnabled||geometry.textures!=0)throw new Exception("Geometry-only package acquired texture maps.");
            }
            Debug.Log("ACTUAL_URP_AND_BUILTIN_NORMAL_BAKE_IMPORT_PASS");EditorApplication.Exit(0);
        }
        catch(Exception error){Debug.LogException(error);EditorApplication.Exit(1);}
    }
}
