using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
public static class UnityTextureValidation
{
    public static void BatchValidate()
    {
        try
        {
            var renderer=ScriptableObject.CreateInstance<UniversalRendererData>();
            AssetDatabase.CreateAsset(renderer,"Assets/TextureRenderer.asset");
            var urp=UniversalRenderPipelineAsset.Create(renderer);AssetDatabase.CreateAsset(urp,"Assets/TextureURP.asset");
            foreach(bool useUrp in new[]{true,false})
            {
                GraphicsSettings.defaultRenderPipeline=null;QualitySettings.renderPipeline=useUrp?urp:null;
                var report=Forge3DImporter.ImportPackage("Assets/Forge3D_Asset");
                if(report.materials!=2)throw new Exception("Distinct source material slots were collapsed.");
                var zero=AssetDatabase.LoadAssetAtPath<Material>("Assets/Forge3D_Asset/Materials/000.mat");
                var one=AssetDatabase.LoadAssetAtPath<Material>("Assets/Forge3D_Asset/Materials/001.mat");
                var fabric=zero!=null&&zero.name=="Fabric"?zero:one;
                var steel=zero!=null&&zero.name=="Steel"?zero:one;
                if(fabric==null||steel==null||fabric.shader.name!=(useUrp?"Universal Render Pipeline/Lit":"Standard"))throw new Exception("Pipeline materials absent.");
                if(Mathf.Abs(steel.GetFloat("_Metallic")-.9f)>.001f)throw new Exception("Metallic factor lost.");
                if(Mathf.Abs(steel.GetFloat(useUrp?"_Smoothness":"_Glossiness")-.8f)>.001f)throw new Exception("Roughness inversion lost.");
                var packed=fabric.GetTexture("_MetallicGlossMap");
                if(packed==null||!fabric.IsKeywordEnabled(useUrp?"_METALLICSPECGLOSSMAP":"_METALLICGLOSSMAP"))throw new Exception("Packed map absent.");
                var importer=AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(packed)) as TextureImporter;
                if(importer.sRGBTexture)throw new Exception("Packed data map incorrectly sRGB.");
                var raw=new Texture2D(2,2,TextureFormat.RGBA32,false,true);raw.LoadImage(File.ReadAllBytes(AssetDatabase.GetAssetPath(packed)));
                var pixel=raw.GetPixels32()[0];UnityEngine.Object.DestroyImmediate(raw);
                if(pixel.r!=64||pixel.a!=204)throw new Exception("glTF G/B to Unity R/A packing or factors incorrect.");
                if(!fabric.IsKeywordEnabled("_NORMALMAP")||fabric.GetTexture("_OcclusionMap")==null)throw new Exception("Preserved normal/AO absent.");
                var albedoImporter=AssetImporter.GetAtPath(AssetDatabase.GetAssetPath(fabric.GetTexture(useUrp?"_BaseMap":"_MainTex"))) as TextureImporter;
                if(!albedoImporter.sRGBTexture)throw new Exception("Albedo not sRGB.");
                File.Copy("Assets/Forge3D_Asset/unity_import_report.json","Assets/Forge3D_Asset/unity_texture_"+(useUrp?"urp":"builtin")+".json",true);
            }
            Debug.Log("TEXTURE_MULTIMATERIAL_PACKED_PBR_URP_BUILTIN_PASS");EditorApplication.Exit(0);
        }
        catch(Exception error){Debug.LogException(error);EditorApplication.Exit(1);}
    }
}
