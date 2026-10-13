using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

// Included in each Unity package. No runtime dependency or remote service.
public static class Forge3DImporter
{
    [Serializable] public class MeshStats { public float[] dimensions; public int triangles; }
    [Serializable] public class FBXValidation { public MeshStats before; }
    [Serializable] public class MaterialRecord { public string name; public string albedo; public string normal; public string metallic_smoothness; public string occlusion; public string unity_occlusion; public string emissive; public float[] color; public float[] emissive_factor; public float metallic; public float roughness; public string alpha_mode; public float alpha_cutoff; public bool double_sided; }
    [Serializable] public class Manifest { public string name; public string pipeline; public string model; public string albedo; public string normal; public FBXValidation fbx_validation; public MaterialRecord[] materials; }
    [Serializable] public class ImportReport { public bool passed; public int meshes; public int triangles; public int materials; public int textures; public string shader; public string prefab; public string unityVersion; public float[] dimensions; public bool normalsAndUVs; public int textureWidth; public int textureHeight; public int normalTextureWidth; public int normalTextureHeight; public bool finiteVerticesAndUVs; public bool normalMapImported; public string normalMapType; public bool normalKeywordEnabled; }

    static void PreserveTextureDimensions(TextureImporter importer, string path)
    {
        // Read the exported file before Unity's default 2K import limit is applied.
        Texture2D source = new Texture2D(2,2,TextureFormat.RGBA32,false);
        try
        {
            if(!ImageConversion.LoadImage(source,File.ReadAllBytes(path),true))throw new InvalidOperationException("Cannot read exported texture dimensions.");
            importer.maxTextureSize=Mathf.NextPowerOfTwo(Mathf.Max(source.width,source.height));
            importer.npotScale=TextureImporterNPOTScale.None;
        }
        finally { UnityEngine.Object.DestroyImmediate(source); }
    }

