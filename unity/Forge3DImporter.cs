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
    [Serializable] public class Manifest { public string name; public string pipeline; public string model; public string albedo; public string normal; public FBXValidation fbx_validation; }
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
        importer.materialImportMode = ModelImporterMaterialImportMode.None;
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
        foreach (Renderer renderer in instance.GetComponentsInChildren<Renderer>())
            renderer.sharedMaterials = Enumerable.Repeat(material, Math.Max(1,renderer.sharedMaterials.Length)).ToArray();
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
        var report = new ImportReport { passed=true, meshes=filters.Length, triangles=triangles, materials=1, textures=(texture!=null?1:0)+(normalTexture!=null?1:0), shader=shader.name, prefab=prefabPath, unityVersion=Application.unityVersion, dimensions=dimensions, normalsAndUVs=true, textureWidth=texture!=null?texture.width:0, textureHeight=texture!=null?texture.height:0, normalTextureWidth=normalTexture!=null?normalTexture.width:0, normalTextureHeight=normalTexture!=null?normalTexture.height:0, finiteVerticesAndUVs=true, normalMapImported=normalTexture!=null, normalMapType=normalTexture!=null?"NormalMap":null, normalKeywordEnabled=material.IsKeywordEnabled("_NORMALMAP") };
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
