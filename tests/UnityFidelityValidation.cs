using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
public static class UnityFidelityValidation
{
    public static void BatchValidate()
    {
        try
        {
            var renderer=AssetDatabase.LoadAssetAtPath<UniversalRendererData>("Assets/FidelityRenderer.asset");
            if(renderer==null){renderer=ScriptableObject.CreateInstance<UniversalRendererData>();AssetDatabase.CreateAsset(renderer,"Assets/FidelityRenderer.asset");}
            var urp=AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>("Assets/FidelityURP.asset");
            if(urp==null){urp=UniversalRenderPipelineAsset.Create(renderer);AssetDatabase.CreateAsset(urp,"Assets/FidelityURP.asset");}
            foreach(bool useUrp in new[]{true,false})
            {
                GraphicsSettings.defaultRenderPipeline=null;QualitySettings.renderPipeline=useUrp?urp:null;
                foreach(var name in new[]{"FaceAsset","ObjectAsset"})
                {
                    var folder="Assets/"+name;
                    var report=Forge3DImporter.ImportPackage(folder);
                    if(!report.passed||!report.normalsAndUVs||!report.finiteVerticesAndUVs)throw new Exception("Invalid mesh channels: "+name);
                    if(report.triangles!=(name=="FaceAsset"?20000:24)||report.materials!=(name=="FaceAsset"?1:2))throw new Exception("Lost triangles/material slots: "+name);
                    if(!report.normalMapImported||!report.normalKeywordEnabled)throw new Exception("Preserved normal map absent: "+name);
                    var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(report.prefab);if(prefab==null)throw new Exception("Prefab missing.");
                    foreach(var r in prefab.GetComponentsInChildren<MeshRenderer>())foreach(var material in r.sharedMaterials)
                    {
                        if(material.shader.name!=(useUrp?"Universal Render Pipeline/Lit":"Standard"))throw new Exception("Wrong pipeline shader.");
                        var albedo=material.GetTexture(useUrp?"_BaseMap":"_MainTex");
                        if(albedo==null||!(AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(albedo)) as TextureImporter).sRGBTexture)throw new Exception("Missing sRGB albedo.");
                        if(name=="FaceAsset"&&albedo.width!=4096)throw new Exception("Face atlas resolution changed.");
                        var normal=material.GetTexture("_BumpMap");if(normal!=null&&(AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(normal)) as TextureImporter).textureType!=TextureImporterType.NormalMap)throw new Exception("Wrong normal import type.");
                        if(material.name=="Fabric")
                        {
                            if(material.GetTexture("_OcclusionMap")==null||normal==null)throw new Exception("Protected Fabric data maps lost.");
                            if(useUrp?material.GetFloat("_Surface")!=1:material.GetFloat("_Mode")!=3)throw new Exception("Fabric transparency lost.");
                            var packed=material.GetTexture("_MetallicGlossMap");if(packed==null||(AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(packed)) as TextureImporter).sRGBTexture)throw new Exception("Packed map color space invalid.");
                            var raw=new Texture2D(2,2,TextureFormat.RGBA32,false,true);raw.LoadImage(File.ReadAllBytes(AssetDatabase.GetAssetPath(packed)));var pixel=raw.GetPixels32()[0];UnityEngine.Object.DestroyImmediate(raw);
                            if(pixel.r!=64||pixel.a!=204)throw new Exception("MR channel/factor packing changed.");
                        }
                        if(material.name=="Steel"&&(Mathf.Abs(material.GetFloat("_Metallic")-.9f)>.001f||Mathf.Abs(material.GetFloat(useUrp?"_Smoothness":"_Glossiness")-.8f)>.001f))throw new Exception("Steel factors changed.");
                    }
                    File.Copy(folder+"/unity_import_report.json",folder+"/unity_"+(useUrp?"urp":"builtin")+".json",true);
                }
            }
            Debug.Log("FIDELITY_FACE_OBJECT_URP_BUILTIN_PASS");EditorApplication.Exit(0);
        }
        catch(Exception error){Debug.LogException(error);EditorApplication.Exit(1);}
    }
}
