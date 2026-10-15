using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
public static class UnitySemanticValidation
{
    static void Check(bool value,string message){if(!value)throw new Exception(message);}
    public static void BatchValidate()
    {
        try
        {
            var renderer=ScriptableObject.CreateInstance<UniversalRendererData>();AssetDatabase.CreateAsset(renderer,"Assets/SemanticRenderer.asset");
            var urp=UniversalRenderPipelineAsset.Create(renderer);AssetDatabase.CreateAsset(urp,"Assets/SemanticURP.asset");
            foreach(bool useUrp in new[]{true,false})
            {
                GraphicsSettings.defaultRenderPipeline=null;QualitySettings.renderPipeline=useUrp?urp:null;
                foreach(var name in new[]{"KageSemantic","HinataSemantic","StylizedSemantic","UniformSemantic","NeuralSemantic","LineageSemantic"})
                {
                    var folder="Assets/"+name;var manifest=JsonUtility.FromJson<Forge3DImporter.Manifest>(File.ReadAllText(folder+"/asset_manifest.json"));
                    var report=Forge3DImporter.ImportPackage(folder);
                    Check(report.passed&&report.normalsAndUVs&&report.finiteVerticesAndUVs,"Mesh channels: "+name);
                    Check(report.triangles==manifest.fbx_validation.before.triangles&&report.materials==manifest.materials.Length,"Topology/material slots: "+name);
                    var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(report.prefab);Check(prefab!=null,"Prefab missing");
                    foreach(var r in prefab.GetComponentsInChildren<MeshRenderer>())foreach(var material in r.sharedMaterials)
                    {
                        Check(material.shader.name==(useUrp?"Universal Render Pipeline/Lit":"Standard"),"Shader pipeline");
                        var albedo=material.GetTexture(useUrp?"_BaseMap":"_MainTex");Check(albedo!=null,"Albedo absent");
                        Check((AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(albedo)) as TextureImporter).sRGBTexture,"Albedo color space");
                        var normal=material.GetTexture("_BumpMap");if(normal!=null)Check((AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(normal)) as TextureImporter).textureType==TextureImporterType.NormalMap,"Normal import type");
                        foreach(var key in new[]{"_OcclusionMap","_MetallicGlossMap"}){var map=material.GetTexture(key);if(map!=null)Check(!(AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(map)) as TextureImporter).sRGBTexture,"Data map color space");}
                    }
                    File.Copy(folder+"/unity_import_report.json",folder+"/unity_"+(useUrp?"urp":"builtin")+".json",true);
                }
            }
            Debug.Log("SEMANTIC_SIX_REAL_ASSETS_URP_BUILTIN_PASS");EditorApplication.Exit(0);
        }
        catch(Exception error){Debug.LogException(error);EditorApplication.Exit(1);}
    }
}