    static Texture2D ImportTexture(string folder,string relative,bool srgb,bool normal=false)
    {
        if(string.IsNullOrEmpty(relative))return null;
        string path=(folder+"/"+relative).Replace('\\','/');
        string absolute=Path.GetFullPath(path),root=Path.GetFullPath(folder)+Path.DirectorySeparatorChar;
        if(!absolute.StartsWith(root,StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("Texture path outside asset package.");
        AssetDatabase.ImportAsset(path,ImportAssetOptions.ForceSynchronousImport);
        var importer=AssetImporter.GetAtPath(path) as TextureImporter;
        if(importer==null)throw new InvalidOperationException("Texture importer unavailable: "+path);
        importer.sRGBTexture=srgb;importer.textureType=normal?TextureImporterType.NormalMap:TextureImporterType.Default;
        importer.textureCompression=TextureImporterCompression.Uncompressed;
        PreserveTextureDimensions(importer,path);importer.SaveAndReimport();
        return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
    }

    static Material ImportMaterial(string folder,string materialFolder,int index,Shader shader,MaterialRecord record)
    {
        string path=materialFolder+"/"+index.ToString("D3")+".mat";
        var material=AssetDatabase.LoadAssetAtPath<Material>(path);
        if(material==null){material=new Material(shader);AssetDatabase.CreateAsset(material,path);}
        material.shader=shader;material.name=record.name;
        var color=record.color!=null&&record.color.Length==4?new Color(record.color[0],record.color[1],record.color[2],record.color[3]):Color.white;
        var albedo=ImportTexture(folder,record.albedo,true);
        var normal=ImportTexture(folder,record.normal,false,true);
        var metallic=ImportTexture(folder,record.metallic_smoothness,false);
        var occlusion=ImportTexture(folder,record.unity_occlusion??record.occlusion,false);
        var emissive=ImportTexture(folder,record.emissive,true);
        foreach(string property in new[]{"_BaseMap","_MainTex"})if(material.HasProperty(property))material.SetTexture(property,albedo);
        foreach(string property in new[]{"_BaseColor","_Color"})if(material.HasProperty(property))material.SetColor(property,color);
        material.SetTexture("_BumpMap",normal);material.SetTexture("_MetallicGlossMap",metallic);material.SetTexture("_OcclusionMap",occlusion);material.SetTexture("_EmissionMap",emissive);
        foreach(string keyword in new[]{"_NORMALMAP","_METALLICGLOSSMAP","_METALLICSPECGLOSSMAP","_EMISSION","_ALPHATEST_ON","_ALPHABLEND_ON","_ALPHAPREMULTIPLY_ON","_SURFACE_TYPE_TRANSPARENT"})material.DisableKeyword(keyword);
        if(normal!=null)material.EnableKeyword("_NORMALMAP");
        if(metallic!=null)material.EnableKeyword(shader.name=="Standard"?"_METALLICGLOSSMAP":"_METALLICSPECGLOSSMAP");
        material.SetFloat("_Metallic",metallic!=null?1:record.metallic);
        foreach(string property in new[]{"_Smoothness","_Glossiness","_GlossMapScale"})if(material.HasProperty(property))material.SetFloat(property,metallic!=null?1:1-record.roughness);
        if(material.HasProperty("_OcclusionStrength"))material.SetFloat("_OcclusionStrength",1);
        var emission=record.emissive_factor!=null&&record.emissive_factor.Length==3?new Color(record.emissive_factor[0],record.emissive_factor[1],record.emissive_factor[2]):Color.black;
        material.SetColor("_EmissionColor",emission);
        if(emissive!=null||emission.maxColorComponent>0)material.EnableKeyword("_EMISSION");
        bool blend=record.alpha_mode=="BLEND",cutout=record.alpha_mode=="MASK";
        if(material.HasProperty("_Mode"))material.SetFloat("_Mode",blend?3:cutout?1:0);
        if(material.HasProperty("_Surface"))material.SetFloat("_Surface",blend?1:0);
        if(material.HasProperty("_AlphaClip"))material.SetFloat("_AlphaClip",cutout?1:0);
        if(material.HasProperty("_Cutoff"))material.SetFloat("_Cutoff",record.alpha_cutoff);
        material.SetFloat("_SrcBlend",(float)(blend?BlendMode.SrcAlpha:BlendMode.One));material.SetFloat("_DstBlend",(float)(blend?BlendMode.OneMinusSrcAlpha:BlendMode.Zero));material.SetFloat("_ZWrite",blend?0:1);
        if(blend){material.EnableKeyword(shader.name=="Standard"?"_ALPHABLEND_ON":"_SURFACE_TYPE_TRANSPARENT");}
        if(cutout)material.EnableKeyword("_ALPHATEST_ON");
        material.SetOverrideTag("RenderType",blend?"Transparent":cutout?"TransparentCutout":"Opaque");material.renderQueue=blend?3000:cutout?2450:2000;
        if(material.HasProperty("_Cull"))material.SetFloat("_Cull",record.double_sided?(float)CullMode.Off:(float)CullMode.Back);
        material.doubleSidedGI=record.double_sided;EditorUtility.SetDirty(material);
        return material;
    }

    [MenuItem("Tools/Forge3D/Import selected asset package")]
    public static void ImportSelected()
    {
        string folder = AssetDatabase.GetAssetPath(Selection.activeObject);
        if (!Directory.Exists(folder)) throw new InvalidOperationException("Select the Forge3D_Asset folder in the Project panel.");
        ImportPackage(folder);
    }

    public static ImportReport ImportPackage(string folder)
    {
        string manifestPath = Path.Combine(folder, "asset_manifest.json");
        Manifest manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(manifestPath));
        string modelPath = (folder + "/" + manifest.model).Replace('\\', '/');
        AssetDatabase.ImportAsset(modelPath, ImportAssetOptions.ForceSynchronousImport);
        ModelImporter importer = AssetImporter.GetAtPath(modelPath) as ModelImporter;
        if (importer == null) throw new InvalidOperationException("FBX importer unavailable.");
        importer.globalScale = 1f;
        importer.useFileScale = true;
        importer.bakeAxisConversion = true;
        importer.importNormals = ModelImporterNormals.Import;
        importer.importTangents = ModelImporterTangents.CalculateMikk;
        importer.importAnimation = false;
        bool multiple=manifest.materials!=null&&manifest.materials.Length>0;
        importer.materialImportMode = multiple?ModelImporterMaterialImportMode.ImportStandard:ModelImporterMaterialImportMode.None;
        importer.SaveAndReimport();
        GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(modelPath);
        if (model == null) throw new InvalidOperationException("FBX produced no GameObject.");
        string materialFolder = folder + "/Materials";
        string prefabFolder = folder + "/Prefabs";
        Directory.CreateDirectory(materialFolder);
        Directory.CreateDirectory(prefabFolder);
        AssetDatabase.Refresh();
        // URP material only when URP is active. Built-in retains Standard fallback.
        Shader shader = GraphicsSettings.currentRenderPipeline != null ? Shader.Find("Universal Render Pipeline/Lit") : Shader.Find("Standard");
        if (shader == null) shader = Shader.Find("Universal Render Pipeline/Lit");
        if (shader == null) throw new InvalidOperationException("Install URP or enable Built-in Standard shader.");
        string materialPath = materialFolder + "/Forge3D.mat";
        Material material = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
        if (material == null) { material = new Material(shader); AssetDatabase.CreateAsset(material, materialPath); }
        material.shader = shader;
        // Neutral constants match the generated material; these are not maps.
        if(material.HasProperty("_Metallic"))material.SetFloat("_Metallic",0f);
        if(material.HasProperty("_Smoothness"))material.SetFloat("_Smoothness",0.35f);
        if(material.HasProperty("_Glossiness"))material.SetFloat("_Glossiness",0.35f);
        Texture2D texture = null;
        if (!string.IsNullOrEmpty(manifest.albedo))
        {
            string texturePath = (folder + "/" + manifest.albedo).Replace('\\','/');
            AssetDatabase.ImportAsset(texturePath, ImportAssetOptions.ForceSynchronousImport);
            TextureImporter textureImporter = AssetImporter.GetAtPath(texturePath) as TextureImporter;
            if (textureImporter == null) throw new InvalidOperationException("Albedo texture unavailable.");
            textureImporter.sRGBTexture = true;
            textureImporter.textureType = TextureImporterType.Default;
            PreserveTextureDimensions(textureImporter,texturePath);
            textureImporter.SaveAndReimport();
            texture = AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath);
        }
        // Reimporting geometry-only packages must clear a previous asset's map.
        if (material.HasProperty("_BaseMap")) material.SetTexture("_BaseMap",texture);
        if (material.HasProperty("_MainTex")) material.SetTexture("_MainTex",texture);
        Texture2D normalTexture=null;
        if(!string.IsNullOrEmpty(manifest.normal))
        {
            string normalPath=(folder+"/"+manifest.normal).Replace('\\','/');
            AssetDatabase.ImportAsset(normalPath,ImportAssetOptions.ForceSynchronousImport);
            TextureImporter normalImporter=AssetImporter.GetAtPath(normalPath) as TextureImporter;
            if(normalImporter==null)throw new InvalidOperationException("Normal map unavailable.");
            normalImporter.textureType=TextureImporterType.NormalMap;
            normalImporter.sRGBTexture=false;
            PreserveTextureDimensions(normalImporter,normalPath);
            normalImporter.SaveAndReimport();
            normalTexture=AssetDatabase.LoadAssetAtPath<Texture2D>(normalPath);
        }
        if(material.HasProperty("_BumpMap"))material.SetTexture("_BumpMap",normalTexture);
        if(normalTexture!=null)material.EnableKeyword("_NORMALMAP");else material.DisableKeyword("_NORMALMAP");
        Color baseColor = texture != null ? Color.white : new Color(0.5f,0.5f,0.5f,1f);
        if (material.HasProperty("_BaseColor")) material.SetColor("_BaseColor",baseColor);
        if (material.HasProperty("_Color")) material.SetColor("_Color",baseColor);
        GameObject instance = UnityEngine.Object.Instantiate(model);
        instance.name = "Forge3D_Asset";
        var materialSlots=new System.Collections.Generic.Dictionary<string,Material>();
        if(multiple)for(int index=0;index<manifest.materials.Length;index++)materialSlots.Add(manifest.materials[index].name,ImportMaterial(folder,materialFolder,index,shader,manifest.materials[index]));
        foreach (Renderer renderer in instance.GetComponentsInChildren<Renderer>())
        {
            if(multiple)renderer.sharedMaterials=renderer.sharedMaterials.Select(slot=>{if(slot==null||!materialSlots.TryGetValue(slot.name,out var mapped))throw new InvalidOperationException("Unmapped FBX material slot: "+(slot!=null?slot.name:"null"));return mapped;}).ToArray();
            else renderer.sharedMaterials = Enumerable.Repeat(material, Math.Max(1,renderer.sharedMaterials.Length)).ToArray();
        }
        MeshFilter[] filters = instance.GetComponentsInChildren<MeshFilter>();
        int triangles = filters.Sum(filter => filter.sharedMesh != null ? filter.sharedMesh.triangles.Length / 3 : 0);
        if (triangles <= 0) throw new InvalidOperationException("Imported mesh is empty.");
        Renderer[] renderers=instance.GetComponentsInChildren<Renderer>();
        Bounds bounds=renderers[0].bounds;
        foreach(Renderer renderer in renderers)bounds.Encapsulate(renderer.bounds);
        float[] dimensions=new[]{bounds.size.x,bounds.size.y,bounds.size.z};
        foreach(MeshFilter filter in filters)
        {
            Mesh mesh=filter.sharedMesh;
            if(mesh.uv.Length!=mesh.vertexCount||mesh.normals.Length!=mesh.vertexCount)throw new InvalidOperationException("FBX lost UVs or normals.");
            foreach(Vector3 vertex in mesh.vertices)if(!float.IsFinite(vertex.x)||!float.IsFinite(vertex.y)||!float.IsFinite(vertex.z))throw new InvalidOperationException("Invalid imported vertex.");
            foreach(Vector2 uv in mesh.uv)if(!float.IsFinite(uv.x)||!float.IsFinite(uv.y))throw new InvalidOperationException("Invalid imported UV.");
        }
        if(manifest.fbx_validation?.before?.triangles>0&&triangles!=manifest.fbx_validation.before.triangles)throw new InvalidOperationException("Unity import changed triangle count.");
        float[] expected=manifest.fbx_validation?.before?.dimensions;
        if(expected!=null&&expected.Length==3&&Mathf.Abs(dimensions[1]-expected[2])>Mathf.Max(0.001f,expected[2]*0.01f))
            throw new InvalidOperationException("Unity Y-up height/scale differs from Blender Z-up export.");
        string prefabPath = prefabFolder + "/Forge3D.prefab";
        PrefabUtility.SaveAsPrefabAsset(instance,prefabPath);
        UnityEngine.Object.DestroyImmediate(instance);
        EditorUtility.SetDirty(material);
        AssetDatabase.SaveAssets();
        var report = new ImportReport { passed=true, meshes=filters.Length, triangles=triangles, materials=multiple?materialSlots.Count:1, textures=multiple?materialSlots.Values.SelectMany(m=>m.GetTexturePropertyNames().Select(m.GetTexture)).Where(t=>t!=null).Distinct().Count():(texture!=null?1:0)+(normalTexture!=null?1:0), shader=shader.name, prefab=prefabPath, unityVersion=Application.unityVersion, dimensions=dimensions, normalsAndUVs=true, textureWidth=texture!=null?texture.width:0, textureHeight=texture!=null?texture.height:0, normalTextureWidth=normalTexture!=null?normalTexture.width:0, normalTextureHeight=normalTexture!=null?normalTexture.height:0, finiteVerticesAndUVs=true, normalMapImported=normalTexture!=null||materialSlots.Values.Any(m=>m.IsKeywordEnabled("_NORMALMAP")), normalMapType=normalTexture!=null?"NormalMap":null, normalKeywordEnabled=material.IsKeywordEnabled("_NORMALMAP")||materialSlots.Values.Any(m=>m.IsKeywordEnabled("_NORMALMAP")) };
        File.WriteAllText(Path.Combine(folder,"unity_import_report.json"),JsonUtility.ToJson(report,true));
        Debug.Log("FORGE3D_IMPORT_PASS " + JsonUtility.ToJson(report));
        return report;
    }

    // Headless test entrypoint, after the exported folder has been copied into Assets.
    public static void BatchValidate()
    {
        try { ImportPackage("Assets/Forge3D_Asset"); EditorApplication.Exit(0); }
        catch (Exception error) { Debug.LogException(error); EditorApplication.Exit(1); }
    }
}
